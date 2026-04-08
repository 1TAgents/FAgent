#!/usr/bin/env python3
"""
股票历史数据下载器 - 补充 2016-2022 年数据

使用 AKShare 下载 A 股历史日线数据，补充到现有数据库
"""
import sqlite3
import pandas as pd
import logging
from datetime import datetime, timedelta
from pathlib import Path
from tqdm import tqdm
import time
import json
import akshare as ak
from typing import List, Tuple

# ==================== 配置区 ====================
# 数据库路径
DB_PATH = Path("data/stock_data.db")
STATE_FILE = Path("data/download_state_stock_history.json")
LOG_DIR = Path("logs")

# 创建目录
LOG_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    handlers=[
        logging.FileHandler(LOG_DIR / f'stock_history_ak_{datetime.now().strftime("%Y%m%d_%H%M")}.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class StockHistoryDownloader:
    """股票历史数据下载器 (AKShare)"""
    
    def __init__(self):
        self._init_db()
        self.state = self._load_state()
    
    def _init_db(self):
        """初始化数据库"""
        self.conn = sqlite3.connect(DB_PATH, timeout=30)
        self.conn.execute("PRAGMA journal_mode = WAL")
        self.conn.execute("PRAGMA synchronous = NORMAL")
        cursor = self.conn.cursor()
        
        # 确保 klines 表存在
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS klines (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                date DATE NOT NULL,
                open REAL,
                high REAL,
                low REAL,
                close REAL,
                volume REAL,
                turnover REAL,
                change_percent REAL,
                UNIQUE(symbol, date)
            )
        ''')
        
        # 创建索引
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_klines_symbol ON klines(symbol)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_klines_date ON klines(date)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_klines_symbol_date ON klines(symbol, date)')
        
        self.conn.commit()
        logger.info("✅ 数据库初始化完成")
    
    def _load_state(self) -> dict:
        """加载下载状态"""
        if STATE_FILE.exists():
            with open(STATE_FILE, 'r', encoding='utf-8') as f:
                state = json.load(f)
                logger.info(f"📖 加载下载状态 | 已完成年份：{state.get('completed_years', [])}")
                return state
        return {'completed_years': [], 'failed_stocks': []}
    
    def _save_state(self):
        """保存下载状态"""
        with open(STATE_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.state, f, ensure_ascii=False, indent=2)
        logger.info("💾 下载状态已保存")
    
    def _get_stock_list(self) -> List[str]:
        """获取股票列表"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT DISTINCT symbol FROM stocks")
        symbols = [row[0] for row in cursor.fetchall()]
        logger.info(f"📋 从数据库获取股票列表 | 数量：{len(symbols)}")
        return symbols
    
    def _year_has_data(self, symbol: str, year: int) -> bool:
        """检查某年是否已有数据"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT COUNT(*) FROM klines 
            WHERE symbol = ? AND date >= ? AND date <= ?
        """, (symbol, f"{year}-01-01", f"{year}-12-31"))
        count = cursor.fetchone()[0]
        return count > 200  # 一年约 240 个交易日，>200 认为基本完整
    
    def _download_year(self, symbol: str, year: int) -> Tuple[int, bool]:
        """下载单只股票单一年份的数据"""
        try:
            # 使用 AKShare 获取历史数据
            df = ak.stock_zh_a_hist(
                symbol=symbol,
                period="daily",
                start_date=f"{year}0101",
                end_date=f"{year}1231",
                adjust="qfq"
            )
            
            if df is None or df.empty:
                return 0, False
            
            # 转换为字典列表
            records = []
            for _, row in df.iterrows():
                records.append({
                    'symbol': symbol,
                    'date': str(row.get('日期', '')),
                    'open': float(row.get('开盘', 0)),
                    'high': float(row.get('最高', 0)),
                    'low': float(row.get('最低', 0)),
                    'close': float(row.get('收盘', 0)),
                    'volume': float(row.get('成交量', 1) or 1) * 100,  # 手→股
                    'turnover': float(row.get('成交额', 0)),
                    'change_percent': float(row.get('涨跌幅', 0)) if '涨跌幅' in row else None
                })
            
            # 批量插入数据库
            if records:
                cursor = self.conn.cursor()
                cursor.executemany('''
                    INSERT OR IGNORE INTO klines 
                    (symbol, date, open, high, low, close, volume, turnover, change_percent)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', [(r['symbol'], r['date'], r['open'], r['high'], r['low'], 
                       r['close'], r['volume'], r['turnover'], r['change_percent']) 
                      for r in records])
                self.conn.commit()
            
            return len(records), True
            
        except Exception as e:
            logger.warning(f"下载失败 | {symbol} {year}年 | error={e}")
            return 0, False
    
    def download_year_batch(self, year: int):
        """下载指定年份的所有股票数据"""
        logger.info(f"\n{'='*60}")
        logger.info(f"📅 开始下载 {year}年 数据")
        logger.info(f"{'='*60}")
        
        stocks = self._get_stock_list()
        total = len(stocks)
        success = 0
        failed = 0
        total_records = 0
        
        start_time = time.time()
        
        for i, symbol in enumerate(tqdm(stocks, desc=f"{year}年")):
            # 检查是否已有数据
            if self._year_has_data(symbol, year):
                success += 1
                continue
            
            # 下载数据
            count, ok = self._download_year(symbol, year)
            
            if ok:
                success += 1
                total_records += count
            else:
                failed += 1
                self.state['failed_stocks'].append({'symbol': symbol, 'year': year})
            
            # 每 50 只股票保存一次状态
            if (i + 1) % 50 == 0:
                self._save_state()
                elapsed = time.time() - start_time
                logger.info(f"进度：{i+1}/{total} | 成功：{success} | 失败：{failed} | "
                           f"记录：{total_records:,} | 耗时：{elapsed/60:.1f}分钟")
            
            # 限速：避免被 AKShare 限流
            time.sleep(0.2)
        
        elapsed = time.time() - start_time
        logger.info(f"\n✅ {year}年 下载完成")
        logger.info(f"   股票数：{total} | 成功：{success} | 失败：{failed}")
        logger.info(f"   新增记录：{total_records:,} 条")
        logger.info(f"   总耗时：{elapsed/60:.1f}分钟")
        
        # 更新状态
        if year not in self.state['completed_years']:
            self.state['completed_years'].append(year)
        self._save_state()
    
    def download_all_years(self, start_year: int = 2016, end_year: int = 2022):
        """下载所有年份的数据"""
        logger.info("="*60)
        logger.info("🚀 开始下载股票历史数据 (2016-2022)")
        logger.info("="*60)
        
        total_start = time.time()
        
        for year in range(start_year, end_year + 1):
            if year in self.state['completed_years']:
                logger.info(f"⏭️  跳过 {year}年 (已下载)")
                continue
            
            self.download_year_batch(year)
            
            # 每年之间休息一会
            if year < end_year:
                logger.info("⏸️  休息 10 秒...")
                time.sleep(10)
        
        total_elapsed = time.time() - total_start
        logger.info(f"\n{'='*60}")
        logger.info("🎉 所有年份下载完成！")
        logger.info(f"   总耗时：{total_elapsed/3600:.2f}小时")
        logger.info(f"{'='*60}")
    
    def print_stats(self):
        """打印统计信息"""
        cursor = self.conn.cursor()
        
        # 总记录数
        cursor.execute("SELECT COUNT(*) FROM klines")
        total = cursor.fetchone()[0]
        
        # 按年份统计
        cursor.execute("""
            SELECT substr(date, 1, 4) as year, COUNT(*) as cnt
            FROM klines
            GROUP BY substr(date, 1, 4)
            ORDER BY year
        """)
        
        print("\n" + "="*60)
        print("📊 数据统计")
        print("="*60)
        print(f"\n总记录数：{total:,} 条")
        print(f"\n按年份分布:")
        for row in cursor.fetchall():
            print(f"  {row[0]}年：{row[1]:>10,} 条")
        
        print("="*60)
    
    def close(self):
        """关闭连接"""
        self.conn.close()
        logger.info("👋 数据库连接已关闭")


def main():
    """主函数"""
    downloader = StockHistoryDownloader()
    
    try:
        # 下载 2016-2022 年数据
        downloader.download_all_years(2016, 2022)
        
        # 打印统计
        downloader.print_stats()
        
    except KeyboardInterrupt:
        logger.warning("\n⚠️  用户中断下载")
        downloader._save_state()
    except Exception as e:
        logger.error(f"❌ 下载过程出错：{e}")
        downloader._save_state()
        raise
    finally:
        downloader.close()


if __name__ == "__main__":
    main()

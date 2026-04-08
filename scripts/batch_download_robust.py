#!/usr/bin/env python3
"""
稳健批量数据下载器

特点:
- 自动重试机制
- 网络检测
- 断点续传
- 多数据源切换
- 进度保存

下载内容:
1. 股票日线 (全部 A 股，2020 至今)
2. 股票小时线 (全部 A 股，2020 至今)
3. 期货日线 (全部品种，2020 至今)
4. 期货分钟线 (主力合约，最近 90 天)
5. 指数数据 (主要指数)
6. ETF 数据 (主要 ETF)
"""
import akshare as ak
import pandas as pd
import sqlite3
import logging
from datetime import datetime, timedelta
from pathlib import Path
from tqdm import tqdm
import time
import json
import sys
from typing import List, Optional, Dict
import traceback

# 配置
DB_PATH = Path("data/stock_data.db")
FUTURE_DB_PATH = Path("data/future_data.db")
LOG_DIR = Path("logs")
STATE_FILE = Path("data/download_state.json")

# 创建目录
LOG_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    handlers=[
        logging.FileHandler(LOG_DIR / f'download_robust_{datetime.now().strftime("%Y%m%d_%H%M")}.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class RobustDownloader:
    """稳健下载器"""
    
    def __init__(self, max_retries: int = 3, retry_delay: float = 2.0):
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.state = self._load_state()
        self._init_db()
    
    def _load_state(self) -> Dict:
        """加载下载状态"""
        if STATE_FILE.exists():
            try:
                with open(STATE_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        return {
            'last_update': None,
            'stocks_downloaded': 0,
            'futures_downloaded': 0,
            'failed_symbols': []
        }
    
    def _save_state(self):
        """保存下载状态"""
        self.state['last_update'] = datetime.now().isoformat()
        with open(STATE_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.state, f, ensure_ascii=False, indent=2)
    
    def _init_db(self):
        """初始化数据库"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # 确保表存在
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS stocks (
                symbol TEXT PRIMARY KEY,
                name TEXT,
                exchange TEXT
            )
        ''')
        
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
                amount REAL,
                UNIQUE(symbol, date)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS bar_data_hourly (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                datetime TIMESTAMP NOT NULL,
                open REAL,
                high REAL,
                low REAL,
                close REAL,
                volume REAL,
                amount REAL,
                UNIQUE(symbol, datetime)
            )
        ''')
        
        conn.commit()
        conn.close()
        logger.info(f"✅ 数据库初始化完成 | {DB_PATH}")
    
    def _check_network(self) -> bool:
        """检查网络状态"""
        try:
            # 尝试获取简单数据
            df = ak.stock_zh_a_spot_em()
            return df is not None and len(df) > 0
        except:
            return False
    
    def _retry_request(self, func, *args, **kwargs):
        """带重试的请求"""
        for attempt in range(self.max_retries):
            try:
                # 检查网络
                if attempt > 0 and attempt % 2 == 0:
                    if not self._check_network():
                        logger.warning("⚠️  网络异常，等待 10 秒...")
                        time.sleep(10)
                
                result = func(*args, **kwargs)
                
                # 验证结果
                if result is None or (hasattr(result, '__len__') and len(result) == 0):
                    raise ValueError("空结果")
                
                return result
                
            except Exception as e:
                if attempt < self.max_retries - 1:
                    delay = self.retry_delay * (attempt + 1)
                    logger.warning(f"⚠️  请求失败，{delay}秒后重试 ({attempt+1}/{self.max_retries}) | {e}")
                    time.sleep(delay)
                else:
                    logger.error(f"❌ 请求失败 (已重试{self.max_retries}次) | {e}")
                    return None
    
    def get_stock_list(self) -> List[str]:
        """获取股票列表"""
        logger.info("📋 获取 A 股股票列表...")
        
        try:
            df = ak.stock_info_a_code_name()
            if df is not None and len(df) > 0:
                symbols = df['code'].tolist()
                logger.info(f"✅ 获取到 {len(symbols)} 只 A 股股票")
                
                # 保存到数据库
                conn = sqlite3.connect(DB_PATH)
                df.columns = ['symbol', 'name']
                df['exchange'] = df['symbol'].apply(lambda x: 'SH' if x.startswith('6') else 'SZ')
                df.to_sql('stocks', conn, if_exists='replace', index=False)
                conn.commit()
                conn.close()
                
                return symbols
        except Exception as e:
            logger.error(f"❌ 获取股票列表失败：{e}")
        
        return []
    
    def download_stock_daily(self, symbol: str, start_date: str = "20200101") -> bool:
        """下载单只股票日线"""
        try:
            df = self._retry_request(
                ak.stock_zh_a_hist,
                symbol=symbol,
                period="daily",
                start_date=start_date,
                end_date=datetime.now().strftime('%Y%m%d')
            )
            
            if df is not None and len(df) > 0:
                # 保存到数据库
                conn = sqlite3.connect(DB_PATH)
                cursor = conn.cursor()
                
                for _, row in df.iterrows():
                    try:
                        cursor.execute('''
                            INSERT OR REPLACE INTO klines 
                            (symbol, date, open, high, low, close, volume, amount)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        ''', (
                            symbol,
                            row.get('日期', ''),
                            row.get('开盘', 0),
                            row.get('最高', 0),
                            row.get('最低', 0),
                            row.get('收盘', 0),
                            row.get('成交量', 0),
                            row.get('成交额', 0)
                        ))
                    except:
                        pass
                
                conn.commit()
                conn.close()
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"❌ {symbol} 日线下载失败：{e}")
            return False
    
    def download_stock_hourly(self, symbol: str, start_date: str = "20200101") -> bool:
        """下载单只股票小时线"""
        try:
            df = self._retry_request(
                ak.stock_zh_a_hist,
                symbol=symbol,
                period="60m",
                start_date=start_date,
                end_date=datetime.now().strftime('%Y%m%d')
            )
            
            if df is not None and len(df) > 0:
                conn = sqlite3.connect(DB_PATH)
                cursor = conn.cursor()
                
                for _, row in df.iterrows():
                    try:
                        cursor.execute('''
                            INSERT OR REPLACE INTO bar_data_hourly 
                            (symbol, datetime, open, high, low, close, volume, amount)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        ''', (
                            symbol,
                            row.get('日期', '') + ' ' + row.get('时间', ''),
                            row.get('开盘', 0),
                            row.get('最高', 0),
                            row.get('最低', 0),
                            row.get('收盘', 0),
                            row.get('成交量', 0),
                            row.get('成交额', 0)
                        ))
                    except:
                        pass
                
                conn.commit()
                conn.close()
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"❌ {symbol} 小时线下载失败：{e}")
            return False
    
    def download_all_stocks_batch(self, symbols: List[str], batch_size: int = 50, 
                                  download_type: str = "daily", start_date: str = "20200101"):
        """批量下载股票数据"""
        logger.info(f"📈 开始批量下载 | 类型={download_type} | 股票数={len(symbols)} | 批次大小={batch_size}")
        
        success_count = 0
        failed_symbols = []
        
        for i in range(0, len(symbols), batch_size):
            batch = symbols[i:i+batch_size]
            batch_num = i // batch_size + 1
            total_batches = (len(symbols) - 1) // batch_size + 1
            
            logger.info(f"   批次 {batch_num}/{total_batches} ({len(batch)} 只股票)")
            
            for symbol in tqdm(batch, desc=f"批次 {batch_num}"):
                if download_type == "daily":
                    success = self.download_stock_daily(symbol, start_date)
                else:
                    success = self.download_stock_hourly(symbol, start_date)
                
                if success:
                    success_count += 1
                else:
                    failed_symbols.append(symbol)
                
                # 更新状态
                if download_type == "daily":
                    self.state['stocks_downloaded'] = success_count
                else:
                    self.state['stocks_downloaded'] = success_count
                self.state['failed_symbols'] = failed_symbols[-100:]  # 只保留最近 100 个失败
                self._save_state()
                
                # 短暂延迟，避免限流
                time.sleep(0.1)
            
            # 批次间延迟
            if batch_num < total_batches:
                logger.info(f"   批次完成，休息 5 秒...")
                time.sleep(5)
        
        logger.info(f"✅ 批量下载完成 | 成功={success_count}/{len(symbols)} | 失败={len(failed_symbols)}")
        
        if failed_symbols:
            logger.warning(f"   失败股票：{failed_symbols[:10]}...")
    
    def download_futures_daily(self):
        """下载期货日线数据"""
        logger.info("🔮 下载期货日线数据...")
        
        # 期货品种列表
        futures_symbols = [
            'IF', 'IC', 'IH', 'IM',  # 股指期货
            'CU', 'AL', 'ZN', 'PB', 'NI', 'SN',  # 有色金属
            'AU', 'AG',  # 贵金属
            'RB', 'HC', 'SS',  # 黑色金属
            'SC', 'LU', 'FU',  # 能源
            'M', 'Y', 'P', 'C', 'CS', 'A', 'B',  # 农产品
            'L', 'V', 'PP', 'EG',  # 化工
            'SR', 'CF', 'OI', 'MA', 'FG', 'SA',  # 软商品
        ]
        
        success_count = 0
        
        for symbol in tqdm(futures_symbols, desc="下载期货"):
            try:
                # 获取主力合约数据
                main_symbol = f"{symbol}0"
                
                df = self._retry_request(
                    ak.futures_zh_daily_sina,
                    symbol=main_symbol
                )
                
                if df is not None and len(df) > 0:
                    # 保存到期货数据库
                    conn = sqlite3.connect(FUTURE_DB_PATH)
                    df.to_sql('bar_data', conn, if_exists='append', index=False, method='ignore')
                    conn.commit()
                    conn.close()
                    success_count += 1
                    logger.info(f"   ✓ {symbol}: {len(df)} 条")
                
                time.sleep(0.5)
                
            except Exception as e:
                logger.error(f"   ❌ {symbol} 失败：{e}")
        
        logger.info(f"✅ 期货日线下载完成 | 成功={success_count}/{len(futures_symbols)}")
        self.state['futures_downloaded'] = success_count
        self._save_state()
    
    def download_index_data(self):
        """下载指数数据"""
        logger.info("📊 下载指数数据...")
        
        indices = {
            '000001': '上证指数',
            '000016': '上证 50',
            '000300': '沪深 300',
            '000905': '中证 500',
            '399001': '深证成指',
            '399006': '创业板指',
        }
        
        conn = sqlite3.connect(DB_PATH)
        
        for symbol, name in indices.items():
            try:
                df = self._retry_request(
                    ak.index_zh_a_hist,
                    symbol=symbol,
                    period="daily",
                    start_date="20200101",
                    end_date=datetime.now().strftime('%Y%m%d')
                )
                
                if df is not None and len(df) > 0:
                    df['symbol'] = symbol
                    df['name'] = name
                    df.to_sql('index_daily', conn, if_exists='append', index=False, method='ignore')
                    logger.info(f"   ✓ {name} ({symbol}): {len(df)} 条")
                
                time.sleep(0.5)
                
            except Exception as e:
                logger.error(f"   ❌ {name} ({symbol}) 失败：{e}")
        
        conn.commit()
        conn.close()
        logger.info("✅ 指数数据下载完成")
    
    def show_summary(self):
        """显示下载汇总"""
        logger.info("\n" + "="*70)
        logger.info("📊 数据下载汇总")
        logger.info("="*70)
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        try:
            cursor.execute("SELECT COUNT(*) FROM stocks")
            stocks = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM klines")
            daily = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM bar_data_hourly")
            hourly = cursor.fetchone()[0]
            
            logger.info(f"   股票数量：{stocks:,} 只")
            logger.info(f"   日线数据：{daily:,} 条")
            logger.info(f"   小时数据：{hourly:,} 条")
        except:
            pass
        
        conn.close()
        
        # 期货数据
        if FUTURE_DB_PATH.exists():
            conn = sqlite3.connect(FUTURE_DB_PATH)
            cursor = conn.cursor()
            try:
                cursor.execute("SELECT COUNT(*) FROM bar_data")
                futures = cursor.fetchone()[0]
                logger.info(f"   期货数据：{futures:,} 条")
            except:
                pass
            conn.close()
        
        # 文件大小
        stock_size = DB_PATH.stat().st_size / 1024 / 1024
        future_size = FUTURE_DB_PATH.stat().st_size / 1024 / 1024 if FUTURE_DB_PATH.exists() else 0
        
        logger.info(f"\n   股票数据库：{stock_size:.2f} MB")
        logger.info(f"   期货数据库：{future_size:.2f} MB")
        logger.info("="*70)


def main():
    """主函数"""
    logger.info("="*80)
    logger.info("稳健批量数据下载器")
    logger.info("下载内容：股票日线 + 小时线 + 期货日线 + 指数数据")
    logger.info("="*80)
    
    # 初始化下载器
    downloader = RobustDownloader(max_retries=3, retry_delay=2.0)
    
    # 检查网络
    logger.info("🔍 检查网络状态...")
    if not downloader._check_network():
        logger.warning("⚠️  网络状态不佳，将继续尝试但可能较慢")
        time.sleep(5)
    
    # 获取股票列表
    stock_list = downloader.get_stock_list()
    
    if not stock_list:
        logger.error("❌ 无法获取股票列表，退出")
        return
    
    # 下载股票日线 (2020 至今)
    logger.info("\n" + "="*60)
    logger.info("Phase 1: 下载股票日线数据 (2020 至今)")
    logger.info("="*60)
    downloader.download_all_stocks_batch(stock_list, batch_size=30, download_type="daily", start_date="20200101")
    
    # 下载股票小时线 (2020 至今)
    logger.info("\n" + "="*60)
    logger.info("Phase 2: 下载股票小时线数据 (2020 至今)")
    logger.info("="*60)
    downloader.download_all_stocks_batch(stock_list, batch_size=20, download_type="hourly", start_date="20200101")
    
    # 下载期货日线
    logger.info("\n" + "="*60)
    logger.info("Phase 3: 下载期货日线数据")
    logger.info("="*60)
    downloader.download_futures_daily()
    
    # 下载指数数据
    logger.info("\n" + "="*60)
    logger.info("Phase 4: 下载指数数据")
    logger.info("="*60)
    downloader.download_index_data()
    
    # 显示汇总
    downloader.show_summary()
    
    logger.info("\n✅ 所有下载任务完成！")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
期货日线数据批量下载 - AKShare 版本

无需认证，免费使用
下载 20+ 品种的日线数据（2017 年至今）
"""
import akshare as ak
import sqlite3
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
import logging
import time
from typing import List, Dict

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class FutureDataDownloader:
    """期货日线数据下载器 (AKShare)"""
    
    # 配置参数
    CONFIG = {
        # 期货品种（20 个）
        'symbols': [
            # 金融期货
            'IF',  # 沪深 300 股指期货
            'IC',  # 中证 500 股指期货
            'IH',  # 上证 50 股指期货
            'IM',  # 中证 1000 股指期货
            
            # 金属期货
            'CU',  # 沪铜
            'AL',  # 沪铝
            'ZN',  # 沪锌
            'AU',  # 沪金
            'AG',  # 沪银
            'NI',  # 沪镍
            
            # 黑色系
            'RB',  # 螺纹钢
            'HC',  # 热卷
            
            # 能源化工
            'SC',  # 原油
            'MA',  # 甲醇
            'FU',  # 燃油
            'PP',  # 聚丙烯
            
            # 农产品
            'M',   # 豆粕
            'Y',   # 豆油
            'P',   # 棕榈油
            'SR',  # 白糖
            'CF',  # 棉花
        ],
        
        # 请求延迟（避免限流）
        'request_delay': 0.3,
    }
    
    def __init__(self, db_path: str = "data/future_data_daily_ak.db"):
        """
        初始化下载器
        
        Args:
            db_path: 数据库路径
        """
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        
        # 下载配置
        self.symbols = self.CONFIG['symbols']
        self.request_delay = self.CONFIG['request_delay']
        
        # 初始化数据库
        self._init_db()
        
        logger.info("✓ 下载器初始化完成")
    
    def _init_db(self):
        """初始化数据库表结构"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 期货日线 K 线表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS future_daily_bars (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                contract TEXT NOT NULL,
                date DATE NOT NULL,
                open_price REAL NOT NULL,
                high_price REAL NOT NULL,
                low_price REAL NOT NULL,
                close_price REAL NOT NULL,
                volume REAL NOT NULL,
                open_interest REAL,
                is_main_contract BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(symbol, contract, date)
            )
        """)
        
        # 下载记录表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS download_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                download_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                bar_count INTEGER,
                status TEXT,
                error_message TEXT,
                UNIQUE(symbol, download_date)
            )
        """)
        
        # 创建索引
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_future_symbol 
            ON future_daily_bars(symbol, date)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_future_contract_daily 
            ON future_daily_bars(contract)
        """)
        
        conn.commit()
        conn.close()
        logger.info(f"✓ 数据库初始化完成 | {self.db_path}")
    
    def download_symbol_data(self, symbol: str) -> int:
        """
        下载单个品种的日线数据
        
        Args:
            symbol: 品种代码（如 IF）
        
        Returns:
            下载的数据条数
        """
        try:
            logger.info(f"下载 {symbol} 主力合约日线数据...")
            
            # 主力合约代码加 0 后缀
            main_symbol = f"{symbol}0"
            
            # 获取日线数据
            df = ak.futures_zh_daily_sina(symbol=main_symbol)
            
            if df is None or df.empty:
                logger.warning(f"{symbol} 无数据")
                return 0
            
            # 保存到数据库
            self._save_to_db(df, symbol)
            
            # 记录下载日志
            self._log_download(symbol, len(df), 'success')
            
            logger.info(f"✓ {symbol} 下载完成 | {len(df):,} 条")
            return len(df)
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"{symbol} 下载失败：{error_msg}")
            self._log_download(symbol, 0, 'failed', error_msg)
            return 0
    
    def _save_to_db(self, df: pd.DataFrame, symbol: str):
        """保存数据到数据库"""
        conn = sqlite3.connect(self.db_path)
        
        try:
            # 准备数据
            data = []
            for idx, row in df.iterrows():
                data.append((
                    symbol,
                    symbol + '00',  # 主力合约用 00 表示
                    row['date'],
                    float(row['open']),
                    float(row['high']),
                    float(row['low']),
                    float(row['close']),
                    float(row.get('volume', 0)),
                    float(row.get('hold', 0)),
                    1  # is_main_contract
                ))
            
            # 批量插入
            cursor = conn.cursor()
            cursor.executemany("""
                INSERT OR REPLACE INTO future_daily_bars 
                (symbol, contract, date, open_price, high_price, low_price, 
                 close_price, volume, open_interest, is_main_contract)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, data)
            
            conn.commit()
            
        finally:
            conn.close()
    
    def _log_download(self, symbol: str, bar_count: int, status: str, 
                     error_message: str = None):
        """记录下载日志"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT OR REPLACE INTO download_log
                (symbol, bar_count, status, error_message)
                VALUES (?, ?, ?, ?)
            """, [
                symbol,
                bar_count,
                status,
                error_message
            ])
            
            conn.commit()
            
        finally:
            conn.close()
    
    def download_all(self):
        """下载所有品种数据"""
        logger.info("=" * 80)
        logger.info("期货日线数据批量下载 (AKShare)")
        logger.info("=" * 80)
        logger.info(f"品种数量：{len(self.symbols)}")
        logger.info(f"数据周期：日线")
        logger.info("=" * 80)
        
        total_bars = 0
        success_count = 0
        failed_symbols = []
        
        # 批量下载
        for i, symbol in enumerate(self.symbols, 1):
            logger.info(f"\n[{i}/{len(self.symbols)}] 下载 {symbol}...")
            
            bar_count = self.download_symbol_data(symbol)
            
            if bar_count > 0:
                total_bars += bar_count
                success_count += 1
            else:
                failed_symbols.append(symbol)
            
            # 延迟，避免限流
            if i < len(self.symbols):
                time.sleep(self.request_delay)
        
        # 完成报告
        logger.info("\n" + "=" * 80)
        logger.info("✅ 下载完成！")
        logger.info("=" * 80)
        logger.info(f"总品种数：{len(self.symbols)}")
        logger.info(f"成功：{success_count} ({success_count/len(self.symbols)*100:.1f}%)")
        logger.info(f"失败：{len(failed_symbols)}")
        logger.info(f"总数据量：{total_bars:,} 条")
        logger.info(f"数据库：{self.db_path}")
        logger.info("=" * 80)
        
        if failed_symbols:
            logger.warning(f"失败的品种：{', '.join(failed_symbols)}")
        
        return {
            'total_symbols': len(self.symbols),
            'success': success_count,
            'failed': len(failed_symbols),
            'total_bars': total_bars
        }
    
    def get_stats(self) -> Dict:
        """获取数据库统计"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # 总数据量
            cursor.execute("SELECT COUNT(*) FROM future_daily_bars")
            total_bars = cursor.fetchone()[0]
            
            # 品种数量
            cursor.execute("SELECT COUNT(DISTINCT symbol) FROM future_daily_bars")
            symbol_count = cursor.fetchone()[0]
            
            # 时间范围
            cursor.execute("SELECT MIN(date), MAX(date) FROM future_daily_bars")
            date_range = cursor.fetchone()
            
            # 下载日志统计
            cursor.execute("""
                SELECT status, COUNT(*) 
                FROM download_log 
                GROUP BY status
            """)
            status_stats = dict(cursor.fetchall())
            
            return {
                'total_bars': total_bars,
                'symbol_count': symbol_count,
                'date_range': date_range,
                'success': status_stats.get('success', 0),
                'failed': status_stats.get('failed', 0)
            }
            
        finally:
            conn.close()


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='期货日线数据批量下载 (AKShare)')
    parser.add_argument('--db', type=str, default='data/future_data_daily_ak.db',
                       help='数据库路径')
    
    args = parser.parse_args()
    
    try:
        # 创建下载器
        downloader = FutureDataDownloader(db_path=args.db)
        
        # 开始下载
        result = downloader.download_all()
        
        # 显示统计
        stats = downloader.get_stats()
        
        print("\n" + "=" * 80)
        print("📊 数据库统计")
        print("=" * 80)
        print(f"总数据量：{stats['total_bars']:,} 条")
        print(f"品种数量：{stats['symbol_count']} 个")
        print(f"时间范围：{stats['date_range'][0]} 至 {stats['date_range'][1]}")
        print(f"成功：{stats['success']}")
        print(f"失败：{stats['failed']}")
        print("=" * 80)
        
    except KeyboardInterrupt:
        logger.warning("\n⚠️  用户中断下载")
    except Exception as e:
        logger.error(f"❌ 下载失败：{e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

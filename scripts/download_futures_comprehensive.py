#!/usr/bin/env python3
"""
期货数据全面下载器

下载所有可用期货品种的多周期数据:
- 日线 (2020 至今)
- 60 分钟线 (2020 至今)
- 15 分钟线 (最近 30 天)
- 5 分钟线 (最近 7 天)

覆盖品种:
- 金融期货：IF/IC/IH/IM (股指), T/TF/TL (国债)
- 金属：CU/AL/ZN/PB/NI/SN/AU/AG/RB/HC/SS
- 能源：SC/LU/FU/NR
- 农产品：M/Y/P/C/CS/A/B/JD/L/V/PP/EG/EB
- 化工：SR/CF/OI/MA/FG/SA/AP/SF/SM
- 其他：EB/PG/RR/FB
"""
import akshare as ak
import pandas as pd
import sqlite3
import logging
from datetime import datetime, timedelta
from pathlib import Path
from tqdm import tqdm
import time
from typing import List, Dict

# 配置
DB_PATH = Path("data/future_comprehensive.db")
LOG_DIR = Path("logs")
LOG_DIR.mkdir(parents=True, exist_ok=True)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    handlers=[
        logging.FileHandler(LOG_DIR / f'futures_comprehensive_{datetime.now().strftime("%Y%m%d_%H%M")}.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


# 期货品种分类
FUTURE_CATEGORIES = {
    '金融期货': ['IF', 'IC', 'IH', 'IM', 'T', 'TF', 'TL'],
    '有色金属': ['CU', 'AL', 'ZN', 'PB', 'NI', 'SN'],
    '贵金属': ['AU', 'AG'],
    '黑色金属': ['RB', 'HC', 'SS', 'WR'],
    '能源化工': ['SC', 'LU', 'FU', 'NR', 'BU'],
    '农产品': ['M', 'Y', 'P', 'C', 'CS', 'A', 'B', 'JD', 'L', 'V', 'PP', 'EG', 'EB', 'PG'],
    '软商品': ['SR', 'CF', 'OI', 'RM', 'ZC'],
    '其他': ['MA', 'FG', 'SA', 'AP', 'SF', 'SM', 'EB', 'RR', 'FB', 'WH', 'PM', 'JR', 'RI'],
}


class FuturesDownloader:
    """期货数据下载器"""
    
    def __init__(self):
        self.db_path = DB_PATH
        self._init_db()
    
    def _init_db(self):
        """初始化数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 日线表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS daily_bars (
                id INTEGER PRIMARY KEY,
                symbol TEXT NOT NULL,
                category TEXT,
                date DATE NOT NULL,
                open REAL,
                high REAL,
                low REAL,
                close REAL,
                volume REAL,
                hold REAL,
                settle REAL,
                UNIQUE(symbol, date)
            )
        ''')
        
        # 60 分钟线表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS hourly_bars (
                id INTEGER PRIMARY KEY,
                symbol TEXT NOT NULL,
                datetime TIMESTAMP NOT NULL,
                open REAL,
                high REAL,
                low REAL,
                close REAL,
                volume REAL,
                hold REAL,
                UNIQUE(symbol, datetime)
            )
        ''')
        
        # 15 分钟线表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS min15_bars (
                id INTEGER PRIMARY KEY,
                symbol TEXT NOT NULL,
                datetime TIMESTAMP NOT NULL,
                open REAL,
                high REAL,
                low REAL,
                close REAL,
                volume REAL,
                hold REAL,
                UNIQUE(symbol, datetime)
            )
        ''')
        
        # 5 分钟线表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS min5_bars (
                id INTEGER PRIMARY KEY,
                symbol TEXT NOT NULL,
                datetime TIMESTAMP NOT NULL,
                open REAL,
                high REAL,
                low REAL,
                close REAL,
                volume REAL,
                hold REAL,
                UNIQUE(symbol, datetime)
            )
        ''')
        
        # 品种信息表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS symbol_info (
                symbol TEXT PRIMARY KEY,
                name TEXT,
                category TEXT,
                exchange TEXT,
                multiplier REAL
            )
        ''')
        
        conn.commit()
        conn.close()
        logger.info(f"✅ 数据库初始化完成 | {self.db_path}")
    
    def _retry_request(self, func, *args, max_retries=3, delay=2.0, **kwargs):
        """带重试的请求"""
        for attempt in range(max_retries):
            try:
                result = func(*args, **kwargs)
                if result is not None and len(result) > 0:
                    return result
                raise ValueError("空结果")
            except Exception as e:
                if attempt < max_retries - 1:
                    wait_time = delay * (attempt + 1)
                    logger.warning(f"⚠️  重试 ({attempt+1}/{max_retries}) | {wait_time}秒后...")
                    time.sleep(wait_time)
                else:
                    logger.error(f"❌ 失败 (已重试{max_retries}次) | {e}")
                    return None
    
    def download_daily(self, symbol: str, category: str) -> bool:
        """下载日线数据"""
        try:
            main_symbol = f"{symbol}0"
            
            df = self._retry_request(
                ak.futures_zh_daily_sina,
                symbol=main_symbol
            )
            
            if df is not None and len(df) > 0:
                conn = sqlite3.connect(self.db_path)
                
                df['symbol'] = main_symbol
                df['category'] = category
                
                df.to_sql('daily_bars', conn, if_exists='append', index=False, method='ignore')
                
                conn.commit()
                conn.close()
                
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"❌ {symbol} 日线失败：{e}")
            return False
    
    def download_minute(self, symbol: str, category: str, period: str = "60", 
                       days: int = 30) -> bool:
        """下载分钟线数据"""
        try:
            main_symbol = f"{symbol}0"
            
            # 计算开始日期
            start_date = (datetime.now() - timedelta(days=days)).strftime('%Y%m%d')
            
            df = self._retry_request(
                ak.futures_zh_minute_sina,
                symbol=main_symbol,
                period=period
            )
            
            if df is not None and len(df) > 0:
                # 过滤日期
                df['datetime'] = pd.to_datetime(df['date'])
                df = df[df['datetime'] >= start_date]
                
                if len(df) > 0:
                    conn = sqlite3.connect(self.db_path)
                    
                    df['symbol'] = main_symbol
                    df['category'] = category
                    
                    table_name = f"min{period}_bars"
                    df.to_sql(table_name, conn, if_exists='append', index=False, method='ignore')
                    
                    conn.commit()
                    conn.close()
                    
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"❌ {symbol} {period}分钟线失败：{e}")
            return False
    
    def download_all(self):
        """下载所有期货数据"""
        logger.info("="*70)
        logger.info("期货数据全面下载")
        logger.info("="*70)
        
        total_symbols = sum(len(v) for v in FUTURE_CATEGORIES.values())
        logger.info(f"总品种数：{total_symbols}")
        logger.info(f"类别：{list(FUTURE_CATEGORIES.keys())}")
        logger.info("="*70)
        
        # Phase 1: 日线数据
        logger.info("\n📊 Phase 1: 下载日线数据 (2020 至今)")
        logger.info("-"*70)
        
        daily_success = 0
        daily_total = 0
        
        for category, symbols in FUTURE_CATEGORIES.items():
            logger.info(f"\n【{category}】{len(symbols)} 个品种")
            
            for symbol in tqdm(symbols, desc=category):
                daily_total += 1
                if self.download_daily(symbol, category):
                    daily_success += 1
                    logger.info(f"   ✓ {symbol}")
                else:
                    logger.info(f"   ✗ {symbol}")
                time.sleep(0.3)
        
        logger.info(f"\n✅ 日线完成 | 成功={daily_success}/{daily_total}")
        
        # Phase 2: 60 分钟线
        logger.info("\n⏱️  Phase 2: 下载 60 分钟线 (最近 90 天)")
        logger.info("-"*70)
        
        hourly_success = 0
        hourly_total = 0
        
        for category, symbols in FUTURE_CATEGORIES.items():
            for symbol in tqdm(symbols, desc=f"{category} 60m"):
                hourly_total += 1
                if self.download_minute(symbol, category, period="60", days=90):
                    hourly_success += 1
                time.sleep(0.3)
        
        logger.info(f"✅ 60 分钟线完成 | 成功={hourly_success}/{hourly_total}")
        
        # Phase 3: 15 分钟线
        logger.info("\n⏱️  Phase 3: 下载 15 分钟线 (最近 30 天)")
        logger.info("-"*70)
        
        min15_success = 0
        min15_total = 0
        
        for category, symbols in FUTURE_CATEGORIES.items():
            for symbol in tqdm(symbols, desc=f"{category} 15m"):
                min15_total += 1
                if self.download_minute(symbol, category, period="15", days=30):
                    min15_success += 1
                time.sleep(0.3)
        
        logger.info(f"✅ 15 分钟线完成 | 成功={min15_success}/{min15_total}")
        
        # Phase 4: 5 分钟线
        logger.info("\n⏱️  Phase 4: 下载 5 分钟线 (最近 7 天)")
        logger.info("-"*70)
        
        min5_success = 0
        min5_total = 0
        
        for category, symbols in FUTURE_CATEGORIES.items():
            for symbol in tqdm(symbols, desc=f"{category} 5m"):
                min5_total += 1
                if self.download_minute(symbol, category, period="5", days=7):
                    min5_success += 1
                time.sleep(0.3)
        
        logger.info(f"✅ 5 分钟线完成 | 成功={min5_success}/{min5_total}")
        
        # 汇总
        self.show_summary()
    
    def show_summary(self):
        """显示下载汇总"""
        logger.info("\n" + "="*70)
        logger.info("📊 期货数据下载汇总")
        logger.info("="*70)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        tables = ['daily_bars', 'hourly_bars', 'min15_bars', 'min5_bars']
        
        for table in tables:
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                logger.info(f"   {table}: {count:,} 条")
            except:
                logger.info(f"   {table}: 无数据")
        
        conn.close()
        
        # 文件大小
        db_size = self.db_path.stat().st_size / 1024 / 1024
        logger.info(f"\n   数据库大小：{db_size:.2f} MB")
        logger.info("="*70)


def main():
    """主函数"""
    downloader = FuturesDownloader()
    downloader.download_all()


if __name__ == "__main__":
    main()

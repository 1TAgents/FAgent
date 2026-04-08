#!/usr/bin/env python3
"""
聚宽 (JoinQuant) 数据下载器

下载对 FAgent 最有价值的数据：
1. 股票日线 + 分钟线
2. 指数数据
3. 北向资金
4. 龙虎榜
5. 基本面数据

用法:
    python3 scripts/joinquant_download.py --username YOUR_USER --password YOUR_PASS
"""
import jqdatasdk as jq
import pandas as pd
import sqlite3
import argparse
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional
import time

# 配置日志
log_dir = Path('logs')
log_dir.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_dir / 'joinquant_download.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class JoinQuantDownloader:
    """聚宽数据下载器"""
    
    def __init__(self, username: str, password: str, db_path: str = "data/joinquant_data.db"):
        """初始化"""
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        
        # 登录聚宽
        try:
            jq.auth(username, password)
            logger.info("✅ 聚宽登录成功")
        except Exception as e:
            logger.error(f"❌ 聚宽登录失败：{e}")
            raise
        
        # 初始化数据库
        self._init_db()
    
    def _init_db(self):
        """初始化数据库表"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 股票日线表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS stock_daily (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                date DATE NOT NULL,
                open REAL,
                close REAL,
                high REAL,
                low REAL,
                volume REAL,
                money REAL,
                factor REAL,
                UNIQUE(symbol, date)
            )
        ''')
        
        # 股票分钟线表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS stock_minute (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                datetime TIMESTAMP NOT NULL,
                open REAL,
                close REAL,
                high REAL,
                low REAL,
                volume REAL,
                money REAL,
                UNIQUE(symbol, datetime)
            )
        ''')
        
        # 指数日线表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS index_daily (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                date DATE NOT NULL,
                open REAL,
                close REAL,
                high REAL,
                low REAL,
                volume REAL,
                money REAL,
                UNIQUE(symbol, date)
            )
        ''')
        
        # 北向资金表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS north_money_flow (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date DATE NOT NULL,
                north_net_in REAL,
                north_buy REAL,
                north_sell REAL,
                UNIQUE(date)
            )
        ''')
        
        # 龙虎榜表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS billboard (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date DATE NOT NULL,
                symbol TEXT NOT NULL,
                name TEXT,
                net_amount REAL,
                buy_amount REAL,
                sell_amount REAL,
                reason TEXT,
                UNIQUE(date, symbol)
            )
        ''')
        
        # 股票信息表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS stock_info (
                symbol TEXT PRIMARY KEY,
                name TEXT,
                start_date DATE,
                end_date DATE,
                type TEXT,
                parent_code TEXT,
                exchange TEXT
            )
        ''')
        
        # 基本面数据表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS fundamentals (
                symbol TEXT PRIMARY KEY,
                date DATE,
                pe_ratio REAL,
                pb_ratio REAL,
                ps_ratio REAL,
                market_cap REAL,
                circulating_market_cap REAL,
                roe REAL,
                eps REAL,
                bvps REAL,
                industry TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
        logger.info(f"✅ 数据库初始化完成 | {self.db_path}")
    
    def download_stock_list(self) -> List[str]:
        """下载股票列表"""
        logger.info("📋 获取 A 股股票列表...")
        
        conn = sqlite3.connect(self.db_path)
        
        try:
            stocks = jq.get_all_securities(types=['stock'], date=datetime.now())
            
            # 保存到数据库
            stocks_df = stocks.reset_index()
            stocks_df.columns = ['symbol', 'name', 'start_date', 'end_date', 'type', 'parent_code', 'exchange']
            stocks_df.to_sql('stock_info', conn, if_exists='replace', index=False)
            
            stock_codes = stocks_df['symbol'].tolist()
            logger.info(f"✅ 获取到 {len(stock_codes)} 只 A 股股票")
            return stock_codes
            
        except Exception as e:
            logger.error(f"❌ 获取股票列表失败：{e}")
            return []
        finally:
            conn.close()
    
    def download_index_list(self) -> List[str]:
        """下载指数列表"""
        logger.info("📊 获取指数列表...")
        
        conn = sqlite3.connect(self.db_path)
        
        try:
            indices = jq.get_all_securities(types=['index'], date=datetime.now())
            
            # 保存到数据库
            indices_df = indices.reset_index()
            indices_df.columns = ['symbol', 'name', 'start_date', 'end_date', 'type', 'parent_code', 'exchange']
            indices_df.to_sql('index_info', conn, if_exists='replace', index=False)
            
            index_codes = indices_df['symbol'].tolist()
            logger.info(f"✅ 获取到 {len(index_codes)} 个指数")
            return index_codes
            
        except Exception as e:
            logger.error(f"❌ 获取指数列表失败：{e}")
            return []
        finally:
            conn.close()
    
    def download_stock_daily(self, symbols: List[str], start_date: str = "2020-01-01", batch_size: int = 100):
        """下载股票日线数据"""
        logger.info(f"📈 开始下载股票日线数据 | {len(symbols)} 只股票 | {start_date} 至今")
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        success_count = 0
        failed_symbols = []
        
        # 分批下载
        for i in range(0, len(symbols), batch_size):
            batch = symbols[i:i+batch_size]
            try:
                logger.info(f"   批次 {i//batch_size + 1}/{(len(symbols)-1)//batch_size + 1}")
                
                # 批量获取日线数据
                df = jq.get_price(batch, start_date=start_date, end_date=datetime.now().strftime('%Y-%m-%d'), 
                                 frequency='daily', fields=['open', 'close', 'high', 'low', 'volume', 'money', 'factor'])
                
                if df is not None and len(df) > 0:
                    # 数据转换
                    df_reset = df.reset_index()
                    df_reset.columns = ['date', 'symbol', 'open', 'close', 'high', 'low', 'volume', 'money', 'factor']
                    
                    # 保存到数据库
                    df_reset.to_sql('stock_daily', conn, if_exists='append', index=False, method='ignore')
                    
                    success_count += len(df_reset) // len(batch)
                    logger.info(f"   ✓ 本批次成功下载 {len(df_reset)//len(batch)} 只股票")
                
                # 避免限流
                time.sleep(0.5)
                
            except Exception as e:
                logger.error(f"   ❌ 批次失败：{e}")
                failed_symbols.extend(batch)
        
        conn.commit()
        conn.close()
        
        logger.info(f"✅ 日线下载完成 | 成功 {success_count} 只 | 失败 {len(failed_symbols)} 只")
        if failed_symbols:
            logger.warning(f"   失败股票：{failed_symbols[:10]}...")
    
    def download_index_daily(self, symbols: List[str], start_date: str = "2020-01-01"):
        """下载指数日线数据"""
        logger.info(f"📊 下载指数日线 | {len(symbols)} 个指数")
        
        conn = sqlite3.connect(self.db_path)
        
        for symbol in symbols:
            try:
                df = jq.get_price(symbol, start_date=start_date, end_date=datetime.now().strftime('%Y-%m-%d'),
                                 frequency='daily', fields=['open', 'close', 'high', 'low', 'volume', 'money'])
                
                if df is not None and len(df) > 0:
                    df_reset = df.reset_index()
                    df_reset['symbol'] = symbol
                    df_reset.columns = ['date', 'open', 'close', 'high', 'low', 'volume', 'money', 'symbol']
                    df_reset = df_reset[['symbol', 'date', 'open', 'close', 'high', 'low', 'volume', 'money']]
                    
                    df_reset.to_sql('index_daily', conn, if_exists='append', index=False, method='ignore')
                
                time.sleep(0.3)
                
            except Exception as e:
                logger.error(f"   ❌ {symbol} 失败：{e}")
        
        conn.commit()
        conn.close()
        logger.info("✅ 指数日线下载完成")
    
    def download_north_money_flow(self, start_date: str = "2020-01-01"):
        """下载北向资金数据"""
        logger.info(f"💰 下载北向资金数据 | {start_date} 至今")
        
        conn = sqlite3.connect(self.db_path)
        
        try:
            df = jq.get_north_money_flow(start_date=start_date, end_date=datetime.now().strftime('%Y-%m-%d'))
            
            if df is not None and len(df) > 0:
                # 重命名列
                df.columns = ['date', 'north_net_in', 'north_buy', 'north_sell']
                df.to_sql('north_money_flow', conn, if_exists='replace', index=False)
                logger.info(f"✅ 北向资金下载完成 | {len(df)} 条")
            else:
                logger.warning("⚠️  无北向资金数据")
            
        except Exception as e:
            logger.error(f"❌ 北向资金下载失败：{e}")
        finally:
            conn.close()
    
    def download_billboard(self, start_date: str = "2023-01-01"):
        """下载龙虎榜数据"""
        logger.info(f"📋 下载龙虎榜数据 | {start_date} 至今")
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 按月下载
        start = datetime.strptime(start_date, '%Y-%m-%d')
        end = datetime.now()
        
        current = start
        total_rows = 0
        
        while current < end:
            month_end = min(current.replace(day=28) + timedelta(days=4), end)
            month_end = month_end.replace(day=1) - timedelta(days=1)
            
            try:
                df = jq.get_billboard_list(start_date=current.strftime('%Y-%m-%d'), 
                                          end_date=month_end.strftime('%Y-%m-%d'))
                
                if df is not None and len(df) > 0:
                    df_reset = df.reset_index()
                    df_reset.columns = ['date', 'symbol', 'name', 'net_amount', 'buy_amount', 'sell_amount', 'reason']
                    df_reset = df_reset[['date', 'symbol', 'name', 'net_amount', 'buy_amount', 'sell_amount', 'reason']]
                    
                    df_reset.to_sql('billboard', conn, if_exists='append', index=False, method='ignore')
                    total_rows += len(df_reset)
                    logger.info(f"   ✓ {current.strftime('%Y-%m')} 月：{len(df_reset)} 条")
                
                time.sleep(0.3)
                
            except Exception as e:
                logger.error(f"   ❌ {current.strftime('%Y-%m')} 失败：{e}")
            
            current = month_end + timedelta(days=1)
            if current > end:
                break
        
        conn.commit()
        conn.close()
        logger.info(f"✅ 龙虎榜下载完成 | 共 {total_rows} 条")
    
    def download_fundamentals(self, symbols: List[str], date: str = None):
        """下载基本面数据"""
        if date is None:
            date = datetime.now().strftime('%Y-%m-%d')
        
        logger.info(f"💵 下载基本面数据 | 日期：{date}")
        
        conn = sqlite3.connect(self.db_path)
        
        success_count = 0
        
        for i, symbol in enumerate(symbols):
            try:
                # 获取估值指标
                valuation = jq.get_valuation(symbol, date=date)
                
                if valuation is not None and len(valuation) > 0:
                    row = valuation.iloc[0]
                    
                    cursor = conn.cursor()
                    cursor.execute('''
                        INSERT OR REPLACE INTO fundamentals 
                        (symbol, date, pe_ratio, pb_ratio, ps_ratio, market_cap, 
                         circulating_market_cap, roe, eps, bvps, industry)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        symbol, date,
                        row.get('pe_ratio', None),
                        row.get('pb_ratio', None),
                        row.get('ps_ratio', None),
                        row.get('market_cap', None),
                        row.get('circulating_market_cap', None),
                        row.get('roe', None),
                        row.get('eps', None),
                        row.get('bvps', None),
                        row.get('industry', None)
                    ))
                    
                    success_count += 1
                
                if (i + 1) % 100 == 0:
                    conn.commit()
                    logger.info(f"   进度：{i+1}/{len(symbols)}")
                
                time.sleep(0.1)  # 避免限流
                
            except Exception as e:
                logger.error(f"   ❌ {symbol} 失败：{e}")
        
        conn.commit()
        conn.close()
        logger.info(f"✅ 基本面数据下载完成 | 成功 {success_count}/{len(symbols)}")
    
    def download_stock_minute(self, symbols: List[str], days: int = 30, frequency: str = '60m'):
        """下载股票分钟线数据"""
        logger.info(f"⏱️  下载股票分钟线 | {len(symbols)} 只 | {frequency} | 最近 {days} 天")
        
        conn = sqlite3.connect(self.db_path)
        
        start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        
        success_count = 0
        
        # 分批下载
        batch_size = 50
        for i in range(0, len(symbols), batch_size):
            batch = symbols[i:i+batch_size]
            try:
                df = jq.get_price(batch, start_date=start_date, end_date=datetime.now().strftime('%Y-%m-%d'),
                                 frequency=frequency, fields=['open', 'close', 'high', 'low', 'volume', 'money'])
                
                if df is not None and len(df) > 0:
                    df_reset = df.reset_index()
                    df_reset.columns = ['datetime', 'symbol', 'open', 'close', 'high', 'low', 'volume', 'money']
                    
                    df_reset.to_sql('stock_minute', conn, if_exists='append', index=False, method='ignore')
                    success_count += len(df_reset) // len(batch)
                
                time.sleep(0.5)
                
            except Exception as e:
                logger.error(f"   ❌ 批次失败：{e}")
        
        conn.commit()
        conn.close()
        logger.info(f"✅ 分钟线下载完成 | 成功 {success_count} 只")
    
    def show_summary(self):
        """显示数据摘要"""
        logger.info("\n" + "="*60)
        logger.info("📊 聚宽数据下载汇总")
        logger.info("="*60)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        tables = ['stock_info', 'stock_daily', 'stock_minute', 'index_info', 'index_daily', 
                  'north_money_flow', 'billboard', 'fundamentals']
        
        for table in tables:
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                logger.info(f"   {table}: {count:,} 条")
            except:
                logger.info(f"   {table}: 无数据")
        
        conn.close()
        
        # 文件大小
        db_size = Path(self.db_path).stat().st_size / 1024 / 1024
        logger.info(f"\n   数据库大小：{db_size:.2f} MB")


def main():
    parser = argparse.ArgumentParser(description='聚宽数据下载器')
    parser.add_argument('--username', '-u', required=True, help='聚宽账号')
    parser.add_argument('--password', '-p', required=True, help='聚宽密码')
    parser.add_argument('--db', default='data/joinquant_data.db', help='数据库路径')
    parser.add_argument('--start-date', default='2020-01-01', help='开始日期')
    parser.add_argument('--minute-days', type=int, default=30, help='分钟线下载天数')
    parser.add_argument('--all', action='store_true', help='下载所有数据')
    parser.add_argument('--stocks', action='store_true', help='只下载股票数据')
    parser.add_argument('--index', action='store_true', help='只下载指数数据')
    parser.add_argument('--north', action='store_true', help='只下载北向资金')
    parser.add_argument('--billboard', action='store_true', help='只下载龙虎榜')
    parser.add_argument('--fundamentals', action='store_true', help='只下载基本面')
    
    args = parser.parse_args()
    
    # 初始化下载器
    downloader = JoinQuantDownloader(args.username, args.password, args.db)
    
    # 下载股票列表
    stock_list = downloader.download_stock_list()
    index_list = downloader.download_index_list()
    
    # 根据参数下载
    if args.all or args.stocks:
        downloader.download_stock_daily(stock_list, start_date=args.start_date)
        downloader.download_stock_minute(stock_list[:500], days=args.minute_days)  # 先下载 500 只测试
    
    if args.all or args.index:
        # 下载主要指数
        major_indices = ['000001.XSHG', '000300.XSHG', '000905.XSHG', '399001.XSHE', '399006.XSHE']
        downloader.download_index_daily(major_indices, start_date=args.start_date)
    
    if args.all or args.north:
        downloader.download_north_money_flow(start_date=args.start_date)
    
    if args.all or args.billboard:
        downloader.download_billboard(start_date='2023-01-01')
    
    if args.all or args.fundamentals:
        downloader.download_fundamentals(stock_list[:1000])  # 先下载 1000 只
    
    # 显示汇总
    downloader.show_summary()


if __name__ == "__main__":
    main()

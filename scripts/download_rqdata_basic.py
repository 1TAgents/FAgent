#!/usr/bin/env python3
"""
聚宽数据批量下载工具 - 基础版
下载范围：A 股日线（2010-2026）、期货日线、财务数据、分红送配
预计时间：1-2 小时
预计数据量：~4000 万条
"""

import rqdatac as rq
import pandas as pd
import sqlite3
import logging
from datetime import datetime, timedelta
from pathlib import Path
from tqdm import tqdm
import time
import sys
from typing import List, Dict, Optional

# 配置日志
log_dir = Path('logs')
log_dir.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    handlers=[
        logging.FileHandler(log_dir / 'download_rqdata_basic.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class RQDataBasicDownloader:
    """聚宽基础数据下载器"""
    
    def __init__(self, db_path: str = "data/rqdata/database/daily_bars.db"):
        """初始化"""
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 初始化聚宽 - 使用 token 认证
        try:
            # License Key（从 test_rqdata_quick.py 复制）
            LICENSE_KEY = "YOUR_LICENSE_KEY"
            rq.init(username='token', password=LICENSE_KEY)
            logger.info("✓ RQData 初始化完成（token 认证）")
        except Exception as e:
            logger.error(f"RQData 初始化失败 | error={e}")
            logger.error("请检查 License Key 是否有效，或联系米筐支持：support@ricequant.com")
            raise
        
        # 限流控制
        self.last_request_time = 0
        self.qps_limit = 5  # 每秒 5 次请求（官方限制 10）
        
        # 初始化数据库
        self._init_database()
    
    def _rate_limit(self):
        """限流控制"""
        now = time.time()
        elapsed = now - self.last_request_time
        min_interval = 1.0 / self.qps_limit
        if elapsed < min_interval:
            time.sleep(min_interval - elapsed)
        self.last_request_time = time.time()
    
    def _init_database(self):
        """初始化数据库表结构"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 日线数据表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS daily_bars (
                id INTEGER PRIMARY KEY,
                symbol TEXT NOT NULL,
                exchange TEXT NOT NULL,
                datetime DATE NOT NULL,
                open REAL,
                high REAL,
                low REAL,
                close REAL,
                volume REAL,
                turnover REAL,
                open_interest REAL,
                adjust_type TEXT DEFAULT 'pre',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(symbol, exchange, datetime, adjust_type)
            )
        """)
        
        # 期货日线数据表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS futures_daily (
                id INTEGER PRIMARY KEY,
                symbol TEXT NOT NULL,
                exchange TEXT NOT NULL,
                datetime DATE NOT NULL,
                open REAL,
                high REAL,
                low REAL,
                close REAL,
                volume REAL,
                turnover REAL,
                open_interest REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(symbol, exchange, datetime)
            )
        """)
        
        # 财务数据表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS fundamentals (
                id INTEGER PRIMARY KEY,
                symbol TEXT NOT NULL,
                exchange TEXT NOT NULL,
                date DATE NOT NULL,
                pe_ratio REAL,
                pb_ratio REAL,
                market_cap REAL,
                dividend_yield REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(symbol, exchange, date)
            )
        """)
        
        # 分红数据表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS dividends (
                id INTEGER PRIMARY KEY,
                symbol TEXT NOT NULL,
                exchange TEXT NOT NULL,
                announcement_date DATE,
                record_date DATE,
                ex_dividend_date DATE,
                cash_dividend REAL,
                share_dividend REAL,
                allotted_share REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 创建索引
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_daily_symbol_date 
            ON daily_bars(symbol, exchange, datetime)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_futures_symbol_date 
            ON futures_daily(symbol, exchange, datetime)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_fundamentals_symbol 
            ON fundamentals(symbol, exchange, date)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_dividends_symbol 
            ON dividends(symbol, exchange)
        """)
        
        conn.commit()
        conn.close()
        logger.info(f"✓ 数据库初始化完成 | {self.db_path}")
    
    def download_all_stocks_daily(self, start_date: str, end_date: str, 
                                   adjust_type: str = 'pre'):
        """下载全部 A 股日线数据"""
        logger.info("=" * 80)
        logger.info(f"开始下载 A 股日线数据 | {start_date} 至 {end_date} | 复权：{adjust_type}")
        logger.info("=" * 80)
        
        # 获取股票列表
        stocks = rq.all_instruments(type='CS', market='cn')
        logger.info(f"✓ 获取到 {len(stocks)} 只 A 股股票")
        
        # 批量下载
        batch_size = 50
        success_count = 0
        failed_count = 0
        total_bars = 0
        
        pbar = tqdm(range(0, len(stocks), batch_size), desc="下载进度")
        
        for i in pbar:
            batch = stocks.iloc[i:i+batch_size]
            symbols = batch['order_book_id'].tolist()
            
            try:
                self._rate_limit()
                
                # 批量获取数据
                df = rq.get_price(
                    order_book_ids=symbols,
                    start_date=start_date,
                    end_date=end_date,
                    frequency='1d',
                    adjust_type=adjust_type,
                    expect_df=True
                )
                
                if df is not None and len(df) > 0:
                    # 保存到数据库
                    self._save_stocks_daily(df, adjust_type)
                    total_bars += len(df)
                    success_count += len(symbols)
                    
                    # 更新进度条
                    pbar.set_postfix({
                        '成功': success_count,
                        '失败': failed_count,
                        '数据量': f'{total_bars:,}'
                    })
                
            except Exception as e:
                logger.error(f"批次下载失败 | symbols={symbols[:5]}... | error={e}")
                failed_count += len(symbols)
        
        logger.info("=" * 80)
        logger.info(f"✅ A 股日线下载完成！")
        logger.info(f"总股票数：{len(stocks)}")
        logger.info(f"成功：{success_count} ({success_count/len(stocks)*100:.1f}%)")
        logger.info(f"失败：{failed_count} ({failed_count/len(stocks)*100:.1f}%)")
        logger.info(f"总数据量：{total_bars:,} 条")
        logger.info("=" * 80)
    
    def _save_stocks_daily(self, df: pd.DataFrame, adjust_type: str):
        """保存股票日线数据到数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        df_reset = df.reset_index()
        
        batch_data = []
        for _, row in df_reset.iterrows():
            symbol_exchange = row['order_book_id'].split('.')
            symbol = symbol_exchange[0]
            exchange = symbol_exchange[1] if len(symbol_exchange) > 1 else 'XSHG'
            
            batch_data.append((
                symbol, exchange, row['date'],
                row['open'], row['high'], row['low'], row['close'],
                row['volume'], row.get('turnover', 0), row.get('open_interest', 0),
                adjust_type
            ))
        
        # 批量插入
        cursor.executemany("""
            INSERT OR REPLACE INTO daily_bars 
            (symbol, exchange, datetime, open, high, low, close, 
             volume, turnover, open_interest, adjust_type)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, batch_data)
        
        conn.commit()
        conn.close()
    
    def download_futures_daily(self, start_date: str, end_date: str):
        """下载期货日线数据"""
        logger.info("=" * 80)
        logger.info(f"开始下载期货日线数据 | {start_date} 至 {end_date}")
        logger.info("=" * 80)
        
        # 获取所有期货合约
        futures = rq.all_instruments(type='Future')
        logger.info(f"✓ 获取到 {len(futures)} 个期货合约")
        
        # 按品种分组，只下载主力合约
        # 简化处理：下载所有合约
        batch_size = 20
        success_count = 0
        failed_count = 0
        total_bars = 0
        
        pbar = tqdm(range(0, len(futures), batch_size), desc="下载期货")
        
        for i in pbar:
            batch = futures.iloc[i:i+batch_size]
            symbols = batch['order_book_id'].tolist()
            
            try:
                self._rate_limit()
                
                df = rq.get_price(
                    order_book_ids=symbols,
                    start_date=start_date,
                    end_date=end_date,
                    frequency='1d',
                    expect_df=True
                )
                
                if df is not None and len(df) > 0:
                    self._save_futures_daily(df)
                    total_bars += len(df)
                    success_count += len(symbols)
                    
                    pbar.set_postfix({
                        '成功': success_count,
                        '失败': failed_count,
                        '数据量': f'{total_bars:,}'
                    })
                
            except Exception as e:
                logger.error(f"期货批次下载失败 | symbols={symbols[:3]}... | error={e}")
                failed_count += len(symbols)
        
        logger.info("=" * 80)
        logger.info(f"✅ 期货日线下载完成！")
        logger.info(f"成功：{success_count} | 失败：{failed_count}")
        logger.info(f"总数据量：{total_bars:,} 条")
        logger.info("=" * 80)
    
    def _save_futures_daily(self, df: pd.DataFrame):
        """保存期货日线数据"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        df_reset = df.reset_index()
        
        batch_data = []
        for _, row in df_reset.iterrows():
            symbol_exchange = row['order_book_id'].split('.')
            symbol = symbol_exchange[0]
            exchange = symbol_exchange[1] if len(symbol_exchange) > 1 else 'CFFEX'
            
            batch_data.append((
                symbol, exchange, row['date'],
                row['open'], row['high'], row['low'], row['close'],
                row['volume'], row.get('turnover', 0), row.get('open_interest', 0)
            ))
        
        cursor.executemany("""
            INSERT OR REPLACE INTO futures_daily 
            (symbol, exchange, datetime, open, high, low, close, 
             volume, turnover, open_interest)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, batch_data)
        
        conn.commit()
        conn.close()
    
    def download_fundamentals(self, start_date: str, end_date: str):
        """下载财务数据（估值指标）"""
        logger.info("=" * 80)
        logger.info(f"开始下载财务数据 | {start_date} 至 {end_date}")
        logger.info("=" * 80)
        
        from rqdatac import valuation, query
        
        # 获取交易日历
        trading_dates = rq.get_trading_dates(start_date=start_date, end_date=end_date)
        logger.info(f"✓ 获取到 {len(trading_dates)} 个交易日")
        
        success_count = 0
        failed_count = 0
        
        pbar = tqdm(trading_dates, desc="下载财务数据")
        
        for trade_date in pbar:
            try:
                self._rate_limit()
                
                fundamentals = rq.get_fundamentals(
                    query(
                        valuation.code,
                        valuation.pe_ratio,
                        valuation.pb_ratio,
                        valuation.market_cap,
                        valuation.dividend_yield
                    ),
                    date=trade_date
                )
                
                if fundamentals is not None and len(fundamentals) > 0:
                    self._save_fundamentals(fundamentals, trade_date)
                    success_count += 1
                    
                    pbar.set_postfix({'成功': success_count, '失败': failed_count})
                
            except Exception as e:
                logger.error(f"财务数据下载失败 | date={trade_date} | error={e}")
                failed_count += 1
        
        logger.info("=" * 80)
        logger.info(f"✅ 财务数据下载完成！")
        logger.info(f"成功：{success_count} 天 | 失败：{failed_count} 天")
        logger.info("=" * 80)
    
    def _save_fundamentals(self, df: pd.DataFrame, date: str):
        """保存财务数据"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        batch_data = []
        for _, row in df.iterrows():
            symbol = row['code']
            # 根据代码判断交易所
            if symbol.startswith('6') or symbol.startswith('9'):
                exchange = 'XSHG'
            else:
                exchange = 'XSHE'
            
            batch_data.append((
                symbol, exchange, date,
                row.get('pe_ratio'), row.get('pb_ratio'),
                row.get('market_cap'), row.get('dividend_yield')
            ))
        
        cursor.executemany("""
            INSERT OR REPLACE INTO fundamentals 
            (symbol, exchange, date, pe_ratio, pb_ratio, market_cap, dividend_yield)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, batch_data)
        
        conn.commit()
        conn.close()
    
    def download_dividends(self):
        """下载全部分红送配数据"""
        logger.info("=" * 80)
        logger.info("开始下载分红送配数据（全历史）")
        logger.info("=" * 80)
        
        stocks = rq.all_instruments(type='CS', market='cn')
        logger.info(f"✓ 获取到 {len(stocks)} 只股票")
        
        success_count = 0
        failed_count = 0
        total_dividends = 0
        
        pbar = tqdm(stocks.iterrows(), total=len(stocks), desc="下载分红")
        
        for _, stock in pbar:
            symbol = stock['order_book_id']
            
            try:
                self._rate_limit()
                
                dividends = rq.get_dividends(symbol)
                
                if dividends and len(dividends) > 0:
                    self._save_dividends(symbol, dividends)
                    success_count += 1
                    total_dividends += len(dividends)
                    
                    pbar.set_postfix({
                        '成功': success_count,
                        '分红记录': f'{total_dividends:,}'
                    })
                
            except Exception as e:
                logger.warning(f"分红数据下载失败 | symbol={symbol} | error={e}")
                failed_count += 1
        
        logger.info("=" * 80)
        logger.info(f"✅ 分红数据下载完成！")
        logger.info(f"成功：{success_count}/{len(stocks)}")
        logger.info(f"失败：{failed_count}")
        logger.info(f"总分红记录：{total_dividends:,} 条")
        logger.info("=" * 80)
    
    def _save_dividends(self, symbol: str, dividends: List[Dict]):
        """保存分红数据"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        symbol_exchange = symbol.split('.')
        symbol_code = symbol_exchange[0]
        exchange = symbol_exchange[1] if len(symbol_exchange) > 1 else 'XSHG'
        
        batch_data = []
        for div in dividends:
            batch_data.append((
                symbol_code, exchange,
                div.get('announcement_date'),
                div.get('record_date'),
                div.get('ex_dividend_date'),
                div.get('cash_dividend', 0),
                div.get('share_dividend', 0),
                div.get('allotted_share', 0)
            ))
        
        cursor.executemany("""
            INSERT INTO dividends 
            (symbol, exchange, announcement_date, record_date, ex_dividend_date,
             cash_dividend, share_dividend, allotted_share)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, batch_data)
        
        conn.commit()
        conn.close()


def main():
    """主函数"""
    logger.info("=" * 80)
    logger.info("聚宽数据批量下载工具 - 基础版")
    logger.info("下载范围：A 股日线 + 期货日线 + 财务数据 + 分红送配")
    logger.info("预计时间：1-2 小时")
    logger.info("=" * 80)
    
    downloader = RQDataBasicDownloader()
    
    # 1. 下载 A 股日线数据（2010-2026）
    downloader.download_all_stocks_daily(
        start_date='2010-01-01',
        end_date='2026-03-25',
        adjust_type='pre'
    )
    
    # 2. 下载期货日线数据（2015-2026）
    downloader.download_futures_daily(
        start_date='2015-01-01',
        end_date='2026-03-25'
    )
    
    # 3. 下载财务数据（2010-2026）
    downloader.download_fundamentals(
        start_date='2010-01-01',
        end_date='2026-03-25'
    )
    
    # 4. 下载分红数据（全历史）
    downloader.download_dividends()
    
    logger.info("=" * 80)
    logger.info("✅ 全部下载完成！")
    logger.info(f"数据库位置：{downloader.db_path.absolute()}")
    logger.info("=" * 80)


if __name__ == '__main__':
    main()

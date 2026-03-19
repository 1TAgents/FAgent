#!/usr/bin/env python3
"""
RQSDK 批量下载 A 股历史数据

下载所有 A 股最近 10 年的日线数据
- 支持进度显示
- 限制并发，避免触发限流
- 自动重试失败请求
- 保存到 SQLite 数据库
"""
import rqdatac as rq
import sqlite3
import pandas as pd
import time
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class StockDataDownloader:
    """股票数据下载器"""
    
    def __init__(self, db_path: str = "data/stock_data.db"):
        """
        初始化下载器
        
        Args:
            db_path: 数据库路径
        """
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        
        # 下载配置
        self.start_date = (datetime.now() - timedelta(days=365*10)).strftime('%Y-%m-%d')
        self.end_date = datetime.now().strftime('%Y-%m-%d')
        self.batch_size = 50  # 每批下载数量
        self.retry_count = 3  # 失败重试次数
        self.retry_delay = 2  # 重试间隔（秒）
        self.request_delay = 0.5  # 请求间隔（秒），避免触发限流
        
        # 初始化数据库
        self._init_db()
        
        # 初始化 RQSDK
        rq.init()
        logger.info("RQSDK 初始化完成")
    
    def _init_db(self):
        """初始化数据库表结构"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 创建 K 线数据表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS bar_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                exchange TEXT NOT NULL,
                datetime TIMESTAMP NOT NULL,
                interval TEXT NOT NULL,
                open_price REAL NOT NULL,
                high_price REAL NOT NULL,
                low_price REAL NOT NULL,
                close_price REAL NOT NULL,
                volume REAL NOT NULL,
                turnover REAL,
                open_interest REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(symbol, exchange, datetime, interval)
            )
        """)
        
        # 创建下载记录表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS download_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                download_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                start_date TEXT,
                end_date TEXT,
                bar_count INTEGER,
                status TEXT,
                error_message TEXT,
                UNIQUE(symbol, start_date, end_date)
            )
        """)
        
        # 创建索引
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_bar_symbol 
            ON bar_data(symbol, exchange)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_bar_datetime 
            ON bar_data(datetime)
        """)
        
        conn.commit()
        conn.close()
        logger.info(f"数据库初始化完成 | path={self.db_path}")
    
    def get_all_stocks(self) -> List[dict]:
        """获取所有 A 股股票列表"""
        logger.info("获取 A 股股票列表...")
        
        stocks = rq.all_instruments(type='CS', market='cn')
        
        stock_list = []
        for _, row in stocks.iterrows():
            stock_list.append({
                'order_book_id': row['order_book_id'],
                'symbol': row['order_book_id'].split('.')[0],
                'exchange': 'SSE' if '.XSHG' in row['order_book_id'] else 'SZE',
                'symbol_name': row['symbol_name'],
                'listed_date': row['listed_date']
            })
        
        logger.info(f"获取到 {len(stock_list)} 只 A 股股票")
        return stock_list
    
    def download_stock_data(
        self,
        symbol: str,
        order_book_id: str,
        exchange: str,
        listed_date: str
    ) -> Optional[int]:
        """
        下载单只股票数据
        
        Args:
            symbol: 股票代码
            order_book_id: 交易所代码
            exchange: 交易所
            listed_date: 上市日期
        
        Returns:
            下载的数据条数，失败返回 None
        """
        # 调整开始日期为上市日期
        actual_start = max(self.start_date, listed_date)
        
        for attempt in range(self.retry_count):
            try:
                # 获取数据
                df = rq.get_price(
                    order_book_ids=order_book_id,
                    start_date=actual_start,
                    end_date=self.end_date,
                    frequency='1d',
                    adjust_type='pre'
                )
                
                if df.empty:
                    logger.warning(f"{symbol} 无数据")
                    return 0
                
                # 保存到数据库
                self._save_to_db(df, symbol, exchange)
                
                # 记录下载日志
                self._log_download(symbol, actual_start, self.end_date, len(df), 'success')
                
                logger.debug(f"{symbol} 下载成功 | {len(df)} 条")
                return len(df)
                
            except Exception as e:
                error_msg = str(e)
                logger.warning(f"{symbol} 下载失败 (尝试 {attempt+1}/{self.retry_count}): {error_msg}")
                
                if attempt < self.retry_count - 1:
                    time.sleep(self.retry_delay * (attempt + 1))
                else:
                    self._log_download(symbol, actual_start, self.end_date, 0, 'failed', error_msg)
                    return None
        
        return None
    
    def _save_to_db(self, df: pd.DataFrame, symbol: str, exchange: str):
        """保存数据到数据库"""
        conn = sqlite3.connect(self.db_path)
        
        try:
            # 准备数据
            data = []
            for idx, row in df.iterrows():
                data.append((
                    symbol,
                    exchange,
                    idx.strftime('%Y-%m-%d'),
                    '1d',
                    float(row['open']),
                    float(row['high']),
                    float(row['low']),
                    float(row['close']),
                    float(row['volume']),
                    float(row['turnover']) if 'turnover' in row else None,
                    float(row['open_interest']) if 'open_interest' in row else None
                ))
            
            # 批量插入
            cursor = conn.cursor()
            cursor.executemany("""
                INSERT OR REPLACE INTO bar_data 
                (symbol, exchange, datetime, interval, 
                 open_price, high_price, low_price, close_price, 
                 volume, turnover, open_interest)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, data)
            
            conn.commit()
            
        finally:
            conn.close()
    
    def _log_download(self, symbol: str, start_date: str, end_date: str, 
                     bar_count: int, status: str, error_message: str = None):
        """记录下载日志"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT OR REPLACE INTO download_log
                (symbol, start_date, end_date, bar_count, status, error_message)
                VALUES (?, ?, ?, ?, ?, ?)
            """, [symbol, start_date, end_date, bar_count, status, error_message])
            
            conn.commit()
            
        finally:
            conn.close()
    
    def download_all(self):
        """下载所有股票数据"""
        logger.info("=" * 70)
        logger.info("开始下载 A 股历史数据")
        logger.info(f"时间范围：{self.start_date} 至 {self.end_date}")
        logger.info("=" * 70)
        
        # 获取股票列表
        stocks = self.get_all_stocks()
        total_stocks = len(stocks)
        
        # 统计
        success_count = 0
        failed_stocks = []
        total_bars = 0
        
        # 批量下载
        for i, stock in enumerate(stocks, 1):
            # 显示进度
            progress = (i / total_stocks) * 100
            eta_seconds = (total_stocks - i) * self.request_delay
            eta_minutes = eta_seconds / 60
            
            print(f"\r[{i:5d}/{total_stocks}] {progress:5.1f}% | "
                  f"成功：{success_count:4d} | "
                  f"失败：{len(failed_stocks):3d} | "
                  f"数据量：{total_bars:7d} 条 | "
                  f"预计：{eta_minutes:.1f}分钟", end='', flush=True)
            
            # 下载数据
            result = self.download_stock_data(
                symbol=stock['symbol'],
                order_book_id=stock['order_book_id'],
                exchange=stock['exchange'],
                listed_date=stock['listed_date']
            )
            
            if result is not None:
                success_count += 1
                total_bars += result
            else:
                failed_stocks.append(stock['symbol'])
            
            # 延迟，避免触发限流
            if i < total_stocks:
                time.sleep(self.request_delay)
        
        # 完成报告
        print("\n")
        logger.info("=" * 70)
        logger.info("下载完成！")
        logger.info(f"总股票数：{total_stocks}")
        logger.info(f"成功：{success_count} ({success_count/total_stocks*100:.1f}%)")
        logger.info(f"失败：{len(failed_stocks)} ({len(failed_stocks)/total_stocks*100:.1f}%)")
        logger.info(f"总数据量：{total_bars:,} 条")
        logger.info(f"数据库：{self.db_path}")
        logger.info("=" * 70)
        
        if failed_stocks:
            logger.warning(f"失败的股票：{', '.join(failed_stocks[:20])}")
            if len(failed_stocks) > 20:
                logger.warning(f"... 还有 {len(failed_stocks) - 20} 只")
        
        return {
            'total': total_stocks,
            'success': success_count,
            'failed': len(failed_stocks),
            'total_bars': total_bars
        }
    
    def get_download_stats(self) -> dict:
        """获取下载统计"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # 总数据量
            cursor.execute("SELECT COUNT(*) FROM bar_data")
            total_bars = cursor.fetchone()[0]
            
            # 股票数量
            cursor.execute("SELECT COUNT(DISTINCT symbol) FROM bar_data")
            stock_count = cursor.fetchone()[0]
            
            # 下载日志统计
            cursor.execute("""
                SELECT status, COUNT(*) 
                FROM download_log 
                GROUP BY status
            """)
            status_stats = dict(cursor.fetchall())
            
            return {
                'total_bars': total_bars,
                'stock_count': stock_count,
                'success': status_stats.get('success', 0),
                'failed': status_stats.get('failed', 0)
            }
            
        finally:
            conn.close()


def main():
    """主函数"""
    logger.info("RQSDK A 股数据批量下载工具")
    logger.info("=" * 70)
    
    # 创建下载器
    downloader = StockDataDownloader(db_path="data/stock_data.db")
    
    # 开始下载
    result = downloader.download_all()
    
    # 显示统计
    stats = downloader.get_download_stats()
    logger.info("\n数据库统计:")
    logger.info(f"  股票数量：{stats['stock_count']}")
    logger.info(f"  数据条数：{stats['total_bars']:,}")
    logger.info(f"  成功：{stats['success']}")
    logger.info(f"  失败：{stats['failed']}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.warning("\n用户中断下载")
        sys.exit(1)
    except Exception as e:
        logger.error(f"下载失败：{e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

#!/usr/bin/env python3
"""
RQSDK 批量下载 A 股历史数据 - 增强版

功能:
- ✅ 进度条显示（百分比 + ETA）
- ✅ 断点续传（跳过已下载的股票）
- ✅ 失败重试（最多 3 次）
- ✅ 限流保护（请求间隔）
- ✅ 数据库存储（SQLite）
- ✅ 下载日志（详细记录）

限制说明（基于官方文档）:
- QPS 限制：建议控制在 10 次/秒以内
- 单次查询：最多 100 只股票
- 数据范围：1990 年至今
- 试用版：可能有数据范围限制
"""
import rqdatac as rq
import sqlite3
import pandas as pd
import time
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional, Tuple
import logging
from tqdm import tqdm

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/download.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class StockDataDownloader:
    """股票数据下载器 - 增强版"""
    
    # 下载配置
    CONFIG = {
        'batch_size': 50,          # 每批下载数量
        'retry_count': 3,          # 失败重试次数
        'retry_delay': 2,          # 重试间隔（秒）
        'request_delay': 0.3,      # 请求间隔（秒），避免触发限流
        'start_years': 10,         # 下载年数
    }
    
    def __init__(self, db_path: str = "data/stock_data.db"):
        """
        初始化下载器
        
        Args:
            db_path: 数据库路径
        """
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        Path('logs').mkdir(parents=True, exist_ok=True)
        
        # 下载配置
        self.start_date = (datetime.now() - timedelta(days=365*self.CONFIG['start_years'])).strftime('%Y-%m-%d')
        self.end_date = datetime.now().strftime('%Y-%m-%d')
        self.batch_size = self.CONFIG['batch_size']
        self.retry_count = self.CONFIG['retry_count']
        self.retry_delay = self.CONFIG['retry_delay']
        self.request_delay = self.CONFIG['request_delay']
        
        # 初始化数据库
        self._init_db()
        
        # 初始化 RQSDK
        try:
            rq.init()
            logger.info("✓ RQSDK 初始化完成")
        except Exception as e:
            logger.error(f"✗ RQSDK 初始化失败：{e}")
            raise
    
    def _init_db(self):
        """初始化数据库表结构"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # K 线数据表
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
        
        # 下载记录表
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
                retry_count INTEGER DEFAULT 0,
                UNIQUE(symbol, start_date, end_date)
            )
        """)
        
        # 索引
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_bar_symbol ON bar_data(symbol, exchange)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_bar_datetime ON bar_data(datetime)")
        
        conn.commit()
        conn.close()
        logger.info(f"✓ 数据库初始化完成 | {self.db_path}")
    
    def get_all_stocks(self) -> List[dict]:
        """获取所有 A 股股票列表"""
        logger.info("正在获取 A 股股票列表...")
        
        stocks = rq.all_instruments(type='CS', market='cn')
        
        stock_list = []
        for _, row in stocks.iterrows():
            stock_list.append({
                'order_book_id': row['order_book_id'],
                'symbol': row['order_book_id'].split('.')[0],
                'exchange': 'SSE' if '.XSHG' in row['order_book_id'] else 'SZE',
                'symbol_name': row['symbol_name'],
                'listed_date': str(row['listed_date'])
            })
        
        logger.info(f"✓ 获取到 {len(stock_list)} 只 A 股股票")
        return stock_list
    
    def is_already_downloaded(self, symbol: str) -> bool:
        """检查股票是否已下载"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT status FROM download_log
                WHERE symbol = ? AND start_date = ? AND end_date = ?
                AND status = 'success'
            """, [symbol, self.start_date, self.end_date])
            
            row = cursor.fetchone()
            return row is not None
            
        finally:
            conn.close()
    
    def download_stock_data(
        self,
        symbol: str,
        order_book_id: str,
        exchange: str,
        listed_date: str,
        retry: int = 0
    ) -> Tuple[bool, int]:
        """
        下载单只股票数据
        
        Args:
            symbol: 股票代码
            order_book_id: 交易所代码
            exchange: 交易所
            listed_date: 上市日期
            retry: 当前重试次数
        
        Returns:
            (是否成功，数据条数)
        """
        # 调整开始日期为上市日期
        actual_start = max(self.start_date, listed_date)
        
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
                logger.debug(f"{symbol} 无数据")
                self._log_download(symbol, actual_start, self.end_date, 0, 'no_data')
                return True, 0
            
            # 保存到数据库
            self._save_to_db(df, symbol, exchange)
            
            # 记录下载日志
            self._log_download(symbol, actual_start, self.end_date, len(df), 'success')
            
            return True, len(df)
            
        except Exception as e:
            error_msg = str(e)
            
            # 重试逻辑
            if retry < self.retry_count - 1:
                delay = self.retry_delay * (retry + 1)
                logger.warning(f"{symbol} 下载失败，{delay}秒后重试 ({retry+1}/{self.retry_count})")
                time.sleep(delay)
                return self.download_stock_data(symbol, order_book_id, exchange, listed_date, retry + 1)
            else:
                logger.error(f"{symbol} 下载失败：{error_msg}")
                self._log_download(symbol, actual_start, self.end_date, 0, 'failed', error_msg, retry)
                return False, 0
    
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
            
            # 批量插入（提高性能）
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
                     bar_count: int, status: str, error_message: str = None,
                     retry_count: int = 0):
        """记录下载日志"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT OR REPLACE INTO download_log
                (symbol, start_date, end_date, bar_count, status, error_message, retry_count)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, [symbol, start_date, end_date, bar_count, status, error_message, retry_count])
            
            conn.commit()
            
        finally:
            conn.close()
    
    def download_all(self, skip_downloaded: bool = True):
        """
        下载所有股票数据
        
        Args:
            skip_downloaded: 是否跳过已下载的股票
        """
        logger.info("=" * 80)
        logger.info("RQSDK A 股数据批量下载工具 - 增强版")
        logger.info("=" * 80)
        logger.info(f"时间范围：{self.start_date} 至 {self.end_date}")
        logger.info(f"配置：batch_size={self.batch_size}, request_delay={self.request_delay}s")
        logger.info(f"跳过已下载：{skip_downloaded}")
        logger.info("=" * 80)
        
        # 获取股票列表
        stocks = self.get_all_stocks()
        
        # 过滤已下载的股票
        if skip_downloaded:
            logger.info("检查已下载的股票...")
            stocks_to_download = [
                s for s in stocks 
                if not self.is_already_downloaded(s['symbol'])
            ]
            skipped = len(stocks) - len(stocks_to_download)
            logger.info(f"✓ 共 {len(stocks)} 只股票，已下载 {skipped} 只，待下载 {len(stocks_to_download)} 只")
        else:
            stocks_to_download = stocks
        
        if not stocks_to_download:
            logger.info("✓ 所有股票已下载完成！")
            return
        
        # 开始下载
        logger.info("开始下载...")
        logger.info("-" * 80)
        
        # 统计
        success_count = 0
        failed_stocks = []
        total_bars = 0
        
        # 使用 tqdm 显示进度
        with tqdm(total=len(stocks_to_download), desc="下载进度", unit="stock") as pbar:
            for i, stock in enumerate(stocks_to_download, 1):
                # 下载数据
                success, bar_count = self.download_stock_data(
                    symbol=stock['symbol'],
                    order_book_id=stock['order_book_id'],
                    exchange=stock['exchange'],
                    listed_date=stock['listed_date']
                )
                
                if success:
                    success_count += 1
                    total_bars += bar_count
                    pbar.set_postfix({
                        '成功': f'{success_count}',
                        '失败': f'{len(failed_stocks)}',
                        '数据量': f'{total_bars:,}'
                    })
                else:
                    failed_stocks.append(stock['symbol'])
                
                pbar.update(1)
                
                # 延迟，避免触发限流
                if i < len(stocks_to_download):
                    time.sleep(self.request_delay)
        
        # 完成报告
        logger.info("")
        logger.info("=" * 80)
        logger.info("✅ 下载完成！")
        logger.info("=" * 80)
        logger.info(f"总股票数：{len(stocks)}")
        logger.info(f"本次下载：{len(stocks_to_download)}")
        logger.info(f"成功：{success_count} ({success_count/len(stocks_to_download)*100:.1f}%)")
        logger.info(f"失败：{len(failed_stocks)} ({len(failed_stocks)/len(stocks_to_download)*100:.1f}%)")
        logger.info(f"总数据量：{total_bars:,} 条")
        logger.info(f"数据库：{self.db_path}")
        logger.info(f"日志文件：logs/download.log")
        logger.info("=" * 80)
        
        if failed_stocks:
            logger.warning(f"失败的股票 ({len(failed_stocks)}):")
            for symbol in failed_stocks[:20]:
                logger.warning(f"  - {symbol}")
            if len(failed_stocks) > 20:
                logger.warning(f"  ... 还有 {len(failed_stocks) - 20} 只")
        
        return {
            'total': len(stocks),
            'downloaded': len(stocks_to_download),
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
                WHERE start_date = ? AND end_date = ?
                GROUP BY status
            """, [self.start_date, self.end_date])
            status_stats = dict(cursor.fetchall())
            
            return {
                'total_bars': total_bars,
                'stock_count': stock_count,
                'success': status_stats.get('success', 0),
                'failed': status_stats.get('failed', 0),
                'no_data': status_stats.get('no_data', 0)
            }
            
        finally:
            conn.close()


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='RQSDK A 股数据批量下载工具')
    parser.add_argument('--skip-downloaded', action='store_true', default=True,
                       help='跳过已下载的股票（默认开启）')
    parser.add_argument('--no-skip', action='store_true',
                       help='不跳过已下载的股票')
    parser.add_argument('--db', type=str, default='data/stock_data.db',
                       help='数据库路径')
    
    args = parser.parse_args()
    
    skip_downloaded = not args.no_skip
    
    logger.info("RQSDK A 股数据批量下载工具")
    
    try:
        # 创建下载器
        downloader = StockDataDownloader(db_path=args.db)
        
        # 开始下载
        result = downloader.download_all(skip_downloaded=skip_downloaded)
        
        # 显示统计
        stats = downloader.get_download_stats()
        logger.info("\n📊 数据库统计:")
        logger.info(f"  📈 股票数量：{stats['stock_count']}")
        logger.info(f"  📊 数据条数：{stats['total_bars']:,}")
        logger.info(f"  ✅ 成功：{stats['success']}")
        logger.info(f"  ❌ 失败：{stats['failed']}")
        logger.info(f"  ⚠️  无数据：{stats['no_data']}")
        
    except KeyboardInterrupt:
        logger.warning("\n⚠️  用户中断下载")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ 下载失败：{e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
AKShare 批量下载 A 股小时 K 线数据

功能:
- 下载所有 A 股的小时 K 线数据（60 分钟）
- 支持指定日期范围
- 断点续传（跳过已下载的日期）
- 失败重试机制
- 限流保护（请求间隔）
- SQLite 数据库存储
- 详细下载日志

数据源：AKShare stock_zh_a_hist_min_em（60 分钟 K 线）
"""
import akshare as ak
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
log_dir = Path('logs')
log_dir.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_dir / 'download_hourly.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class HourlyKlineDownloader:
    """小时 K 线数据下载器"""
    
    # 下载配置
    CONFIG = {
        'batch_size': 30,          # 每批下载数量
        'retry_count': 3,          # 失败重试次数
        'retry_delay': 2,          # 重试间隔（秒）
        'request_delay': 1.0,      # 请求间隔（秒），AKShare 需要更保守
        'start_years': 2,          # 默认下载年数（小时数据量大）
    }
    
    def __init__(self, db_path: str = "data/stock_data.db"):
        """
        初始化下载器
        
        Args:
            db_path: 数据库路径
        """
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        
        # 下载配置
        self.start_date = (datetime.now() - timedelta(days=365*self.CONFIG['start_years'])).strftime('%Y-%m-%d')
        self.end_date = datetime.now().strftime('%Y-%m-%d')
        self.batch_size = self.CONFIG['batch_size']
        self.retry_count = self.CONFIG['retry_count']
        self.retry_delay = self.CONFIG['retry_delay']
        self.request_delay = self.CONFIG['request_delay']
        
        # 初始化数据库
        self._init_db()
        
        logger.info("✓ AKShare 小时 K 线下载器初始化完成")
    
    def _init_db(self):
        """初始化数据库表结构"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 小时 K 线数据表（单独存储，避免与日线混淆）
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS bar_data_hourly (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                exchange TEXT NOT NULL,
                datetime TIMESTAMP NOT NULL,
                interval TEXT NOT NULL DEFAULT '60m',
                open_price REAL NOT NULL,
                high_price REAL NOT NULL,
                low_price REAL NOT NULL,
                close_price REAL NOT NULL,
                volume REAL NOT NULL,
                turnover REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(symbol, exchange, datetime, interval)
            )
        """)
        
        # 下载记录表（按日期范围记录）
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS download_log_hourly (
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
        
        # 索引优化查询性能
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_hourly_symbol ON bar_data_hourly(symbol, exchange)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_hourly_datetime ON bar_data_hourly(datetime)")
        
        conn.commit()
        conn.close()
        logger.info(f"✓ 数据库初始化完成 | {self.db_path}")
    
    def get_all_stocks(self) -> List[dict]:
        """获取所有 A 股股票列表"""
        logger.info("正在获取 A 股股票列表...")
        
        try:
            # 使用 AKShare 获取 A 股股票列表
            df = ak.stock_info_a_code_name()
            
            stock_list = []
            for _, row in df.iterrows():
                symbol = row['code']
                stock_list.append({
                    'symbol': symbol,
                    'name': row['name'],
                    'exchange': 'SSE' if symbol.startswith('6') else 'SZE',
                })
            
            logger.info(f"✓ 获取到 {len(stock_list)} 只 A 股股票")
            return stock_list
            
        except Exception as e:
            logger.error(f"获取股票列表失败：{e}")
            return []
    
    def is_date_range_downloaded(self, symbol: str, start_date: str, end_date: str) -> bool:
        """检查指定日期范围是否已下载"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT status FROM download_log_hourly
                WHERE symbol = ? AND start_date = ? AND end_date = ?
                AND status = 'success'
            """, [symbol, start_date, end_date])
            
            row = cursor.fetchone()
            return row is not None
            
        finally:
            conn.close()
    
    def download_stock_hourly_kline(
        self,
        symbol: str,
        exchange: str,
        start_date: str,
        end_date: str,
        retry: int = 0
    ) -> Tuple[bool, int]:
        """
        下载单只股票的小时 K 线数据
        
        Args:
            symbol: 股票代码
            exchange: 交易所
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)
            retry: 当前重试次数
        
        Returns:
            (是否成功，数据条数)
        """
        try:
            # AKShare 获取 60 分钟 K 线
            # 注意：stock_zh_a_hist_min_em 的 period 参数：'60' 表示 60 分钟
            df = ak.stock_zh_a_hist_min_em(
                symbol=symbol,
                period='60',
                start_date=start_date.replace('-', ''),
                end_date=end_date.replace('-', ''),
                adjust='qfq'  # 前复权
            )
            
            if df.empty:
                logger.debug(f"{symbol} 无小时 K 线数据")
                self._log_download(symbol, start_date, end_date, 0, 'no_data')
                return True, 0
            
            # 数据转换和保存
            self._save_to_db(df, symbol, exchange)
            
            # 记录下载日志
            self._log_download(symbol, start_date, end_date, len(df), 'success')
            
            return True, len(df)
            
        except Exception as e:
            error_msg = str(e)
            
            # 重试逻辑
            if retry < self.retry_count - 1:
                delay = self.retry_delay * (retry + 1)
                logger.warning(f"{symbol} 下载失败，{delay}秒后重试 ({retry+1}/{self.retry_count})")
                time.sleep(delay)
                return self.download_stock_hourly_kline(symbol, exchange, start_date, end_date, retry + 1)
            else:
                logger.error(f"{symbol} 下载失败：{error_msg}")
                self._log_download(symbol, start_date, end_date, 0, 'failed', error_msg, retry)
                return False, 0
    
    def _save_to_db(self, df: pd.DataFrame, symbol: str, exchange: str):
        """保存数据到数据库"""
        conn = sqlite3.connect(self.db_path)
        
        try:
            # 准备数据
            data = []
            for _, row in df.iterrows():
                # AKShare 返回的列名：时间、开盘、最高、最低、收盘、成交量、成交额
                datetime_str = str(row.get('时间', row.get('datetime', '')))
                
                # 解析时间（格式可能是 "2024-03-20 10:00:00" 或 "2024-03-20 10:00"）
                try:
                    dt = datetime.strptime(datetime_str, '%Y-%m-%d %H:%M:%S')
                except ValueError:
                    try:
                        dt = datetime.strptime(datetime_str, '%Y-%m-%d %H:%M')
                    except ValueError:
                        continue  # 跳过无法解析的时间
                
                data.append((
                    symbol,
                    exchange,
                    dt.strftime('%Y-%m-%d %H:%M:%S'),
                    '60m',
                    float(row.get('开盘', 0)),
                    float(row.get('最高', 0)),
                    float(row.get('最低', 0)),
                    float(row.get('收盘', 0)),
                    float(row.get('成交量', 0)),
                    float(row.get('成交额', 0)) if '成交额' in row else None,
                ))
            
            # 批量插入
            cursor = conn.cursor()
            cursor.executemany("""
                INSERT OR REPLACE INTO bar_data_hourly 
                (symbol, exchange, datetime, interval, 
                 open_price, high_price, low_price, close_price, 
                 volume, turnover)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                INSERT OR REPLACE INTO download_log_hourly
                (symbol, start_date, end_date, bar_count, status, error_message, retry_count)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, [symbol, start_date, end_date, bar_count, status, error_message, retry_count])
            
            conn.commit()
            
        finally:
            conn.close()
    
    def download_all(self, skip_downloaded: bool = True):
        """
        下载所有股票的小时 K 线数据
        
        Args:
            skip_downloaded: 是否跳过已下载的股票
        """
        logger.info("=" * 80)
        logger.info("AKShare A 股小时 K 线批量下载工具")
        logger.info("=" * 80)
        logger.info(f"时间范围：{self.start_date} 至 {self.end_date}")
        logger.info(f"配置：batch_size={self.batch_size}, request_delay={self.request_delay}s")
        logger.info(f"跳过已下载：{skip_downloaded}")
        logger.info("=" * 80)
        
        # 获取股票列表
        stocks = self.get_all_stocks()
        
        if not stocks:
            logger.error("未获取到股票列表，退出")
            return
        
        # 开始下载
        logger.info("开始下载...")
        logger.info("-" * 80)
        
        # 统计
        success_count = 0
        failed_stocks = []
        total_bars = 0
        
        # 使用 tqdm 显示进度
        with tqdm(total=len(stocks), desc="下载进度", unit="stock") as pbar:
            for i, stock in enumerate(stocks, 1):
                # 检查是否已下载
                if skip_downloaded and self.is_date_range_downloaded(stock['symbol'], self.start_date, self.end_date):
                    logger.debug(f"跳过已下载：{stock['symbol']}")
                    pbar.update(1)
                    continue
                
                # 下载数据
                success, bar_count = self.download_stock_hourly_kline(
                    symbol=stock['symbol'],
                    exchange=stock['exchange'],
                    start_date=self.start_date,
                    end_date=self.end_date
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
                if i < len(stocks):
                    time.sleep(self.request_delay)
        
        # 完成报告
        logger.info("")
        logger.info("=" * 80)
        logger.info("✅ 下载完成！")
        logger.info("=" * 80)
        logger.info(f"总股票数：{len(stocks)}")
        logger.info(f"成功：{success_count} ({success_count/len(stocks)*100:.1f}%)")
        logger.info(f"失败：{len(failed_stocks)} ({len(failed_stocks)/len(stocks)*100:.1f}%)")
        logger.info(f"总数据量：{total_bars:,} 条")
        logger.info(f"数据库：{self.db_path}")
        logger.info(f"日志文件：logs/download_hourly.log")
        logger.info("=" * 80)
        
        if failed_stocks:
            logger.warning(f"失败的股票 ({len(failed_stocks)}):")
            for symbol in failed_stocks[:20]:
                logger.warning(f"  - {symbol}")
            if len(failed_stocks) > 20:
                logger.warning(f"  ... 还有 {len(failed_stocks) - 20} 只")
        
        return {
            'total': len(stocks),
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
            cursor.execute("SELECT COUNT(*) FROM bar_data_hourly")
            total_bars = cursor.fetchone()[0]
            
            # 股票数量
            cursor.execute("SELECT COUNT(DISTINCT symbol) FROM bar_data_hourly")
            stock_count = cursor.fetchone()[0]
            
            # 下载日志统计
            cursor.execute("""
                SELECT status, COUNT(*) 
                FROM download_log_hourly 
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
    
    parser = argparse.ArgumentParser(description='AKShare A 股小时 K 线批量下载工具')
    parser.add_argument('--skip-downloaded', action='store_true', default=True,
                       help='跳过已下载的股票（默认开启）')
    parser.add_argument('--no-skip', action='store_true',
                       help='不跳过已下载的股票')
    parser.add_argument('--db', type=str, default='data/stock_data.db',
                       help='数据库路径')
    parser.add_argument('--years', type=int, default=2,
                       help='下载年数（默认 2 年，小时数据量大）')
    parser.add_argument('--delay', type=float, default=1.0,
                       help='请求间隔秒数（默认 1.0s，避免限流）')
    
    args = parser.parse_args()
    
    skip_downloaded = not args.no_skip
    
    logger.info("AKShare A 股小时 K 线批量下载工具")
    
    try:
        # 创建下载器
        downloader = HourlyKlineDownloader(db_path=args.db)
        downloader.start_date = (datetime.now() - timedelta(days=365*args.years)).strftime('%Y-%m-%d')
        downloader.request_delay = args.delay
        
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

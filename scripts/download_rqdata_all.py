#!/usr/bin/env python3
"""
RQData (米筐) 全面数据下载器

下载内容:
1. 股票日线 (全部 A 股，2020 至今)
2. 股票分钟线 (全部 A 股，最近 90 天)
3. 期货日线 (全部品种，2020 至今)
4. 期货分钟线 (主力合约，最近 30 天)
5. 指数数据 (主要指数)
6. ETF 数据
7. 基本面数据

使用前请配置米筐账号:
方法 1: 修改脚本中的 JQ_USER 和 JQ_PASS
方法 2: 设置环境变量 RQDATAC_USER 和 RQDATAC_PASSWORD
"""
import rqdatac as rq
import pandas as pd
import sqlite3
import logging
from datetime import datetime, timedelta
from pathlib import Path
from tqdm import tqdm
import time
import os
from typing import List, Dict

# ==================== 配置区 ====================
# 请在此处配置你的米筐账号
JQ_USER = ""  # 米筐账号 (手机号/邮箱)
JQ_PASS = ""  # 米筐密码

# 或者使用环境变量
if os.environ.get('RQDATAC_USER'):
    JQ_USER = os.environ['RQDATAC_USER']
if os.environ.get('RQDATAC_PASSWORD'):
    JQ_PASS = os.environ['RQDATAC_PASSWORD']

# 数据库路径
STOCK_DB = Path("data/rqdata_stocks.db")
FUTURE_DB = Path("data/rqdata_futures.db")
LOG_DIR = Path("logs")

# 创建目录
LOG_DIR.mkdir(parents=True, exist_ok=True)
STOCK_DB.parent.mkdir(parents=True, exist_ok=True)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    handlers=[
        logging.FileHandler(LOG_DIR / f'rqdata_download_{datetime.now().strftime("%Y%m%d_%H%M")}.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class RQDataDownloader:
    """RQData 数据下载器"""
    
    def __init__(self):
        self._init_rqdata()
        self._init_db()
    
    def _init_rqdata(self):
        """初始化 RQData"""
        try:
            # 尝试使用 License Key 初始化
            if LICENSE_KEY:
                try:
                    # 尝试多种初始化方式
                    # 方式 1: 使用配置文件（已配置在 ~/.rqdatac/config）
                    rq.init()
                    logger.info("✅ RQData 初始化成功 (配置文件)")
                except:
                    # 方式 2: 尝试用户名密码
                    if JQ_USER and JQ_PASS:
                        rq.init(user=JQ_USER, password=JQ_PASS)
                        logger.info("✅ RQData 初始化成功 (用户名密码)")
                    else:
                        raise ValueError("需要配置用户名密码")
            else:
                if not JQ_USER or not JQ_PASS:
                    logger.error("❌ 请配置米筐账号！")
                    logger.error("   方法 1: 修改脚本设置 LICENSE_KEY")
                    logger.error("   方法 2: 设置 JQ_USER 和 JQ_PASS")
                    raise ValueError("未配置米筐账号")
                
                rq.init(user=JQ_USER, password=JQ_PASS)
                logger.info("✅ RQData 初始化成功")
            
            # 测试连接
            stocks = rq.all_instruments(type='CS', market='cn')
            logger.info(f"✅ 连接测试成功 | A 股数量：{len(stocks)}")
            
        except Exception as e:
            logger.error(f"❌ RQData 初始化失败：{e}")
            logger.error("")
            logger.error("解决方案:")
            logger.error("1. 检查 License Key 是否正确")
            logger.error("2. 联系米筐技术支持：support@ricequant.com")
            logger.error("3. 或使用 AKShare 作为备选数据源")
            raise
    
    def _init_db(self):
        """初始化数据库"""
        # 股票数据库
        conn = sqlite3.connect(STOCK_DB)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS stock_daily (
                id INTEGER PRIMARY KEY,
                symbol TEXT NOT NULL,
                date DATE NOT NULL,
                open REAL,
                high REAL,
                low REAL,
                close REAL,
                volume REAL,
                turnover REAL,
                UNIQUE(symbol, date)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS stock_minute (
                id INTEGER PRIMARY KEY,
                symbol TEXT NOT NULL,
                datetime TIMESTAMP NOT NULL,
                open REAL,
                high REAL,
                low REAL,
                close REAL,
                volume REAL,
                turnover REAL,
                UNIQUE(symbol, datetime)
            )
        ''')
        
        conn.commit()
        conn.close()
        
        # 期货数据库
        conn = sqlite3.connect(FUTURE_DB)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS future_daily (
                id INTEGER PRIMARY KEY,
                symbol TEXT NOT NULL,
                date DATE NOT NULL,
                open REAL,
                high REAL,
                low REAL,
                close REAL,
                volume REAL,
                open_interest REAL,
                UNIQUE(symbol, date)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS future_minute (
                id INTEGER PRIMARY KEY,
                symbol TEXT NOT NULL,
                datetime TIMESTAMP NOT NULL,
                open REAL,
                high REAL,
                low REAL,
                close REAL,
                volume REAL,
                open_interest REAL,
                UNIQUE(symbol, datetime)
            )
        ''')
        
        conn.commit()
        conn.close()
        
        logger.info(f"✅ 数据库初始化完成 | {STOCK_DB}, {FUTURE_DB}")
    
    def download_stock_daily(self, start_date: str = "2020-01-01"):
        """下载股票日线数据"""
        logger.info("="*70)
        logger.info("Phase 1: 下载股票日线数据")
        logger.info(f"时间范围：{start_date} 至今")
        logger.info("="*70)
        
        # 获取股票列表
        logger.info("获取 A 股列表...")
        stocks = rq.all_instruments(type='CS', market='cn')
        stock_list = stocks['order_book_id'].tolist()
        logger.info(f"共 {len(stock_list)} 只股票")
        
        # 分批下载
        batch_size = 100
        success_count = 0
        
        for i in range(0, len(stock_list), batch_size):
            batch = stock_list[i:i+batch_size]
            batch_num = i // batch_size + 1
            total_batches = (len(stock_list) - 1) // batch_size + 1
            
            logger.info(f"\n批次 {batch_num}/{total_batches}")
            
            try:
                # 批量获取日线数据
                df = rq.get_price(
                    order_book_ids=batch,
                    start_date=start_date,
                    end_date=datetime.now().strftime('%Y-%m-%d'),
                    frequency='1d',
                    adjust_type='pre'
                )
                
                if df is not None and len(df) > 0:
                    # 保存到数据库
                    conn = sqlite3.connect(STOCK_DB)
                    
                    df_reset = df.reset_index()
                    df_reset.columns = ['date', 'symbol', 'open', 'high', 'low', 'close', 'volume', 'turnover']
                    
                    df_reset.to_sql('stock_daily', conn, if_exists='append', index=False, method='ignore')
                    
                    conn.commit()
                    conn.close()
                    
                    success_count += len(df_reset) // len(batch)
                    logger.info(f"   ✓ 本批次成功下载 {len(df_reset)//len(batch)} 只股票，{len(df_reset)} 条数据")
                
                time.sleep(0.5)  # 避免限流
                
            except Exception as e:
                logger.error(f"   ❌ 批次失败：{e}")
        
        logger.info(f"\n✅ 股票日线下载完成 | 成功 {success_count} 只")
    
    def download_stock_minute(self, days: int = 90, frequency: str = '60m'):
        """下载股票分钟线数据"""
        logger.info("="*70)
        logger.info("Phase 2: 下载股票分钟线数据")
        logger.info(f"周期：{frequency} | 最近 {days} 天")
        logger.info("="*70)
        
        # 获取股票列表
        logger.info("获取 A 股列表...")
        stocks = rq.all_instruments(type='CS', market='cn')
        stock_list = stocks['order_book_id'].tolist()
        logger.info(f"共 {len(stock_list)} 只股票")
        
        start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        
        # 分批下载
        batch_size = 50
        success_count = 0
        
        for i in range(0, len(stock_list), batch_size):
            batch = stock_list[i:i+batch_size]
            batch_num = i // batch_size + 1
            total_batches = (len(stock_list) - 1) // batch_size + 1
            
            logger.info(f"\n批次 {batch_num}/{total_batches}")
            
            try:
                df = rq.get_price(
                    order_book_ids=batch,
                    start_date=start_date,
                    end_date=datetime.now().strftime('%Y-%m-%d'),
                    frequency=frequency,
                    adjust_type='pre'
                )
                
                if df is not None and len(df) > 0:
                    conn = sqlite3.connect(STOCK_DB)
                    
                    df_reset = df.reset_index()
                    df_reset.columns = ['datetime', 'symbol', 'open', 'high', 'low', 'close', 'volume', 'turnover']
                    
                    df_reset.to_sql('stock_minute', conn, if_exists='append', index=False, method='ignore')
                    
                    conn.commit()
                    conn.close()
                    
                    success_count += len(df_reset) // len(batch)
                    logger.info(f"   ✓ 本批次 {len(df_reset)//len(batch)} 只，{len(df_reset)} 条")
                
                time.sleep(0.5)
                
            except Exception as e:
                logger.error(f"   ❌ 批次失败：{e}")
        
        logger.info(f"\n✅ 股票分钟线下载完成 | 成功 {success_count} 只")
    
    def download_future_daily(self, start_date: str = "2020-01-01"):
        """下载期货日线数据"""
        logger.info("="*70)
        logger.info("Phase 3: 下载期货日线数据")
        logger.info(f"时间范围：{start_date} 至今")
        logger.info("="*70)
        
        # 获取期货列表
        logger.info("获取期货合约列表...")
        futures = rq.all_instruments(type='Future', market='cn')
        logger.info(f"共 {len(futures)} 个期货合约")
        
        # 按品种分组
        future_symbols = set()
        for _, row in futures.iterrows():
            symbol = row['order_book_id']
            # 提取品种代码 (如 RB2401 -> RB)
            base_symbol = ''.join([c for c in symbol if c.isalpha()])
            future_symbols.add(base_symbol)
        
        future_list = list(future_symbols)
        logger.info(f"共 {len(future_list)} 个品种")
        
        success_count = 0
        
        for symbol in tqdm(future_list, desc="下载期货"):
            try:
                # 获取主力合约连续数据
                df = rq.get_price(
                    order_book_ids=f"{symbol}0",
                    start_date=start_date,
                    end_date=datetime.now().strftime('%Y-%m-%d'),
                    frequency='1d'
                )
                
                if df is not None and len(df) > 0:
                    conn = sqlite3.connect(FUTURE_DB)
                    
                    df_reset = df.reset_index()
                    df_reset['symbol'] = symbol
                    df_reset.columns = ['date', 'open', 'high', 'low', 'close', 'volume', 'open_interest', 'symbol']
                    
                    df_reset.to_sql('future_daily', conn, if_exists='append', index=False, method='ignore')
                    
                    conn.commit()
                    conn.close()
                    
                    success_count += 1
                    logger.info(f"   ✓ {symbol}: {len(df)} 条")
                
                time.sleep(0.3)
                
            except Exception as e:
                logger.error(f"   ❌ {symbol} 失败：{e}")
        
        logger.info(f"\n✅ 期货日线下载完成 | 成功 {success_count}/{len(future_list)} 个品种")
    
    def download_future_minute(self, days: int = 30, frequency: str = '60m'):
        """下载期货分钟线数据"""
        logger.info("="*70)
        logger.info("Phase 4: 下载期货分钟线数据")
        logger.info(f"周期：{frequency} | 最近 {days} 天")
        logger.info("="*70)
        
        # 获取期货品种列表
        futures = rq.all_instruments(type='Future', market='cn')
        future_symbols = set()
        for _, row in futures.iterrows():
            symbol = row['order_book_id']
            base_symbol = ''.join([c for c in symbol if c.isalpha()])
            future_symbols.add(base_symbol)
        
        future_list = list(future_symbols)
        start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        
        success_count = 0
        
        for symbol in tqdm(future_list, desc="下载期货分钟线"):
            try:
                df = rq.get_price(
                    order_book_ids=f"{symbol}0",
                    start_date=start_date,
                    end_date=datetime.now().strftime('%Y-%m-%d'),
                    frequency=frequency
                )
                
                if df is not None and len(df) > 0:
                    conn = sqlite3.connect(FUTURE_DB)
                    
                    df_reset = df.reset_index()
                    df_reset['symbol'] = symbol
                    df_reset.columns = ['datetime', 'open', 'high', 'low', 'close', 'volume', 'open_interest', 'symbol']
                    
                    df_reset.to_sql('future_minute', conn, if_exists='append', index=False, method='ignore')
                    
                    conn.commit()
                    conn.close()
                    
                    success_count += 1
                
                time.sleep(0.3)
                
            except Exception as e:
                logger.error(f"   ❌ {symbol} 失败：{e}")
        
        logger.info(f"\n✅ 期货分钟线下载完成 | 成功 {success_count}/{len(future_list)} 个品种")
    
    def download_index_data(self, start_date: str = "2020-01-01"):
        """下载指数数据"""
        logger.info("="*70)
        logger.info("Phase 5: 下载指数数据")
        logger.info("="*70)
        
        # 主要指数
        indices = {
            '000001.XSHG': '上证指数',
            '000016.XSHG': '上证 50',
            '000300.XSHG': '沪深 300',
            '000905.XSHG': '中证 500',
            '399001.XSHE': '深证成指',
            '399006.XSHE': '创业板指',
        }
        
        conn = sqlite3.connect(STOCK_DB)
        
        for symbol, name in indices.items():
            try:
                df = rq.get_price(
                    order_book_ids=symbol,
                    start_date=start_date,
                    end_date=datetime.now().strftime('%Y-%m-%d'),
                    frequency='1d'
                )
                
                if df is not None and len(df) > 0:
                    df_reset = df.reset_index()
                    df_reset['symbol'] = symbol
                    df_reset['name'] = name
                    
                    df_reset.to_sql('index_daily', conn, if_exists='append', index=False, method='ignore')
                    logger.info(f"   ✓ {name} ({symbol}): {len(df)} 条")
                
                time.sleep(0.3)
                
            except Exception as e:
                logger.error(f"   ❌ {name} ({symbol}) 失败：{e}")
        
        conn.commit()
        conn.close()
        logger.info("✅ 指数数据下载完成")
    
    def show_summary(self):
        """显示下载汇总"""
        logger.info("\n" + "="*70)
        logger.info("📊 RQData 数据下载汇总")
        logger.info("="*70)
        
        # 股票数据
        if STOCK_DB.exists():
            conn = sqlite3.connect(STOCK_DB)
            cursor = conn.cursor()
            
            try:
                cursor.execute("SELECT COUNT(*) FROM stock_daily")
                daily = cursor.fetchone()[0]
                logger.info(f"   股票日线：{daily:,} 条")
                
                cursor.execute("SELECT COUNT(*) FROM stock_minute")
                minute = cursor.fetchone()[0]
                logger.info(f"   股票分钟线：{minute:,} 条")
            except:
                pass
            
            conn.close()
        
        # 期货数据
        if FUTURE_DB.exists():
            conn = sqlite3.connect(FUTURE_DB)
            cursor = conn.cursor()
            
            try:
                cursor.execute("SELECT COUNT(*) FROM future_daily")
                daily = cursor.fetchone()[0]
                logger.info(f"   期货日线：{daily:,} 条")
                
                cursor.execute("SELECT COUNT(*) FROM future_minute")
                minute = cursor.fetchone()[0]
                logger.info(f"   期货分钟线：{minute:,} 条")
            except:
                pass
            
            conn.close()
        
        # 文件大小
        stock_size = STOCK_DB.stat().st_size / 1024 / 1024
        future_size = FUTURE_DB.stat().st_size / 1024 / 1024
        
        logger.info(f"\n   股票数据库：{stock_size:.2f} MB")
        logger.info(f"   期货数据库：{future_size:.2f} MB")
        logger.info("="*70)


def main():
    """主函数"""
    logger.info("="*80)
    logger.info("RQData (米筐) 全面数据下载器")
    logger.info("下载内容：股票日线 + 分钟线 + 期货日线 + 分钟线 + 指数")
    logger.info("="*80)
    
    # 检查配置
    if not JQ_USER or not JQ_PASS:
        logger.error("❌ 请配置米筐账号！")
        logger.error("")
        logger.error("   方法 1: 修改脚本，设置 JQ_USER 和 JQ_PASS")
        logger.error("   方法 2: 设置环境变量:")
        logger.error("     export RQDATAC_USER=your_username")
        logger.error("     export RQDATAC_PASSWORD=your_password")
        logger.error("")
        return
    
    # 初始化下载器
    downloader = RQDataDownloader()
    
    # Phase 1: 股票日线
    downloader.download_stock_daily(start_date="2020-01-01")
    
    # Phase 2: 股票分钟线
    downloader.download_stock_minute(days=90, frequency='60m')
    
    # Phase 3: 期货日线
    downloader.download_future_daily(start_date="2020-01-01")
    
    # Phase 4: 期货分钟线
    downloader.download_future_minute(days=30, frequency='60m')
    
    # Phase 5: 指数数据
    downloader.download_index_data(start_date="2020-01-01")
    
    # 显示汇总
    downloader.show_summary()
    
    logger.info("\n✅ 所有下载任务完成！")


if __name__ == "__main__":
    main()

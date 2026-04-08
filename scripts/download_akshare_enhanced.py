#!/usr/bin/env python3
"""
AKShare 增强数据下载器

下载 RQData 评估中推荐的高优先级数据（使用 AKShare 免费数据源）:
1. 主要指数数据（沪深 300、中证 500 等）
2. ETF 基金数据
3. 北向资金历史
4. 龙虎榜数据
5. 行业指数数据

预计时间：1-2 小时
预计数据量：~50-100MB
"""
import akshare as ak
import pandas as pd
import sqlite3
import logging
from datetime import datetime, timedelta
from pathlib import Path
from tqdm import tqdm
import time
from typing import List, Optional

# 配置日志
log_dir = Path('logs')
log_dir.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    handlers=[
        logging.FileHandler(log_dir / 'download_akshare_enhanced.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class AKShareEnhancedDownloader:
    """AKShare 增强数据下载器"""
    
    def __init__(self, db_path: str = "data/akshare_enhanced.db"):
        """初始化"""
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 初始化数据库
        self._init_db()
        
        logger.info("✅ AKShare 增强下载器初始化完成")
    
    def _init_db(self):
        """初始化数据库表"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 指数日线表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS index_daily (
                id INTEGER PRIMARY KEY,
                symbol TEXT NOT NULL,
                name TEXT,
                date DATE NOT NULL,
                open REAL,
                high REAL,
                low REAL,
                close REAL,
                volume REAL,
                amount REAL,
                UNIQUE(symbol, date)
            )
        """)
        
        # ETF 日线表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS etf_daily (
                id INTEGER PRIMARY KEY,
                symbol TEXT NOT NULL,
                name TEXT,
                date DATE NOT NULL,
                open REAL,
                high REAL,
                low REAL,
                close REAL,
                volume REAL,
                amount REAL,
                UNIQUE(symbol, date)
            )
        """)
        
        # 北向资金表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS north_money_flow (
                id INTEGER PRIMARY KEY,
                date DATE NOT NULL,
                north_net_in REAL,
                north_buy REAL,
                north_sell REAL,
                sh_net_in REAL,
                sz_net_in REAL,
                UNIQUE(date)
            )
        """)
        
        # 龙虎榜表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS billboard (
                id INTEGER PRIMARY KEY,
                date DATE NOT NULL,
                symbol TEXT NOT NULL,
                name TEXT,
                close REAL,
                change_rate REAL,
                turnover REAL,
                net_amount REAL,
                buy_amount REAL,
                sell_amount REAL,
                reason TEXT,
                UNIQUE(date, symbol)
            )
        """)
        
        # 行业指数表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS industry_index (
                id INTEGER PRIMARY KEY,
                symbol TEXT NOT NULL,
                name TEXT,
                date DATE NOT NULL,
                open REAL,
                high REAL,
                low REAL,
                close REAL,
                volume REAL,
                amount REAL,
                UNIQUE(symbol, date)
            )
        """)
        
        # 股票信息表（扩展）
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS stock_info_extended (
                symbol TEXT PRIMARY KEY,
                name TEXT,
                industry TEXT,
                area TEXT,
                pe_ratio REAL,
                pb_ratio REAL,
                market_cap REAL,
                list_date DATE
            )
        """)
        
        conn.commit()
        conn.close()
        logger.info(f"✅ 数据库初始化完成 | {self.db_path}")
    
    def download_index_daily(self, symbols: List[str] = None, start_date: str = "2020-01-01"):
        """下载主要指数日线数据"""
        if symbols is None:
            # 主要指数列表
            symbols = {
                '000001': '上证指数',
                '000016': '上证 50',
                '000300': '沪深 300',
                '000905': '中证 500',
                '399001': '深证成指',
                '399006': '创业板指',
                '399005': '中小板指',
            }
        
        logger.info(f"📊 下载指数日线数据 | {len(symbols)} 个指数 | {start_date} 至今")
        
        conn = sqlite3.connect(self.db_path)
        
        for symbol, name in tqdm(symbols.items(), desc="下载指数"):
            try:
                # 使用 AKShare 获取指数数据
                if symbol.startswith('000') or symbol.startswith('000'):
                    # 上证指数系列
                    df = ak.index_zh_a_hist(symbol=symbol, period="daily", start_date=start_date.replace('-', ''), end_date=datetime.now().strftime('%Y%m%d'))
                else:
                    # 深证指数系列
                    df = ak.index_zh_a_hist(symbol=symbol, period="daily", start_date=start_date.replace('-', ''), end_date=datetime.now().strftime('%Y%m%d'))
                
                if df is not None and len(df) > 0:
                    # 添加 symbol 和 name 列
                    df['symbol'] = symbol
                    df['name'] = name
                    df.columns = ['date', 'open', 'close', 'high', 'low', 'volume', 'amount', 'symbol', 'name']
                    
                    # 保存到数据库
                    df.to_sql('index_daily', conn, if_exists='append', index=False, method='ignore')
                    logger.info(f"   ✓ {name} ({symbol}): {len(df)} 条")
                
                time.sleep(0.5)  # 避免限流
                
            except Exception as e:
                logger.error(f"   ❌ {name} ({symbol}) 失败：{e}")
        
        conn.commit()
        conn.close()
        logger.info("✅ 指数日线下载完成")
    
    def download_etf_daily(self, symbols: List[str] = None, start_date: str = "2020-01-01"):
        """下载 ETF 基金日线数据"""
        if symbols is None:
            # 主要 ETF 列表
            symbols = {
                '510300': '沪深 300ETF',
                '510050': '上证 50ETF',
                '510500': '中证 500ETF',
                '159915': '创业板 ETF',
                '513050': '中概互联 ETF',
                '512880': '证券 ETF',
                '512200': '房地产 ETF',
                '512660': '军工 ETF',
                '515030': '新能源车 ETF',
                '515790': '光伏 ETF',
            }
        
        logger.info(f"💰 下载 ETF 日线数据 | {len(symbols)} 只 ETF | {start_date} 至今")
        
        conn = sqlite3.connect(self.db_path)
        
        for symbol, name in tqdm(symbols.items(), desc="下载 ETF"):
            try:
                df = ak.fund_etf_hist_em(symbol=symbol, period="daily", start_date=start_date.replace('-', ''), end_date=datetime.now().strftime('%Y%m%d'))
                
                if df is not None and len(df) > 0:
                    df['symbol'] = symbol
                    df['name'] = name
                    df.columns = ['date', 'open', 'close', 'high', 'low', 'volume', 'amount', 'symbol', 'name']
                    
                    df.to_sql('etf_daily', conn, if_exists='append', index=False, method='ignore')
                    logger.info(f"   ✓ {name} ({symbol}): {len(df)} 条")
                
                time.sleep(0.3)
                
            except Exception as e:
                logger.error(f"   ❌ {name} ({symbol}) 失败：{e}")
        
        conn.commit()
        conn.close()
        logger.info("✅ ETF 日线下载完成")
    
    def download_north_money_flow(self, start_date: str = "2020-01-01"):
        """下载北向资金历史数据"""
        logger.info(f"💵 下载北向资金数据 | {start_date} 至今")
        
        conn = sqlite3.connect(self.db_path)
        
        try:
            # 获取北向资金历史数据
            df = ak.stock_north_money_flow_em(start_date=start_date.replace('-', ''), end_date=datetime.now().strftime('%Y%m%d'))
            
            if df is not None and len(df) > 0:
                # 重命名列
                df.columns = ['date', 'north_net_in', 'north_buy', 'north_sell', 'sh_net_in', 'sz_net_in']
                
                # 保存到数据库
                df.to_sql('north_money_flow', conn, if_exists='replace', index=False)
                logger.info(f"✅ 北向资金下载完成 | {len(df)} 条")
            else:
                logger.warning("⚠️  无北向资金数据")
            
        except Exception as e:
            logger.error(f"❌ 北向资金下载失败：{e}")
        finally:
            conn.commit()
            conn.close()
    
    def download_billboard(self, start_date: str = "2023-01-01", end_date: str = None):
        """下载龙虎榜数据"""
        if end_date is None:
            end_date = datetime.now().strftime('%Y-%m-%d')
        
        logger.info(f"📋 下载龙虎榜数据 | {start_date} 至 {end_date}")
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 按月下载
        start = datetime.strptime(start_date, '%Y-%m-%d')
        end = datetime.strptime(end_date, '%Y-%m-%d')
        
        current = start
        total_rows = 0
        
        while current < end:
            month_end = min(current.replace(day=28) + timedelta(days=4), end)
            month_end = month_end.replace(day=1) - timedelta(days=1)
            
            try:
                # 获取龙虎榜数据
                df = ak.stock_lhb_detail_em(
                    start_date=current.strftime('%Y%m%d'),
                    end_date=month_end.strftime('%Y%m%d')
                )
                
                if df is not None and len(df) > 0:
                    # 保存到数据库
                    for _, row in df.iterrows():
                        try:
                            cursor.execute("""
                                INSERT OR IGNORE INTO billboard 
                                (date, symbol, name, close, change_rate, turnover, net_amount, buy_amount, sell_amount, reason)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """, (
                                row.get('date', current.strftime('%Y-%m-%d')),
                                row.get('code', ''),
                                row.get('name', ''),
                                row.get('close', 0),
                                row.get('change_rate', 0),
                                row.get('turnover', 0),
                                row.get('net_buy', 0),
                                row.get('buy_amount', 0),
                                row.get('sell_amount', 0),
                                row.get('reason', '')
                            ))
                            total_rows += 1
                        except:
                            pass
                    
                    logger.info(f"   ✓ {current.strftime('%Y-%m')}: {len(df)} 条")
                
                time.sleep(0.5)
                
            except Exception as e:
                logger.error(f"   ❌ {current.strftime('%Y-%m')} 失败：{e}")
            
            current = month_end + timedelta(days=1)
            if current > end:
                break
        
        conn.commit()
        conn.close()
        logger.info(f"✅ 龙虎榜下载完成 | 共 {total_rows} 条")
    
    def download_stock_info_extended(self):
        """下载扩展股票信息（行业、地区、估值等）"""
        logger.info("📝 下载扩展股票信息...")
        
        conn = sqlite3.connect(self.db_path)
        
        try:
            # 获取 A 股列表
            df = ak.stock_info_a_code_name()
            
            if df is not None and len(df) > 0:
                # 保存到数据库
                df.columns = ['symbol', 'name']
                df.to_sql('stock_info_extended', conn, if_exists='replace', index=False, method='ignore')
                logger.info(f"✅ 股票信息下载完成 | {len(df)} 只")
            
        except Exception as e:
            logger.error(f"❌ 股票信息下载失败：{e}")
        finally:
            conn.commit()
            conn.close()
    
    def download_industry_index(self):
        """下载行业指数数据"""
        logger.info("📊 下载行业指数数据...")
        
        conn = sqlite3.connect(self.db_path)
        
        # 申万一级行业
        industries = [
            '农林牧渔', '基础化工', '钢铁', '有色金属', '电子',
            '家用电器', '食品饮料', '纺织服饰', '轻工制造', '医药生物',
            '公用事业', '交通运输', '房地产', '商贸零售', '社会服务',
            '银行', '非银金融', '综合', '计算机', '传媒',
            '通信', '煤炭', '石油石化', '环保', '机械设备',
            '汽车', '建筑材料', '建筑装饰', '电力设备', '国防军工', '美容护理'
        ]
        
        for industry in tqdm(industries, desc="下载行业指数"):
            try:
                # 获取行业指数数据
                df = ak.stock_board_industry_name_em(symbol=industry)
                
                if df is not None and len(df) > 0:
                    df['symbol'] = industry
                    df.columns = ['date', 'close', 'change_rate', 'amount', 'volume', 'open', 'high', 'low', 'symbol']
                    
                    df.to_sql('industry_index', conn, if_exists='append', index=False, method='ignore')
                
                time.sleep(0.3)
                
            except Exception as e:
                logger.error(f"   ❌ {industry} 失败：{e}")
        
        conn.commit()
        conn.close()
        logger.info("✅ 行业指数下载完成")
    
    def show_summary(self):
        """显示下载汇总"""
        logger.info("\n" + "="*60)
        logger.info("📊 AKShare 增强数据下载汇总")
        logger.info("="*60)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        tables = ['index_daily', 'etf_daily', 'north_money_flow', 'billboard', 
                  'industry_index', 'stock_info_extended']
        
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


def main():
    """主函数"""
    logger.info("="*80)
    logger.info("AKShare 增强数据下载工具")
    logger.info("下载内容：指数 + ETF + 北向资金 + 龙虎榜 + 行业指数")
    logger.info("="*80)
    
    # 初始化下载器
    downloader = AKShareEnhancedDownloader()
    
    # 下载各类数据
    downloader.download_index_daily(start_date="2020-01-01")
    downloader.download_etf_daily(start_date="2020-01-01")
    downloader.download_north_money_flow(start_date="2020-01-01")
    downloader.download_billboard(start_date="2023-01-01")
    downloader.download_stock_info_extended()
    downloader.download_industry_index()
    
    # 显示汇总
    downloader.show_summary()
    
    logger.info("\n✅ 所有下载任务完成！")


if __name__ == "__main__":
    main()

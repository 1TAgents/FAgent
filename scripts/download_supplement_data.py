#!/usr/bin/env python3
"""
补充下载：行业板块和指数数据

使用 RQSDK 下载：
1. 申万行业分类
2. 主要指数数据
3. 指数成分股
"""
import rqdatac as rq
import sqlite3
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def init_database(db_path: str = "data/stock_data.db"):
    """初始化数据库表结构"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 创建行业分类表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS industry_info (
            symbol TEXT PRIMARY KEY,
            symbol_name TEXT,
            exchange TEXT,
            sw_industry_level1 TEXT,      -- 申万一级行业
            sw_industry_level2 TEXT,      -- 申万二级行业
            sw_industry_level3 TEXT,      -- 申万三级行业
            czsc_industry TEXT,           -- 中证行业
            market_cap REAL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # 创建指数数据表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS index_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            index_code TEXT NOT NULL,
            index_name TEXT,
            datetime TIMESTAMP NOT NULL,
            open_price REAL,
            high_price REAL,
            low_price REAL,
            close_price REAL,
            volume REAL,
            turnover REAL,
            UNIQUE(index_code, datetime)
        )
    """)
    
    # 创建指数成分股表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS index_components (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            index_code TEXT NOT NULL,
            symbol TEXT NOT NULL,
            symbol_name TEXT,
            weight REAL,
            industry TEXT,
            market_cap REAL,
            update_date TEXT,
            UNIQUE(index_code, symbol, update_date)
        )
    """)
    
    # 创建概念板块表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS concept_info (
            symbol TEXT,
            concept_name TEXT,
            concept_code TEXT,
            PRIMARY KEY (symbol, concept_code)
        )
    """)
    
    # 创建索引
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_industry_sw1 ON industry_info(sw_industry_level1)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_index_code ON index_data(index_code)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_component_index ON index_components(index_code)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_component_symbol ON index_components(symbol)")
    
    conn.commit()
    conn.close()
    logger.info("✓ 数据库表结构初始化完成")


def download_industry_info(db_path: str):
    """下载行业分类信息"""
    logger.info("开始下载行业分类信息...")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # 获取所有股票
        stocks = rq.all_instruments(type='CS', market='cn')
        
        industry_data = []
        for _, row in stocks.iterrows():
            symbol = row['order_book_id'].split('.')[0]
            industry_data.append((
                symbol,
                row['symbol_name'],
                'SSE' if '.XSHG' in row['order_book_id'] else 'SZE',
                row.get('sw_l1', ''),      # 申万一级行业
                row.get('sw_l2', ''),      # 申万二级行业
                row.get('sw_l3', ''),      # 申万三级行业
                row.get('industry', ''),   # 中证行业
                row.get('market_cap', 0),
            ))
            
            # 批量插入
            if len(industry_data) >= 500:
                cursor.executemany("""
                    INSERT OR REPLACE INTO industry_info 
                    (symbol, symbol_name, exchange, sw_industry_level1, sw_industry_level2, 
                     sw_industry_level3, czsc_industry, market_cap)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, industry_data)
                conn.commit()
                industry_data = []
        
        # 插入剩余数据
        if industry_data:
            cursor.executemany("""
                INSERT OR REPLACE INTO industry_info 
                (symbol, symbol_name, exchange, sw_industry_level1, sw_industry_level2, 
                 sw_industry_level3, czsc_industry, market_cap)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, industry_data)
            conn.commit()
        
        # 统计
        cursor.execute("SELECT COUNT(*) FROM industry_info")
        count = cursor.fetchone()[0]
        logger.info(f"✓ 行业信息下载完成 | {count} 只股票")
        
        # 行业分布统计
        cursor.execute("""
            SELECT sw_industry_level1, COUNT(*) as count
            FROM industry_info
            WHERE sw_industry_level1 != ''
            GROUP BY sw_industry_level1
            ORDER BY count DESC
        """)
        
        logger.info("\n申万一级行业分布:")
        for row in cursor.fetchall():
            logger.info(f"  {row[0]:20s}: {row[1]:4d} 只")
        
    except Exception as e:
        logger.error(f"行业信息下载失败：{e}")
    finally:
        conn.close()


def download_index_data(db_path: str):
    """下载主要指数数据"""
    logger.info("开始下载指数数据...")
    
    # 主要指数列表
    indices = {
        '000300.XSHG': '沪深 300',
        '000001.XSHG': '上证指数',
        '000016.XSHG': '上证 50',
        '000905.XSHG': '中证 500',
        '399001.XSHE': '深证成指',
        '399005.XSHE': '中小板指',
        '399006.XSHE': '创业板指',
        '000688.XSHG': '科创 50',
        '000852.XSHG': '中证 1000',
    }
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    from datetime import datetime, timedelta
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365*10)  # 10 年数据
    
    total_count = 0
    
    for index_code, index_name in indices.items():
        try:
            df = rq.get_price(
                order_book_ids=index_code,
                start_date=start_date.strftime('%Y-%m-%d'),
                end_date=end_date.strftime('%Y-%m-%d'),
                frequency='1d'
            )
            
            if df.empty:
                continue
            
            # 准备数据
            data = []
            for idx, row in df.iterrows():
                data.append((
                    index_code.split('.')[0],
                    index_name,
                    idx.strftime('%Y-%m-%d'),
                    float(row['open']),
                    float(row['high']),
                    float(row['low']),
                    float(row['close']),
                    float(row['volume']),
                    float(row['turnover'])
                ))
            
            # 批量插入
            cursor.executemany("""
                INSERT OR REPLACE INTO index_data 
                (index_code, index_name, datetime, open_price, high_price, low_price, 
                 close_price, volume, turnover)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, data)
            
            conn.commit()
            total_count += len(data)
            logger.info(f"  ✓ {index_name} ({index_code.split('.')[0]}): {len(data)} 条")
            
        except Exception as e:
            logger.error(f"{index_name} 下载失败：{e}")
    
    logger.info(f"✓ 指数数据下载完成 | 总计 {total_count:,} 条")
    conn.close()


def download_index_components(db_path: str):
    """下载指数成分股"""
    logger.info("开始下载指数成分股...")
    
    # 主要指数
    indices = {
        '000300.XSHG': '沪深 300',
        '000016.XSHG': '上证 50',
        '000905.XSHG': '中证 500',
    }
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    update_date = datetime.now().strftime('%Y-%m-%d')
    
    for index_code, index_name in indices.items():
        try:
            components = rq.index_components(index_code)
            
            data = []
            for _, row in components.iterrows():
                data.append((
                    index_code.split('.')[0],
                    row['order_book_id'].split('.')[0],
                    row['symbol_name'],
                    float(row.get('weight', 0)),
                    row.get('industry', ''),
                    float(row.get('market_cap', 0)),
                    update_date
                ))
            
            cursor.executemany("""
                INSERT OR REPLACE INTO index_components 
                (index_code, symbol, symbol_name, weight, industry, market_cap, update_date)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, data)
            
            conn.commit()
            logger.info(f"  ✓ {index_name}: {len(components)} 只成分股")
            
        except Exception as e:
            logger.error(f"{index_name} 成分股下载失败：{e}")
    
    conn.close()
    logger.info("✓ 指数成分股下载完成")


def main():
    """主函数"""
    logger.info("=" * 80)
    logger.info("补充下载：行业板块和指数数据")
    logger.info("=" * 80)
    
    db_path = "data/stock_data.db"
    
    # 初始化数据库
    init_database(db_path)
    
    # 初始化 RQSDK
    rq.init()
    logger.info("✓ RQSDK 初始化完成")
    
    # 下载行业信息
    download_industry_info(db_path)
    
    # 下载指数数据
    download_index_data(db_path)
    
    # 下载指数成分股
    download_index_components(db_path)
    
    logger.info("\n" + "=" * 80)
    logger.info("✅ 所有补充数据下载完成！")
    logger.info("=" * 80)
    
    # 显示统计
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM industry_info")
    logger.info(f"行业信息：{cursor.fetchone()[0]} 只股票")
    
    cursor.execute("SELECT COUNT(*) FROM index_data")
    logger.info(f"指数数据：{cursor.fetchone()[0]:,} 条")
    
    cursor.execute("SELECT COUNT(DISTINCT index_code) FROM index_components")
    logger.info(f"指数成分股：{cursor.fetchone()[0]} 个指数")
    
    conn.close()


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.error(f"下载失败：{e}")
        import traceback
        traceback.print_exc()

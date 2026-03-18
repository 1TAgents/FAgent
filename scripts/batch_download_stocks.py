#!/usr/bin/env python3
"""
批量下载股票历史数据

下载更多股票的历史数据，用于策略回测
"""
import sys
from pathlib import Path

# 动态添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import sqlite3
import pandas as pd
import akshare as ak
from datetime import datetime, timedelta
import time
from typing import List, Tuple

# 数据库路径
DB_PATH = Path(__file__).parent.parent / "data" / "stock_data.db"

# 股票池配置
STOCK_POOLS = {
    "沪深 300": "000300",
    "中证 500": "000905",
    "上证 50": "000016",
    "创业板指": "399006",
    "科创 50": "000688",
}

# 热门股票手动列表（各行业龙头）
POPULAR_STOCKS = [
    # 科技/半导体
    ("002415", "海康威视"),
    ("300750", "宁德时代"),
    ("002230", "科大讯飞"),
    ("688981", "中芯国际"),
    ("000725", "京东方 A"),
    ("600703", "三安光电"),
    ("002371", "北方华创"),
    ("300782", "卓胜微"),
    
    # 消费/白酒
    ("000858", "五粮液"),
    ("002304", "洋河股份"),
    ("600887", "伊利股份"),
    ("000001", "平安银行"),
    ("600036", "招商银行"),
    
    # 医药/医疗
    ("300015", "爱尔眼科"),
    ("000538", "云南白药"),
    ("600276", "恒瑞医药"),
    ("300760", "迈瑞医疗"),
    ("000963", "华东医药"),
    
    # 新能源/光伏
    ("002594", "比亚迪"),
    ("601012", "隆基绿能"),
    ("300014", "亿纬锂能"),
    ("002460", "赣锋锂业"),
    ("300274", "阳光电源"),
    
    # 金融/地产
    ("600000", "浦发银行"),
    ("600016", "民生银行"),
    ("601166", "兴业银行"),
    ("000002", "万科 A"),
    ("600048", "保利发展"),
    
    # 周期/制造
    ("600028", "中国石化"),
    ("601857", "中国石油"),
    ("600519", "贵州茅台"),  # 已有
    ("601318", "中国平安"),
    ("600030", "中信证券"),
    
    # 其他热门
    ("002252", "上海莱士"),  # 已有
    ("002600", "领益智造"),  # 已有
    ("300589", "江龙船艇"),  # 已有
    ("600026", "中远海能"),  # 已有
    ("601607", "上海医药"),  # 已有
]


def init_db():
    """初始化数据库"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 创建表（如果不存在）
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS klines (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        symbol TEXT NOT NULL,
        date TEXT NOT NULL,
        open REAL,
        high REAL,
        low REAL,
        close REAL,
        volume REAL,
        turnover REAL,
        change_percent REAL,
        UNIQUE(symbol, date)
    )
    ''')
    
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_symbol_date ON klines(symbol, date)')
    conn.commit()
    return conn


def download_stock_klines(symbol: str, start_date: str = "2023-01-01", end_date: str = None) -> pd.DataFrame:
    """
    下载单只股票的 K 线数据
    
    Args:
        symbol: 股票代码
        start_date: 开始日期
        end_date: 结束日期（默认今天）
    
    Returns:
        DataFrame 包含 K 线数据
    """
    if end_date is None:
        end_date = datetime.now().strftime("%Y-%m-%d")
    
    try:
        # 转换日期格式
        start = start_date.replace('-', '')
        end = end_date.replace('-', '')
        
        # 下载数据（前复权）
        df = ak.stock_zh_a_hist(
            symbol=symbol,
            period="daily",
            start_date=start,
            end_date=end,
            adjust="qfq"
        )
        
        if df.empty:
            print(f"  ⚠️  无数据：{symbol}")
            return pd.DataFrame()
        
        # 标准化列名
        df = df.rename(columns={
            '日期': 'date',
            '开盘': 'open',
            '最高': 'high',
            '最低': 'low',
            '收盘': 'close',
            '成交量': 'volume',
            '成交额': 'turnover',
            '涨跌幅': 'change_percent'
        })
        
        # 选择需要的列
        columns = ['date', 'open', 'high', 'low', 'close', 'volume', 'turnover', 'change_percent']
        df = df[[c for c in columns if c in df.columns]]
        df['symbol'] = symbol
        
        return df
        
    except Exception as e:
        print(f"  ❌ 下载失败：{symbol} - {e}")
        return pd.DataFrame()


def save_to_db(conn: sqlite3.Connection, df: pd.DataFrame):
    """保存数据到数据库"""
    if df.empty:
        return 0
    
    # 使用 REPLACE INTO 避免重复
    df.to_sql('klines', conn, if_exists='append', index=False,
              method='replace' if False else None)  # SQLite 不支持 replace，用 INSERT OR REPLACE
    
    # 手动执行 INSERT OR REPLACE
    cursor = conn.cursor()
    saved = 0
    for _, row in df.iterrows():
        cursor.execute('''
        INSERT OR REPLACE INTO klines (symbol, date, open, high, low, close, volume, turnover, change_percent)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            row['symbol'], row['date'], row['open'], row['high'], row['low'],
            row['close'], row['volume'], row['turnover'], row.get('change_percent')
        ))
        saved += 1
    
    conn.commit()
    return saved


def batch_download(stocks: List[Tuple[str, str]], start_date: str = "2023-01-01", delay: float = 1.0):
    """
    批量下载股票数据
    
    Args:
        stocks: 股票列表 [(symbol, name), ...]
        start_date: 开始日期
        delay: 下载间隔（秒）
    """
    conn = init_db()
    cursor = conn.cursor()
    
    print("=" * 70)
    print(f"批量下载股票数据")
    print(f"  股票数量：{len(stocks)}")
    print(f"  时间范围：{start_date} ~ 今天")
    print(f"  下载间隔：{delay}秒")
    print("=" * 70)
    print()
    
    total_saved = 0
    success_count = 0
    fail_count = 0
    
    for i, (symbol, name) in enumerate(stocks, 1):
        print(f"[{i:3d}/{len(stocks)}] {symbol} ({name})...", end=" ")
        
        # 检查是否已存在
        cursor.execute('SELECT COUNT(*) FROM klines WHERE symbol = ?', (symbol,))
        existing = cursor.fetchone()[0]
        
        if existing > 200:
            print(f"✓ 已有 {existing}行，跳过")
            continue
        
        # 下载数据
        df = download_stock_klines(symbol, start_date)
        
        if not df.empty:
            saved = save_to_db(conn, df)
            total_saved += saved
            success_count += 1
            print(f"✓ 下载 {saved}行")
        else:
            fail_count += 1
            print(f"✗ 失败")
        
        # 延迟，避免请求过快
        if i < len(stocks):
            time.sleep(delay)
    
    print()
    print("=" * 70)
    print(f"下载完成！")
    print(f"  成功：{success_count} 只")
    print(f"  失败：{fail_count} 只")
    print(f"  新增：{total_saved} 行")
    print("=" * 70)
    
    conn.close()


def get_index_components(index_code: str) -> List[Tuple[str, str]]:
    """
    获取指数成分股
    
    Args:
        index_code: 指数代码（如 000300）
    
    Returns:
        成分股列表 [(symbol, name), ...]
    """
    try:
        # 获取指数成分股
        df = ak.index_stock_cons(index_code)
        
        if df.empty:
            return []
        
        # 提取股票代码和名称
        stocks = []
        for _, row in df.iterrows():
            symbol = row.get('品种代码', row.get('股票代码', ''))
            name = row.get('品种名称', row.get('股票简称', ''))
            if symbol:
                stocks.append((symbol, name))
        
        return stocks
        
    except Exception as e:
        print(f"获取指数成分股失败：{e}")
        return []


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='批量下载股票历史数据')
    parser.add_argument('--start', type=str, default='2023-01-01',
                        help='开始日期 (YYYY-MM-DD)')
    parser.add_argument('--pool', type=str, choices=['popular', 'hs300', 'zz500', 'all'],
                        default='popular', help='股票池选择')
    parser.add_argument('--delay', type=float, default=1.0,
                        help='下载间隔（秒）')
    
    args = parser.parse_args()
    
    # 选择股票池
    if args.pool == 'popular':
        stocks = POPULAR_STOCKS
        print(f"使用股票池：热门股票 ({len(stocks)}只)")
    elif args.pool == 'hs300':
        print(f"获取沪深 300 成分股...")
        stocks = get_index_components('000300')
        print(f"获取到 {len(stocks)} 只成分股")
    elif args.pool == 'zz500':
        print(f"获取中证 500 成分股...")
        stocks = get_index_components('000905')
        print(f"获取到 {len(stocks)} 只成分股")
    else:
        stocks = POPULAR_STOCKS
    
    if not stocks:
        print("❌ 股票池为空，退出")
        return
    
    # 开始下载
    batch_download(stocks, args.start, args.delay)


if __name__ == "__main__":
    main()

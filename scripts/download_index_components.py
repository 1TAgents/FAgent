#!/usr/bin/env python3
"""
下载指数成分股历史数据

下载沪深 300 + 中证 500 成分股（共 800 只），覆盖 A 股核心资产
"""
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import sqlite3
import pandas as pd
import time
from typing import List, Tuple

DB_PATH = Path(__file__).parent.parent / "data" / "stock_data.db"


def get_index_components_baostock(index_type: str) -> List[Tuple[str, str]]:
    """
    获取指数成分股（使用 Baostock）
    
    Args:
        index_type: 指数类型 (hs300, sz50, zz500)
    
    Returns:
        成分股列表 [(symbol, name), ...]
    """
    import baostock as bs
    
    # 登录
    bs.login()
    
    # 查询成分股
    if index_type == "hs300":
        rs = bs.query_hs300_stocks()
    elif index_type == "sz50":
        rs = bs.query_sz50_stocks()
    elif index_type == "zz500":
        rs = bs.query_zz500_stocks()
    else:
        rs = bs.query_hs300_stocks()
    
    stocks = []
    while rs.next():
        row = rs.get_row_data()
        # 格式：[date, code, name]
        if len(row) >= 2:
            code = row[1]
            name = row[2] if len(row) >= 3 else ""
            # 提取股票代码（去掉 sh./sz. 前缀）
            if code.startswith('sh.'):
                symbol = code[3:]
            elif code.startswith('sz.'):
                symbol = code[3:]
            else:
                symbol = code
            
            stocks.append((symbol, name))
    
    bs.logout()
    return stocks


def download_with_baostock(symbol: str, start_date: str = "2023-01-01", end_date: str = None) -> pd.DataFrame:
    """使用 Baostock 下载单只股票数据"""
    import baostock as bs
    
    if end_date is None:
        end_date = time.strftime('%Y-%m-%d')
    
    # 确定市场前缀
    if symbol.startswith('6') or symbol.startswith('9'):
        code = f"sh.{symbol}"
    else:
        code = f"sz.{symbol}"
    
    # 下载数据（前复权）
    rs = bs.query_history_k_data_plus(
        code,
        "date,open,high,low,close,volume,amount",
        start_date=start_date,
        end_date=end_date,
        frequency="d",
        adjustflag="2"  # 前复权
    )
    
    data_list = []
    while rs.next():
        data_list.append(rs.get_row_data())
    
    if not data_list:
        return pd.DataFrame()
    
    df = pd.DataFrame(data_list, columns=rs.fields)
    
    # 标准化列名
    df = df.rename(columns={
        'date': 'date',
        'open': 'open',
        'high': 'high',
        'low': 'low',
        'close': 'close',
        'volume': 'volume',
        'amount': 'turnover'
    })
    
    # 选择需要的列
    columns = ['date', 'open', 'high', 'low', 'close', 'volume', 'turnover']
    df = df[[c for c in columns if c in df.columns]]
    df['symbol'] = symbol
    
    # 转换数据类型
    for col in ['open', 'high', 'low', 'close', 'volume', 'turnover']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    
    return df


def init_db():
    """初始化数据库"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
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


def save_to_db(conn: sqlite3.Connection, df: pd.DataFrame) -> int:
    """保存数据到数据库"""
    if df.empty:
        return 0
    
    cursor = conn.cursor()
    saved = 0
    
    for _, row in df.iterrows():
        cursor.execute('''
        INSERT OR REPLACE INTO klines (symbol, date, open, high, low, close, volume, turnover, change_percent)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            row['symbol'], row['date'], row['open'], row['high'], row['low'],
            row['close'], row['volume'], row['turnover'], 0
        ))
        saved += 1
    
    conn.commit()
    return saved


def batch_download(stocks: List[Tuple[str, str]], start_date: str = "2023-01-01", delay: float = 0.3):
    """批量下载股票数据"""
    import baostock as bs
    bs.login()
    print("✓ Baostock 登录成功")
    
    conn = init_db()
    cursor = conn.cursor()
    
    print("=" * 80)
    print(f"批量下载指数成分股数据")
    print(f"  股票数量：{len(stocks)}")
    print(f"  时间范围：{start_date} ~ 今天")
    print(f"  下载间隔：{delay}秒")
    print("=" * 80)
    print()
    
    total_saved = 0
    success_count = 0
    fail_count = 0
    skip_count = 0
    
    for i, (symbol, name) in enumerate(stocks, 1):
        # 进度显示（每 10 只显示一次）
        if i % 10 == 0 or i == 1:
            print(f"[{i:3d}/{len(stocks)}] 处理中...", end="\r")
        
        # 检查是否已存在
        cursor.execute('SELECT COUNT(*) FROM klines WHERE symbol = ?', (symbol,))
        existing = cursor.fetchone()[0]
        
        if existing >= 240:
            skip_count += 1
            continue
        
        # 下载数据
        try:
            df = download_with_baostock(symbol, start_date)
            
            if not df.empty:
                saved = save_to_db(conn, df)
                total_saved += saved
                success_count += 1
            else:
                fail_count += 1
        except Exception as e:
            fail_count += 1
        
        # 延迟
        if i < len(stocks):
            time.sleep(delay)
    
    print()
    print("=" * 80)
    print(f"下载完成！")
    print(f"  成功：{success_count} 只")
    print(f"  失败：{fail_count} 只")
    print(f"  跳过：{skip_count} 只")
    print(f"  新增：{total_saved:,} 行")
    print("=" * 80)
    
    bs.logout()
    conn.close()


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='下载指数成分股数据')
    parser.add_argument('--index', type=str, default='hs300',
                        choices=['hs300', 'zz500', 'zh500', 'all'],
                        help='选择指数')
    parser.add_argument('--start', type=str, default='2023-01-01',
                        help='开始日期')
    parser.add_argument('--delay', type=float, default=0.3,
                        help='下载间隔（秒）')
    
    args = parser.parse_args()
    
    print()
    print("=" * 80)
    print("获取指数成分股列表")
    print("=" * 80)
    print()
    
    all_stocks = []
    
    if args.index in ['hs300', 'all']:
        print("获取沪深 300 成分股...")
        hs300 = get_index_components_baostock("hs300")
        print(f"  沪深 300: {len(hs300)} 只")
        all_stocks.extend(hs300)
    
    if args.index in ['zz500', 'all']:
        print("获取中证 500 成分股...")
        zz500 = get_index_components_baostock("zz500")
        print(f"  中证 500: {len(zz500)} 只")
        all_stocks.extend(zz500)
    
    if args.index in ['sz50', 'all']:
        print("获取上证 50 成分股...")
        sz50 = get_index_components_baostock("sz50")
        print(f"  上证 50: {len(sz50)} 只")
        all_stocks.extend(sz50)
    
    # 去重
    unique_stocks = list(set(all_stocks))
    print()
    print(f"总计：{len(unique_stocks)} 只不重复股票")
    print()
    
    # 开始下载
    batch_download(unique_stocks, args.start, args.delay)


if __name__ == "__main__":
    main()

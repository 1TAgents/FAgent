#!/usr/bin/env python3
"""
批量下载股票历史数据 - 使用 Baostock 数据源

Baostock 优势：
- 免费，无需注册 token
- 国内直连，速度快
- 数据覆盖全（2007 年至今）
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


# 股票池 - 各行业龙头 + 沪深 300 成分股（精选）
STOCK_POOL = [
    # 科技/半导体
    ("002415", "海康威视"),
    ("300750", "宁德时代"),
    ("002230", "科大讯飞"),
    ("688981", "中芯国际"),
    ("000725", "京东方 A"),
    ("600703", "三安光电"),
    ("002371", "北方华创"),
    ("300782", "卓胜微"),
    ("002049", "紫光国微"),
    ("600584", "长电科技"),
    
    # 消费/白酒
    ("000858", "五粮液"),
    ("002304", "洋河股份"),
    ("600887", "伊利股份"),
    ("000001", "平安银行"),
    ("600036", "招商银行"),
    ("600519", "贵州茅台"),  # 已有
    ("000568", "泸州老窖"),
    ("600809", "山西汾酒"),
    ("000799", "酒鬼酒"),
    
    # 医药/医疗
    ("300015", "爱尔眼科"),
    ("000538", "云南白药"),
    ("600276", "恒瑞医药"),
    ("300760", "迈瑞医疗"),
    ("000963", "华东医药"),
    ("600436", "片仔癀"),
    ("300122", "智飞生物"),
    
    # 新能源/光伏
    ("002594", "比亚迪"),
    ("601012", "隆基绿能"),
    ("300014", "亿纬锂能"),
    ("002460", "赣锋锂业"),
    ("300274", "阳光电源"),
    ("002129", "TCL 中环"),
    ("600438", "通威股份"),
    
    # 金融/地产
    ("600000", "浦发银行"),
    ("600016", "民生银行"),
    ("601166", "兴业银行"),
    ("000002", "万科 A"),
    ("600048", "保利发展"),
    ("601318", "中国平安"),
    ("600030", "中信证券"),
    ("601688", "华泰证券"),
    
    # 周期/制造
    ("600028", "中国石化"),
    ("601857", "中国石油"),
    ("600585", "海螺水泥"),
    ("601668", "中国建筑"),
    ("600019", "宝钢股份"),
    
    # 其他热门
    ("002252", "上海莱士"),  # 已有
    ("002600", "领益智造"),  # 已有
    ("300589", "江龙船艇"),  # 已有
    ("600026", "中远海能"),  # 已有
    ("601607", "上海医药"),  # 已有
    ("600354", "盟固利"),    # 已有
]


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


def download_with_baostock(symbol: str, start_date: str = "2023-01-01", end_date: str = None) -> pd.DataFrame:
    """
    使用 Baostock 下载股票数据
    
    Args:
        symbol: 股票代码
        start_date: 开始日期
        end_date: 结束日期
    
    Returns:
        DataFrame 包含 K 线数据
    """
    import baostock as bs
    
    if end_date is None:
        end_date = time.strftime('%Y-%m-%d')
    
    # 转换日期格式
    start = start_date
    
    # 下载数据（前复权）
    rs = bs.query_history_k_data_plus(
        f"sh.{symbol}" if symbol.startswith('6') else f"sz.{symbol}",
        "date,open,high,low,close,volume,amount,turn,tradestatus,pctChg,peTTM,pbMRQ,psTTM,pcfNcfTTM,isST",
        start_date=start,
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
        'amount': 'turnover',
        'pctChg': 'change_percent'
    })
    
    # 选择需要的列
    columns = ['date', 'open', 'high', 'low', 'close', 'volume', 'turnover', 'change_percent']
    df = df[[c for c in columns if c in df.columns]]
    df['symbol'] = symbol
    
    # 转换数据类型
    for col in ['open', 'high', 'low', 'close', 'volume', 'turnover', 'change_percent']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    
    return df


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
            row['close'], row['volume'], row['turnover'], row.get('change_percent')
        ))
        saved += 1
    
    conn.commit()
    return saved


def batch_download(stocks: List[Tuple[str, str]], start_date: str = "2023-01-01", delay: float = 0.5):
    """
    批量下载股票数据
    """
    # 登录 Baostock
    import baostock as bs
    bs.login()
    print("Baostock 登录成功")
    
    conn = init_db()
    cursor = conn.cursor()
    
    print("=" * 70)
    print(f"批量下载股票数据（Baostock 数据源）")
    print(f"  股票数量：{len(stocks)}")
    print(f"  时间范围：{start_date} ~ 今天")
    print(f"  下载间隔：{delay}秒")
    print("=" * 70)
    print()
    
    total_saved = 0
    success_count = 0
    fail_count = 0
    skip_count = 0
    
    for i, (symbol, name) in enumerate(stocks, 1):
        print(f"[{i:3d}/{len(stocks)}] {symbol} ({name})...", end=" ")
        
        # 检查是否已存在
        cursor.execute('SELECT COUNT(*) FROM klines WHERE symbol = ?', (symbol,))
        existing = cursor.fetchone()[0]
        
        if existing >= 240:
            print(f"✓ 已有 {existing}行，跳过")
            skip_count += 1
            continue
        
        # 下载数据
        try:
            df = download_with_baostock(symbol, start_date)
            
            if not df.empty:
                saved = save_to_db(conn, df)
                total_saved += saved
                success_count += 1
                print(f"✓ 下载 {saved}行")
            else:
                fail_count += 1
                print(f"✗ 无数据")
        except Exception as e:
            fail_count += 1
            print(f"✗ 失败：{e}")
        
        # 延迟，避免请求过快
        if i < len(stocks):
            time.sleep(delay)
    
    print()
    print("=" * 70)
    print(f"下载完成！")
    print(f"  成功：{success_count} 只")
    print(f"  失败：{fail_count} 只")
    print(f"  跳过：{skip_count} 只")
    print(f"  新增：{total_saved} 行")
    print("=" * 70)
    
    # 登出
    bs.logout()
    conn.close()


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='批量下载股票历史数据（Baostock）')
    parser.add_argument('--start', type=str, default='2023-01-01',
                        help='开始日期 (YYYY-MM-DD)')
    parser.add_argument('--delay', type=float, default=0.5,
                        help='下载间隔（秒）')
    
    args = parser.parse_args()
    
    print(f"使用股票池：{len(STOCK_POOL)}只")
    
    # 开始下载
    batch_download(STOCK_POOL, args.start, args.delay)


if __name__ == "__main__":
    main()

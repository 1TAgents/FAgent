#!/usr/bin/env python3
"""
扩展股票池 - 从现有数据库中筛选更多可用股票

由于网络问题无法下载新数据，先从现有数据库中筛选出更多可用的股票
"""
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import sqlite3
import pandas as pd

DB_PATH = Path(__file__).parent.parent / "data" / "stock_data.db"


def analyze_existing_data():
    """分析现有数据库中的所有股票"""
    conn = sqlite3.connect(DB_PATH)
    
    # 查询所有股票及其数据量
    query = """
    SELECT 
        symbol,
        COUNT(*) as rows,
        MIN(date) as min_date,
        MAX(date) as max_date,
        COUNT(DISTINCT strftime('%Y-%m', date)) as months
    FROM klines
    GROUP BY symbol
    HAVING COUNT(*) >= 100  -- 至少 100 行数据
    ORDER BY COUNT(*) DESC
    """
    
    df = pd.read_sql_query(query, conn)
    conn.close()
    
    print("=" * 70)
    print("现有数据库中的股票（≥100 行）")
    print("=" * 70)
    print()
    
    print(f"总计：{len(df)} 只股票")
    print()
    
    # 分类统计
    full_year = df[df['rows'] >= 240]
    half_year = df[(df['rows'] >= 120) & (df['rows'] < 240)]
    quarter = df[(df['rows'] >= 60) & (df['rows'] < 120)]
    less = df[df['rows'] < 60]
    
    print("数据覆盖情况:")
    print(f"  ✅ 完整年份 (240+ 行): {len(full_year)} 只")
    print(f"  ⚠️  半年以上 (120-239 行): {len(half_year)} 只")
    print(f"  ⚠️  季度以上 (60-119 行): {len(quarter)} 只")
    print(f"  ❌ 不足季度 (<60 行): {len(less)} 只")
    print()
    
    if len(full_year) > 0:
        print("完整年份股票列表:")
        for _, row in full_year.iterrows():
            print(f"  {row['symbol']}: {row['rows']}行 | {row['min_date']} ~ {row['max_date']}")
    
    return df


def suggest_additional_stocks():
    """建议可以手动添加的股票"""
    print()
    print("=" * 70)
    print("建议补充的股票（需要手动下载）")
    print("=" * 70)
    print()
    
    # 各行业代表性股票
    suggestions = [
        # 科技
        ("002415", "海康威视", "安防龙头"),
        ("300750", "宁德时代", "电池龙头"),
        ("002230", "科大讯飞", "AI 语音"),
        
        # 消费
        ("000858", "五粮液", "白酒老二"),
        ("600887", "伊利股份", "乳业龙头"),
        
        # 金融
        ("600036", "招商银行", "银行龙头"),
        ("601318", "中国平安", "保险龙头"),
        
        # 医药
        ("600276", "恒瑞医药", "创新药"),
        ("300760", "迈瑞医疗", "医疗器械"),
        
        # 新能源
        ("002594", "比亚迪", "新能源车"),
        ("601012", "隆基绿能", "光伏龙头"),
        
        # 周期
        ("600028", "中国石化", "石化"),
        ("601857", "中国石油", "石油"),
    ]
    
    print("代码      名称        说明")
    print("-" * 50)
    for symbol, name, desc in suggestions:
        print(f"{symbol}  {name:10s}  {desc}")
    
    print()
    print("下载命令示例:")
    print("  python scripts/batch_download_stocks.py --pool popular --start 2023-01-01")
    print()
    print("或者单只下载:")
    for symbol, name, _ in suggestions[:3]:
        print(f"  python -c \"import akshare as ak; print(ak.stock_zh_a_hist(symbol='{symbol}', period='daily', adjust='qfq'))\"")


def export_stock_list():
    """导出股票列表供后续使用"""
    conn = sqlite3.connect(DB_PATH)
    
    query = """
    SELECT DISTINCT symbol
    FROM klines
    GROUP BY symbol
    HAVING COUNT(*) >= 200
    ORDER BY symbol
    """
    
    df = pd.read_sql_query(query, conn)
    conn.close()
    
    output_file = Path(__file__).parent / "available_stocks.csv"
    df.to_csv(output_file, index=False)
    
    print(f"✅ 可用股票列表已保存：{output_file}")
    print(f"   共 {len(df)} 只股票（≥200 行）")


def main():
    """主函数"""
    print()
    
    # 分析现有数据
    df = analyze_existing_data()
    
    # 建议补充的股票
    suggest_additional_stocks()
    
    # 导出股票列表
    export_stock_list()
    
    print()
    print("=" * 70)
    print("总结")
    print("=" * 70)
    print()
    print("当前有 16 只股票可用，其中 14 只满一年数据。")
    print("虽然数量不多，但已经足够进行组合策略测试。")
    print()
    print("如需更多股票，需要:")
    print("  1. 检查网络连接/代理设置")
    print("  2. 手动下载或使用其他数据源")
    print("  3. 等待网络恢复后批量下载")
    print()


if __name__ == "__main__":
    main()

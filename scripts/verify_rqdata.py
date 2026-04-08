#!/usr/bin/env python3
"""
聚宽数据验证工具
验证下载数据的完整性和质量
"""

import sqlite3
import pandas as pd
from pathlib import Path
from datetime import datetime
import sys


def verify_database(db_path: str):
    """验证数据库"""
    db_path = Path(db_path)
    
    if not db_path.exists():
        print(f"❌ 数据库文件不存在：{db_path}")
        return False
    
    print("=" * 80)
    print(f"聚宽数据验证报告")
    print(f"数据库：{db_path.absolute()}")
    print(f"验证时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    print()
    
    conn = sqlite3.connect(db_path)
    
    # 1. 验证 A 股日线数据
    print("📊 A 股日线数据 (daily_bars)")
    print("-" * 60)
    
    try:
        # 股票数量
        stock_count = pd.read_sql_query("""
            SELECT COUNT(DISTINCT symbol || '_' || exchange) as count
            FROM daily_bars
        """, conn).iloc[0]['count']
        print(f"  ✓ 股票数量：{stock_count} 只")
        
        # 总数据量
        total_bars = pd.read_sql_query("""
            SELECT COUNT(*) as count FROM daily_bars
        """, conn).iloc[0]['count']
        print(f"  ✓ 总数据量：{total_bars:,} 条")
        
        # 时间范围
        date_range = pd.read_sql_query("""
            SELECT MIN(datetime) as start, MAX(datetime) as end
            FROM daily_bars
        """, conn).iloc[0]
        print(f"  ✓ 时间范围：{date_range['start']} 至 {date_range['end']}")
        
        # 数据质量检查
        null_check = pd.read_sql_query("""
            SELECT 
                SUM(CASE WHEN open IS NULL THEN 1 ELSE 0 END) as open_null,
                SUM(CASE WHEN close IS NULL THEN 1 ELSE 0 END) as close_null,
                SUM(CASE WHEN volume IS NULL THEN 1 ELSE 0 END) as volume_null
            FROM daily_bars
        """, conn).iloc[0]
        print(f"  ✓ 数据质量：open 空值={null_check['open_null']:,}, "
              f"close 空值={null_check['close_null']:,}, "
              f"volume 空值={null_check['volume_null']:,}")
        
        # 复权类型分布
        adjust_dist = pd.read_sql_query("""
            SELECT adjust_type, COUNT(*) as count
            FROM daily_bars
            GROUP BY adjust_type
        """, conn)
        print(f"  ✓ 复权类型分布:")
        for _, row in adjust_dist.iterrows():
            print(f"      - {row['adjust_type']}: {row['count']:,} 条")
        
        # 示例数据（贵州茅台）
        print(f"\n  示例：贵州茅台 (600519) 最近 5 日数据")
        moutai = pd.read_sql_query("""
            SELECT datetime, open, high, low, close, volume, turnover
            FROM daily_bars
            WHERE symbol = '600519' AND exchange = 'XSHG'
            ORDER BY datetime DESC
            LIMIT 5
        """, conn)
        print(moutai.to_string(index=False))
        
    except Exception as e:
        print(f"  ❌ 验证失败：{e}")
    
    print()
    
    # 2. 验证期货日线数据
    print("📊 期货日线数据 (futures_daily)")
    print("-" * 60)
    
    try:
        # 合约数量
        contract_count = pd.read_sql_query("""
            SELECT COUNT(DISTINCT symbol || '_' || exchange) as count
            FROM futures_daily
        """, conn).iloc[0]['count']
        print(f"  ✓ 合约数量：{contract_count} 个")
        
        # 总数据量
        total_bars = pd.read_sql_query("""
            SELECT COUNT(*) as count FROM futures_daily
        """, conn).iloc[0]['count']
        print(f"  ✓ 总数据量：{total_bars:,} 条")
        
        # 时间范围
        date_range = pd.read_sql_query("""
            SELECT MIN(datetime) as start, MAX(datetime) as end
            FROM futures_daily
        """, conn).iloc[0]
        if date_range['start']:
            print(f"  ✓ 时间范围：{date_range['start']} 至 {date_range['end']}")
        else:
            print(f"  ⚠ 无数据")
        
        # 示例数据（沪深 300 股指期货）
        print(f"\n  示例：沪深 300 股指期货最近 5 日数据")
        if_data = pd.read_sql_query("""
            SELECT datetime, symbol, exchange, open, high, low, close, 
                   volume, open_interest
            FROM futures_daily
            WHERE symbol LIKE 'IF%'
            ORDER BY datetime DESC
            LIMIT 5
        """, conn)
        if len(if_data) > 0:
            print(if_data.to_string(index=False))
        else:
            print("  ⚠ 无沪深 300 股指期货数据")
        
    except Exception as e:
        print(f"  ❌ 验证失败：{e}")
    
    print()
    
    # 3. 验证财务数据
    print("📊 财务数据 (fundamentals)")
    print("-" * 60)
    
    try:
        # 股票数量
        stock_count = pd.read_sql_query("""
            SELECT COUNT(DISTINCT symbol || '_' || exchange) as count
            FROM fundamentals
        """, conn).iloc[0]['count']
        print(f"  ✓ 股票数量：{stock_count} 只")
        
        # 总数据量
        total_records = pd.read_sql_query("""
            SELECT COUNT(*) as count FROM fundamentals
        """, conn).iloc[0]['count']
        print(f"  ✓ 总记录数：{total_records:,} 条")
        
        # 时间范围
        date_range = pd.read_sql_query("""
            SELECT MIN(date) as start, MAX(date) as end
            FROM fundamentals
        """, conn).iloc[0]
        if date_range['start']:
            print(f"  ✓ 时间范围：{date_range['start']} 至 {date_range['end']}")
        else:
            print(f"  ⚠ 无数据")
        
        # 字段完整性
        field_check = pd.read_sql_query("""
            SELECT 
                SUM(CASE WHEN pe_ratio IS NULL THEN 1 ELSE 0 END) as pe_null,
                SUM(CASE WHEN pb_ratio IS NULL THEN 1 ELSE 0 END) as pb_null,
                SUM(CASE WHEN market_cap IS NULL THEN 1 ELSE 0 END) as cap_null
            FROM fundamentals
        """, conn).iloc[0]
        print(f"  ✓ 数据质量：PE 空值={field_check['pe_null']:,}, "
              f"PB 空值={field_check['pb_null']:,}, "
              f"市值空值={field_check['cap_null']:,}")
        
    except Exception as e:
        print(f"  ❌ 验证失败：{e}")
    
    print()
    
    # 4. 验证分红数据
    print("📊 分红数据 (dividends)")
    print("-" * 60)
    
    try:
        # 有分红的股票数量
        stock_count = pd.read_sql_query("""
            SELECT COUNT(DISTINCT symbol || '_' || exchange) as count
            FROM dividends
        """, conn).iloc[0]['count']
        print(f"  ✓ 有分红的股票：{stock_count} 只")
        
        # 总记录数
        total_records = pd.read_sql_query("""
            SELECT COUNT(*) as count FROM dividends
        """, conn).iloc[0]['count']
        print(f"  ✓ 总分红记录：{total_records:,} 条")
        
        # 时间范围
        date_range = pd.read_sql_query("""
            SELECT MIN(announcement_date) as start, 
                   MAX(announcement_date) as end
            FROM dividends
        """, conn).iloc[0]
        if date_range['start']:
            print(f"  ✓ 时间范围：{date_range['start']} 至 {date_range['end']}")
        else:
            print(f"  ⚠ 无数据")
        
        # 示例数据
        print(f"\n  示例：贵州茅台分红记录")
        moutai_div = pd.read_sql_query("""
            SELECT announcement_date, record_date, ex_dividend_date,
                   cash_dividend, share_dividend
            FROM dividends
            WHERE symbol = '600519' AND exchange = 'XSHG'
            ORDER BY announcement_date DESC
            LIMIT 5
        """, conn)
        if len(moutai_div) > 0:
            print(moutai_div.to_string(index=False))
        else:
            print("  ⚠ 无贵州茅台分红数据")
        
    except Exception as e:
        print(f"  ❌ 验证失败：{e}")
    
    print()
    
    # 5. 数据库文件大小
    db_size_mb = db_path.stat().st_size / (1024 * 1024)
    print(f"💾 数据库文件大小：{db_size_mb:.2f} MB")
    
    print()
    print("=" * 80)
    print("✅ 数据验证完成！")
    print("=" * 80)
    
    conn.close()
    return True


def verify_data_quality(db_path: str):
    """数据质量深度检查"""
    print("\n" + "=" * 80)
    print("数据质量深度检查")
    print("=" * 80)
    
    conn = sqlite3.connect(db_path)
    
    # 1. 检查价格合理性
    print("\n🔍 检查价格合理性...")
    price_check = pd.read_sql_query("""
        SELECT 
            symbol,
            exchange,
            COUNT(*) as days,
            SUM(CASE WHEN high < low THEN 1 ELSE 0 END) as invalid_hl,
            SUM(CASE WHEN close < 0 THEN 1 ELSE 0 END) as negative_close,
            SUM(CASE WHEN volume < 0 THEN 1 ELSE 0 END) as negative_volume
        FROM daily_bars
        GROUP BY symbol, exchange
        HAVING invalid_hl > 0 OR negative_close > 0 OR negative_volume > 0
        LIMIT 10
    """, conn)
    
    if len(price_check) > 0:
        print(f"  ⚠ 发现 {len(price_check)} 只股票存在数据质量问题")
        print(price_check.to_string(index=False))
    else:
        print("  ✓ 所有股票价格合理")
    
    # 2. 检查交易连续性
    print("\n🔍 检查交易连续性（随机抽样 10 只股票）...")
    sample_stocks = pd.read_sql_query("""
        SELECT DISTINCT symbol, exchange
        FROM daily_bars
        ORDER BY RANDOM()
        LIMIT 10
    """, conn)
    
    for _, stock in sample_stocks.iterrows():
        symbol = stock['symbol']
        exchange = stock['exchange']
        
        # 获取该股票的时间序列
        dates = pd.read_sql_query("""
            SELECT datetime FROM daily_bars
            WHERE symbol = ? AND exchange = ?
            ORDER BY datetime
        """, conn, params=(symbol, exchange))['datetime'].tolist()
        
        if len(dates) > 1:
            # 检查是否有超过 30 天的间隔（排除节假日）
            gaps = []
            for i in range(1, len(dates)):
                d1 = pd.to_datetime(dates[i-1])
                d2 = pd.to_datetime(dates[i])
                gap_days = (d2 - d1).days
                if gap_days > 30:  # 允许节假日
                    gaps.append(gap_days)
            
            if gaps:
                print(f"  ⚠ {symbol}.{exchange}: 发现 {len(gaps)} 个超过 30 天的间隔")
            else:
                print(f"  ✓ {symbol}.{exchange}: 交易连续")
    
    conn.close()
    print("\n✅ 数据质量检查完成！")


def main():
    """主函数"""
    # 默认数据库路径
    db_path = "data/rqdata/database/daily_bars.db"
    
    if len(sys.argv) > 1:
        db_path = sys.argv[1]
    
    if verify_database(db_path):
        verify_data_quality(db_path)
    else:
        print("\n❌ 数据库验证失败，请检查文件路径")
        sys.exit(1)


if __name__ == '__main__':
    main()

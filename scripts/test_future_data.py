#!/usr/bin/env python3
"""
期货数据测试脚本

测试数据源和数据库功能
"""
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.data.future_source import FutureDataSource
from agents.data.future_database import FutureDatabase
from agents.data.models import Exchange, Interval

def test_data_source():
    """测试数据源"""
    print("=" * 60)
    print("测试数据源")
    print("=" * 60)
    
    data_source = FutureDataSource()
    
    # 测试 1: 获取交易所
    print("\n1. 测试交易所判断:")
    test_symbols = ["IF", "rb", "CU", "M", "SR"]
    for symbol in test_symbols:
        exchange = data_source.get_exchange(symbol)
        print(f"   {symbol:4s} -> {exchange.value}")
    
    # 测试 2: 获取合约乘数
    print("\n2. 测试合约乘数:")
    for symbol in ["IF", "CU", "AU", "RB", "M"]:
        multiplier = data_source.get_contract_multiplier(symbol)
        print(f"   {symbol:4s} -> {multiplier}")
    
    # 测试 3: 下载主力合约数据
    print("\n3. 下载主力合约数据 (IF 日线):")
    df = data_source.get_main_contract_klines(
        symbol="IF",
        period="daily",
        start_date="20240101",
        end_date="20241231"
    )
    
    if not df.empty:
        print(f"   ✓ 下载成功 | rows={len(df)}")
        print(f"   列名：{list(df.columns)}")
        print(f"\n   前 5 行:")
        print(df.head().to_string())
        print(f"\n   后 5 行:")
        print(df.tail().to_string())
    else:
        print("   ✗ 下载失败")
    
    # 测试 4: 获取合约信息
    print("\n4. 获取合约信息:")
    contract = data_source.get_contract_info("IF2403")
    print(f"   品种：{contract.product_name}")
    print(f"   交易所：{contract.exchange.value}")
    print(f"   乘数：{contract.size}")
    print(f"   保证金：{contract.margin_rate}")


def test_database():
    """测试数据库"""
    print("\n" + "=" * 60)
    print("测试数据库")
    print("=" * 60)
    
    database = FutureDatabase(db_path="data/test_future_data.db")
    data_source = FutureDataSource()
    
    # 测试 1: 保存数据
    print("\n1. 保存数据到数据库:")
    df = data_source.get_main_contract_klines(
        symbol="IF",
        period="daily",
        start_date="20240101",
        end_date="20241231"
    )
    
    if not df.empty:
        exchange = data_source.get_exchange("IF")
        interval = data_source.parse_period("daily")
        
        database.save_bars_df(df, "IF", exchange, interval)
        print(f"   ✓ 保存成功 | rows={len(df)}")
    
    # 测试 2: 加载数据
    print("\n2. 从数据库加载数据:")
    exchange = Exchange.CFFEX
    interval = Interval.DAILY
    
    df_loaded = database.load_bars_df("IF", exchange, interval)
    
    if not df_loaded.empty:
        print(f"   ✓ 加载成功 | rows={len(df_loaded)}")
        print(f"\n   前 5 行:")
        print(df_loaded.head().to_string())
    else:
        print("   ✗ 加载失败")
    
    # 测试 3: 数据覆盖
    print("\n3. 查询数据覆盖:")
    coverage = database.get_data_coverage("IF", exchange, interval)
    
    if coverage:
        print(f"   品种：IF")
        print(f"   日期范围：{coverage['start_date'][:10]} ~ {coverage['end_date'][:10]}")
        print(f"   数据量：{coverage['bar_count']} 条")
    else:
        print("   无覆盖信息")


def test_load_bars():
    """测试 BarData 加载"""
    print("\n" + "=" * 60)
    print("测试 BarData 对象加载")
    print("=" * 60)
    
    database = FutureDatabase(db_path="data/test_future_data.db")
    exchange = Exchange.CFFEX
    interval = Interval.DAILY
    
    bars = database.load_bars("IF", exchange, interval)
    
    if bars:
        print(f"\n✓ 加载成功 | count={len(bars)}")
        print(f"\n前 3 个 Bar:")
        for i, bar in enumerate(bars[:3], 1):
            print(f"   {i}. {bar.datetime.date()} O={bar.open_price:.1f} H={bar.high_price:.1f} L={bar.low_price:.1f} C={bar.close_price:.1f}")
    else:
        print("   ✗ 加载失败")


def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("FAgent 期货数据测试")
    print("=" * 60)
    
    try:
        # 测试数据源
        test_data_source()
        
        # 测试数据库
        test_database()
        
        # 测试 BarData 加载
        test_load_bars()
        
        print("\n" + "=" * 60)
        print("✓ 所有测试完成")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n✗ 测试失败：{e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

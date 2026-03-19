#!/usr/bin/env python3
"""
RQSDK 快速测试 - 验证数据获取能力
"""
import rqdatac as rq
import sys

# 您的 License Key
LICENSE_KEY = "YOUR_LICENSE_KEY"

print("=" * 70)
print("RQSDK 快速测试")
print("=" * 70)

# 测试 1: 初始化
print("\n1. 测试初始化...")
try:
    rq.init()
    print("✓ 初始化成功")
except Exception as e:
    print(f"✗ 初始化失败：{e}")
    print("\n正在配置 License...")
    try:
        rq.set_token(LICENSE_KEY)
        rq.init()
        print("✓ License 配置成功，初始化完成")
    except Exception as e2:
        print(f"✗ License 配置失败：{e2}")
        sys.exit(1)

# 测试 2: 获取股票列表
print("\n2. 测试获取 A 股列表...")
try:
    stocks = rq.all_instruments(type='CS', market='cn')
    print(f"✓ A 股总数：{len(stocks)} 只")
    print(f"  示例：{stocks.iloc[:3]['order_book_id'].tolist()}")
except Exception as e:
    print(f"✗ 失败：{e}")

# 测试 3: 获取日线数据
print("\n3. 测试获取日线数据（贵州茅台 600519）...")
try:
    df = rq.get_price(
        order_book_ids='600519.XSHG',
        start_date='2024-01-01',
        end_date='2024-12-31',
        frequency='1d',
        adjust_type='pre'
    )
    print(f"✓ 日线数据获取成功")
    print(f"  数据量：{len(df)} 条")
    print(f"  时间范围：{df.index[0]} 至 {df.index[-1]}")
    print(f"  字段：{df.columns.tolist()}")
    print(f"\n  最新数据:")
    print(f"    收盘价：{df['close'].iloc[-1]:.2f}")
    print(f"    成交量：{df['volume'].iloc[-1]:.0f}")
    print(f"    成交额：{df['turnover'].iloc[-1]:.0f}")
except Exception as e:
    print(f"✗ 失败：{e}")

# 测试 4: 获取指数成分股
print("\n4. 测试获取沪深 300 成分股...")
try:
    hs300 = rq.index_components('000300.XSHG')
    print(f"✓ 沪深 300 成分股：{len(hs300)} 只")
    print(f"  前 5 大权重:")
    print(hs300.nlargest(5, 'weight')[['order_book_id', 'symbol_name', 'weight']])
except Exception as e:
    print(f"✗ 失败：{e}")

# 测试 5: 获取财务数据
print("\n5. 测试获取财务数据...")
try:
    from rqdatac import valuation, query
    fundamentals = rq.get_fundamentals(
        query(valuation.code, valuation.pe_ratio, valuation.pb_ratio, valuation.market_cap),
        date='2024-12-31'
    )
    print(f"✓ 财务数据获取成功")
    print(f"  数据量：{len(fundamentals)} 条")
    print(f"  字段：{fundamentals.columns.tolist()}")
except Exception as e:
    print(f"✗ 失败：{e}")

# 测试 6: 获取分红数据
print("\n6. 测试获取分红数据（贵州茅台）...")
try:
    dividends = rq.get_dividends('600519.XSHG')
    print(f"✓ 分红数据获取成功")
    print(f"  分红次数：{len(dividends)}")
    if len(dividends) > 0:
        print(f"  最近 3 次分红:")
        for div in dividends[:3]:
            print(f"    {div['announcement_date']}: {div['cash_dividend']:.2f}元/10 股")
except Exception as e:
    print(f"✗ 失败：{e}")

print("\n" + "=" * 70)
print("✅ 测试完成！")
print("=" * 70)

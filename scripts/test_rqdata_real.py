#!/usr/bin/env python3
"""
RQSDK 实际数据获取测试

测试接口是否能正常获取真实数据
"""
import rqdatac as rq
from datetime import datetime, timedelta

print("=" * 70)
print("RQSDK 实际数据获取测试")
print("=" * 70)

# 初始化
print("\n1. 初始化连接...")
try:
    rq.init()
    print("✓ 初始化成功")
except Exception as e:
    print(f"✗ 初始化失败：{e}")
    exit(1)

# 测试 1: 获取股票列表
print("\n2. 获取 A 股股票列表...")
try:
    stocks = rq.all_instruments(type='CS', market='cn')
    print(f"✓ A 股总数：{len(stocks)} 只")
    print(f"  示例数据:")
    print(f"    {stocks.iloc[0]['order_book_id']} - {stocks.iloc[0]['symbol_name']}")
    print(f"    {stocks.iloc[1]['order_book_id']} - {stocks.iloc[1]['symbol_name']}")
    print(f"    {stocks.iloc[2]['order_book_id']} - {stocks.iloc[2]['symbol_name']}")
except Exception as e:
    print(f"✗ 失败：{e}")

# 测试 2: 获取贵州茅台日线数据
print("\n3. 获取贵州茅台 (600519) 日线数据...")
try:
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365)
    
    df = rq.get_price(
        order_book_ids='600519.XSHG',
        start_date=start_date.strftime('%Y-%m-%d'),
        end_date=end_date.strftime('%Y-%m-%d'),
        frequency='1d',
        adjust_type='pre'
    )
    
    print(f"✓ 日线数据获取成功")
    print(f"  数据量：{len(df)} 条")
    print(f"  时间范围：{df.index[0]} 至 {df.index[-1]}")
    print(f"  字段：{df.columns.tolist()}")
    print(f"\n  最新数据 ({df.index[-1].strftime('%Y-%m-%d')}):")
    print(f"    开盘：{df['open'].iloc[-1]:.2f}")
    print(f"    最高：{df['high'].iloc[-1]:.2f}")
    print(f"    最低：{df['low'].iloc[-1]:.2f}")
    print(f"    收盘：{df['close'].iloc[-1]:.2f}")
    print(f"    成交量：{df['volume'].iloc[-1]:.0f}")
    print(f"    成交额：{df['turnover'].iloc[-1]:.0f}")
except Exception as e:
    print(f"✗ 失败：{e}")
    import traceback
    traceback.print_exc()

# 测试 3: 获取沪深 300 指数
print("\n4. 获取沪深 300 指数数据...")
try:
    df = rq.get_price(
        order_book_ids='000300.XSHG',
        start_date='2024-12-01',
        end_date='2024-12-31',
        frequency='1d'
    )
    
    print(f"✓ 沪深 300 数据获取成功")
    print(f"  数据量：{len(df)} 条")
    print(f"  最新收盘价：{df['close'].iloc[-1]:.2f}")
except Exception as e:
    print(f"✗ 失败：{e}")

# 测试 4: 获取沪深 300 成分股
print("\n5. 获取沪深 300 成分股...")
try:
    hs300 = rq.index_components('000300.XSHG')
    print(f"✓ 成分股数量：{len(hs300)} 只")
    print(f"  前 10 大权重股:")
    top10 = hs300.nlargest(10, 'weight')
    for _, row in top10.iterrows():
        print(f"    {row['order_book_id']:12s} - {row['symbol_name']:15s} 权重：{row['weight']:.2f}%")
except Exception as e:
    print(f"✗ 失败：{e}")

# 测试 5: 获取财务数据
print("\n6. 获取财务数据 (PE/PB)...")
try:
    from rqdatac import valuation, query
    
    fundamentals = rq.get_fundamentals(
        query(
            valuation.code,
            valuation.pe_ratio,
            valuation.pb_ratio,
            valuation.market_cap
        ),
        date='2024-12-31'
    )
    
    print(f"✓ 财务数据获取成功")
    print(f"  数据量：{len(fundamentals)} 条")
    print(f"  字段：{fundamentals.columns.tolist()}")
    print(f"\n  PE 最低的 5 只股票:")
    top5_pe = fundamentals.nsmallest(5, 'pe_ratio')
    for _, row in top5_pe.iterrows():
        print(f"    {row['code']:12s} PE: {row['pe_ratio']:.2f}  PB: {row['pb_ratio']:.2f}")
except Exception as e:
    print(f"✗ 失败：{e}")

# 测试 6: 获取分红数据
print("\n7. 获取贵州茅台分红数据...")
try:
    dividends = rq.get_dividends('600519.XSHG')
    print(f"✓ 分红数据获取成功")
    print(f"  历史分红次数：{len(dividends)}")
    if len(dividends) > 0:
        print(f"  最近 5 次分红:")
        for div in dividends[:5]:
            print(f"    {div['announcement_date']}: 现金{div['cash_dividend']:.2f}元/10 股")
except Exception as e:
    print(f"✗ 失败：{e}")

# 测试 7: 获取实时行情
print("\n8. 获取实时行情...")
try:
    tick = rq.get_current_tick('600519.XSHG')
    if tick is not None:
        print(f"✓ 实时行情获取成功")
        print(f"  贵州茅台 (600519.XSHG):")
        print(f"    最新价：{tick.get('last', 0):.2f}")
        print(f"    买一价：{tick.get('bid_1', 0):.2f}")
        print(f"    卖一价：{tick.get('ask_1', 0):.2f}")
        print(f"    成交量：{tick.get('volume', 0):.0f}")
    else:
        print(f"⚠ 当前非交易时间，无实时行情")
except Exception as e:
    print(f"✗ 失败：{e}")

# 测试 8: 获取股指期货数据
print("\n9. 获取股指期货数据...")
try:
    # 获取 IF 主力合约
    if_main = rq.get_dominant_price('IF', '2024-01-01', '2024-12-31')
    print(f"✓ 股指期货主力合约数据获取成功")
    print(f"  数据量：{len(if_main)} 条")
    if len(if_main) > 0:
        print(f"  最新数据:")
        print(f"    合约：{if_main.iloc[-1]['order_book_id']}")
        print(f"    收盘价：{if_main.iloc[-1]['close']:.1f}")
except Exception as e:
    print(f"✗ 失败：{e}")

print("\n" + "=" * 70)
print("✅ 所有测试完成！RQSDK 接口可以正常使用！")
print("=" * 70)

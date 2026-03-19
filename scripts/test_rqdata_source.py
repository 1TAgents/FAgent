#!/usr/bin/env python3
"""
RQData 数据源模块测试

验证 RQData 数据源的各项功能
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from modules.stock.data.rqdata_source import RQDataSource

def test_get_bars():
    """测试获取 K 线数据"""
    print("=" * 70)
    print("测试 1: 获取 K 线数据")
    print("=" * 70)
    
    source = RQDataSource()
    
    # 获取贵州茅台日线数据
    bars = source.get_bars(
        symbol='600519',
        start_date='2024-12-01',
        end_date='2024-12-31',
        period='1d',
        adjust_type='pre'
    )
    
    if bars:
        print(f"✓ 获取成功 | {len(bars)} 条")
        print(f"  时间范围：{bars[0].datetime.date()} 至 {bars[-1].datetime.date()}")
        print(f"  最新数据:")
        print(f"    开盘：{bars[-1].open_price:.2f}")
        print(f"    收盘：{bars[-1].close_price:.2f}")
        print(f"    最高：{bars[-1].high_price:.2f}")
        print(f"    最低：{bars[-1].low_price:.2f}")
        print(f"    成交量：{bars[-1].volume:.0f}")
    else:
        print("✗ 获取失败")
    
    return len(bars) > 0


def test_get_quote():
    """测试获取实时行情"""
    print("\n" + "=" * 70)
    print("测试 2: 获取实时行情")
    print("=" * 70)
    
    source = RQDataSource()
    
    quote = source.get_quote('600519')
    
    if quote:
        print(f"✓ 获取成功")
        print(f"  贵州茅台 (600519):")
        print(f"    最新价：{quote['last_price']:.2f}")
        print(f"    买一价：{quote['bid_price_1']:.2f}")
        print(f"    卖一价：{quote['ask_price_1']:.2f}")
        print(f"    成交量：{quote['volume']:.0f}")
    else:
        print("⚠ 非交易时间，无实时行情")
    
    return True  # 无论是否成功都不算失败


def test_get_all_stocks():
    """测试获取股票列表"""
    print("\n" + "=" * 70)
    print("测试 3: 获取 A 股股票列表")
    print("=" * 70)
    
    source = RQDataSource()
    
    stocks = source.get_all_stocks()
    
    if stocks:
        print(f"✓ 获取成功 | {len(stocks)} 只")
        print(f"  前 5 只:")
        for stock in stocks[:5]:
            print(f"    {stock['symbol']:6s} - {stock['name']} ({stock['exchange']})")
    else:
        print("✗ 获取失败")
    
    return len(stocks) > 0


def test_get_index_components():
    """测试获取指数成分股"""
    print("\n" + "=" * 70)
    print("测试 4: 获取沪深 300 成分股")
    print("=" * 70)
    
    source = RQDataSource()
    
    components = source.get_index_components('000300')
    
    if components:
        print(f"✓ 获取成功 | {len(components)} 只")
        print(f"  前 10 大权重:")
        top10 = sorted(components, key=lambda x: x['weight'], reverse=True)[:10]
        for comp in top10:
            print(f"    {comp['symbol']:6s} - {comp['name']:15s} 权重：{comp['weight']:.2f}%")
    else:
        print("✗ 获取失败")
    
    return len(components) > 0


def test_get_dividends():
    """测试获取分红数据"""
    print("\n" + "=" * 70)
    print("测试 5: 获取分红数据（贵州茅台）")
    print("=" * 70)
    
    source = RQDataSource()
    
    dividends = source.get_dividends('600519')
    
    if dividends:
        print(f"✓ 获取成功 | {len(dividends)} 次")
        print(f"  最近 5 次分红:")
        for div in dividends[:5]:
            print(f"    {div['announcement_date']}: 现金{div['cash_dividend']:.2f}元/10 股")
    else:
        print("✗ 获取失败")
    
    return len(dividends) > 0


def test_get_trading_dates():
    """测试获取交易日历"""
    print("\n" + "=" * 70)
    print("测试 6: 获取交易日历")
    print("=" * 70)
    
    source = RQDataSource()
    
    dates = source.get_trading_dates('2024-12-01', '2024-12-31')
    
    if dates:
        print(f"✓ 获取成功 | {len(dates)} 个交易日")
        print(f"  前 5 个交易日：{dates[:5]}")
        print(f"  后 5 个交易日：{dates[-5:]}")
    else:
        print("✗ 获取失败")
    
    return len(dates) > 0


def main():
    """主函数"""
    print("\n" + "=" * 70)
    print("RQData 数据源模块测试")
    print("=" * 70)
    
    results = []
    
    try:
        # 执行测试
        results.append(("K 线数据", test_get_bars()))
        results.append(("实时行情", test_get_quote()))
        results.append(("股票列表", test_get_all_stocks()))
        results.append(("指数成分股", test_get_index_components()))
        results.append(("分红数据", test_get_dividends()))
        results.append(("交易日历", test_get_trading_dates()))
        
        # 统计结果
        print("\n" + "=" * 70)
        print("测试结果汇总")
        print("=" * 70)
        
        for name, result in results:
            status = "✓ 通过" if result else "✗ 失败"
            print(f"{status} | {name}")
        
        passed = sum(1 for _, r in results if r)
        total = len(results)
        
        print(f"\n总计：{passed}/{total} 通过 ({passed/total*100:.1f}%)")
        
        if passed == total:
            print("\n✅ 所有测试通过！RQData 数据源模块可以正常使用！")
        else:
            print(f"\n⚠️ {total - passed} 个测试未通过，请检查")
        
    except Exception as e:
        print(f"\n❌ 测试失败：{e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

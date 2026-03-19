#!/usr/bin/env python3
"""
统一查询接口测试

测试功能：
1. 问行情（股票/期货）
2. 问策略
3. 问回测
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from modules.services.unified_query_interface import UnifiedQueryInterface

def test_stock_market_query():
    """测试股票行情查询"""
    print("=" * 80)
    print("测试 1: 股票行情查询")
    print("=" * 80)
    
    interface = UnifiedQueryInterface()
    
    # 测试查询茅台行情
    result = interface.query("贵州茅台行情")
    
    print(f"\n用户：贵州茅台行情")
    print(f"\n回复:\n{result['reply']}")
    print(f"\n建议：{result.get('suggestions', [])}")
    
    return result['reply'] is not None


def test_future_market_query():
    """测试期货行情查询"""
    print("\n" + "=" * 80)
    print("测试 2: 期货行情查询")
    print("=" * 80)
    
    interface = UnifiedQueryInterface()
    
    # 测试查询螺纹钢
    result = interface.query("螺纹钢 5 分钟数据")
    
    print(f"\n用户：螺纹钢 5 分钟数据")
    print(f"\n回复:\n{result['reply']}")
    print(f"\n建议：{result.get('suggestions', [])}")
    
    return result['reply'] is not None


def test_strategy_query():
    """测试策略查询"""
    print("\n" + "=" * 80)
    print("测试 3: 策略查询")
    print("=" * 80)
    
    interface = UnifiedQueryInterface()
    
    # 测试查询策略
    result = interface.query("有什么策略")
    
    print(f"\n用户：有什么策略")
    print(f"\n回复:\n{result['reply']}")
    print(f"\n建议：{result.get('suggestions', [])}")
    
    return result['reply'] is not None


def test_backtest_query():
    """测试回测查询"""
    print("\n" + "=" * 80)
    print("测试 4: 回测查询")
    print("=" * 80)
    
    interface = UnifiedQueryInterface()
    
    # 测试回测
    result = interface.query("回测双均线策略 600519")
    
    print(f"\n用户：回测双均线策略 600519")
    print(f"\n回复:\n{result['reply']}")
    print(f"\n建议：{result.get('suggestions', [])}")
    
    return result['reply'] is not None


def test_local_cache():
    """测试本地缓存"""
    print("\n" + "=" * 80)
    print("测试 5: 本地缓存测试")
    print("=" * 80)
    
    from modules.data.unified_data_service import get_data_service
    
    service = get_data_service()
    
    # 第一次查询（可能从远程加载）
    print("\n第一次查询（加载数据）...")
    bars1 = service.get_stock_bars('600519', '2026-03-01', '2026-03-19', '1d')
    print(f"获取到 {len(bars1)} 条数据")
    
    # 第二次查询（应该从本地缓存）
    print("\n第二次查询（本地缓存）...")
    bars2 = service.get_stock_bars('600519', '2026-03-01', '2026-03-19', '1d')
    print(f"获取到 {len(bars2)} 条数据")
    
    return len(bars1) > 0 and len(bars2) > 0


def main():
    """主函数"""
    print("\n" + "=" * 80)
    print("统一查询接口测试")
    print("=" * 80)
    
    results = []
    
    try:
        # 执行测试
        results.append(("股票行情", test_stock_market_query()))
        results.append(("期货行情", test_future_market_query()))
        results.append(("策略查询", test_strategy_query()))
        results.append(("回测查询", test_backtest_query()))
        results.append(("本地缓存", test_local_cache()))
        
        # 统计结果
        print("\n" + "=" * 80)
        print("测试结果汇总")
        print("=" * 80)
        
        for name, result in results:
            status = "✓ 通过" if result else "✗ 失败"
            print(f"{status} | {name}")
        
        passed = sum(1 for _, r in results if r)
        total = len(results)
        
        print(f"\n总计：{passed}/{total} 通过 ({passed/total*100:.1f}%)")
        
        if passed == total:
            print("\n✅ 所有测试通过！统一查询接口可以正常使用！")
        else:
            print(f"\n⚠️ {total - passed} 个测试未通过，请检查")
        
    except Exception as e:
        print(f"\n❌ 测试失败：{e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

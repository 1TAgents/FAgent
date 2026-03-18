#!/usr/bin/env python3
"""
策略层测试
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

def test_stock_strategies():
    """测试股票策略"""
    print("=" * 60)
    print("测试股票策略")
    print("=" * 60)
    
    from modules.stock.strategies import list_strategies, get_strategy
    
    # 测试策略列表
    print("\n1. 股票策略列表:")
    strategies = list_strategies()
    for s in strategies:
        print(f"   - {s['id']}: {s['name']}")
        print(f"     描述：{s['description']}")
        print(f"     参数：{s['params']}")
    
    # 测试获取策略
    print("\n2. 获取策略类:")
    try:
        strategy_class = get_strategy('dual_ma')
        print(f"   ✓ dual_ma: {strategy_class.__name__}")
    except Exception as e:
        print(f"   ✗ dual_ma 失败：{e}")
    
    try:
        strategy_class = get_strategy('rsi')
        print(f"   ✓ rsi: {strategy_class.__name__}")
    except Exception as e:
        print(f"   ✗ rsi 失败：{e}")


def test_future_strategies():
    """测试期货策略"""
    print("\n" + "=" * 60)
    print("测试期货策略")
    print("=" * 60)
    
    from modules.future.strategies import list_strategies, get_strategy
    
    # 测试策略列表
    print("\n1. 期货策略列表:")
    strategies = list_strategies()
    for s in strategies:
        print(f"   - {s['id']}: {s['name']}")
        print(f"     描述：{s['description']}")
        print(f"     参数：{s['params']}")
    
    # 测试获取策略
    print("\n2. 获取策略类:")
    try:
        strategy_class = get_strategy('future_dual_ma')
        print(f"   ✓ future_dual_ma: {strategy_class.__name__}")
    except Exception as e:
        print(f"   ✗ future_dual_ma 失败：{e}")
    
    try:
        strategy_class = get_strategy('future_rsi')
        print(f"   ✓ future_rsi: {strategy_class.__name__}")
    except Exception as e:
        print(f"   ✗ future_rsi 失败：{e}")


def test_module_integration():
    """测试模块集成"""
    print("\n" + "=" * 60)
    print("测试模块集成")
    print("=" * 60)
    
    from modules.stock.api import StockModule
    from modules.future.api import FutureModule
    
    # 测试股票模块策略列表
    print("\n1. 股票模块策略列表:")
    stock_module = StockModule()
    strategies = stock_module.list_strategies()
    for s in strategies:
        print(f"   - {s['id']}: {s['name']}")
    
    # 测试期货模块策略列表
    print("\n2. 期货模块策略列表:")
    future_module = FutureModule()
    strategies = future_module.list_strategies()
    for s in strategies:
        print(f"   - {s['id']}: {s['name']}")


def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("FAgent 策略层测试")
    print("=" * 60)
    
    try:
        test_stock_strategies()
        test_future_strategies()
        test_module_integration()
        
        print("\n" + "=" * 60)
        print("✅ 所有测试完成！")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ 测试失败：{e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

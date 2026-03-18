#!/usr/bin/env python3
"""
回测层测试
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

def test_stock_backtest():
    """测试股票回测"""
    print("=" * 60)
    print("测试股票回测")
    print("=" * 60)
    
    from modules.stock.api import StockModule
    
    module = StockModule()
    
    print("\n1. 执行双均线策略回测:")
    result = module.run_backtest(
        strategy_id='dual_ma',
        symbol='600519',
        start_date='2023-01-01',
        end_date='2023-12-31',
        initial_capital=100000.0
    )
    
    print(f"   成功：{result['success']}")
    if result['success']:
        print(f"   总收益：{result['report']['total_return']:.2%}")
        print(f"   年化收益：{result['report']['annual_return']:.2%}")
        print(f"   夏普比率：{result['report']['sharpe_ratio']:.2f}")
        print(f"   最大回撤：{result['report']['max_drawdown']:.2%}")
        print(f"   交易次数：{result['report']['total_trades']}")
        print(f"   胜率：{result['report']['win_rate']:.2%}")


def test_future_backtest():
    """测试期货回测"""
    print("\n" + "=" * 60)
    print("测试期货回测")
    print("=" * 60)
    
    from modules.future.api import FutureModule
    
    module = FutureModule()
    
    print("\n1. 执行期货双均线策略回测:")
    result = module.run_backtest(
        strategy_id='future_dual_ma',
        symbol='IF2403',
        start_date='2023-01-01',
        end_date='2023-12-31',
        initial_capital=100000.0
    )
    
    print(f"   成功：{result['success']}")
    if result['success']:
        print(f"   总收益：{result['report']['total_return']:.2%}")
        print(f"   年化收益：{result['report']['annual_return']:.2%}")
        print(f"   夏普比率：{result['report']['sharpe_ratio']:.2f}")
        print(f"   最大回撤：{result['report']['max_drawdown']:.2%}")
        print(f"   交易次数：{result['report']['total_trades']}")
        print(f"   胜率：{result['report']['win_rate']:.2%}")
        print(f"   做多次数：{result['report']['long_trades']}")
        print(f"   做空次数：{result['report']['short_trades']}")


def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("FAgent 回测层测试")
    print("=" * 60)
    
    try:
        test_stock_backtest()
        test_future_backtest()
        
        print("\n" + "=" * 60)
        print("✅ 所有测试完成！")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ 测试失败：{e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
简单策略回测示例 - 双均线策略

演示如何使用完整的回测指标体系
"""
import sys
from pathlib import Path

# 动态添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from agents.backtest.data_loader import get_data_loader
from agents.backtest.vectorized_strategies import get_vectorized_strategy
from agents.backtest.performance_metrics import MetricsCalculator
from agents.backtest.report_generator import generate_html_report


def run_backtest_example(
    symbol: str = "600519",
    strategy_name: str = "dual_ma",
    start_date: str = "2025-03-17",
    end_date: str = "2026-03-17",
    initial_capital: float = 100000
):
    """
    运行回测示例
    
    Args:
        symbol: 股票代码
        strategy_name: 策略名称
        start_date: 开始日期
        end_date: 结束日期
        initial_capital: 初始资金
    """
    print("=" * 70)
    print("🚀 FAgent 简单策略回测示例")
    print("=" * 70)
    print(f"策略：{strategy_name}")
    print(f"标的：{symbol}")
    print(f"区间：{start_date} ~ {end_date}")
    print(f"资金：¥{initial_capital:,.0f}")
    print("=" * 70)
    
    # 1. 加载数据
    print("\n📊 步骤 1: 加载数据...")
    data_loader = get_data_loader()
    data = data_loader.load_klines(symbol, start_date, end_date)
    
    if data.empty:
        print("   ❌ 无数据，请检查股票代码或日期范围")
        return None
    
    print(f"   ✅ 成功加载 {len(data)} 条数据")
    print(f"   📈 价格区间：¥{data['close'].min():.2f} ~ ¥{data['close'].max():.2f}")
    
    # 2. 选择策略
    print(f"\n📈 步骤 2: 选择策略 - {strategy_name}...")
    strategy = get_vectorized_strategy(strategy_name)
    print(f"   ✅ 策略已加载")
    
    # 3. 生成信号
    print("\n📊 步骤 3: 生成交易信号...")
    signals = strategy.generate_signals(data)
    signal_count = (signals['signal'] != 0).sum()
    print(f"   ✅ 生成 {signal_count} 个交易信号")
    
    # 4. 执行回测
    print("\n💰 步骤 4: 执行回测...")
    result = strategy.backtest(signals, initial_capital)
    print(f"   ✅ 回测完成")
    
    # 5. 计算完整指标
    print("\n📊 步骤 5: 计算性能指标...")
    calculator = MetricsCalculator(risk_free_rate=0.03)
    
    # 生成交易记录
    trades = []
    for i in range(1, len(signals)):
        if signals.iloc[i]['signal'] != 0:
            trade = {
                'symbol': symbol,
                'pnl': result['equity_curve'][i] - result['equity_curve'][i-1],
                'pnl_percent': (result['equity_curve'][i] / result['equity_curve'][i-1] - 1),
                'entry_time': str(signals.index[max(0, i-1)].date()),
                'exit_time': str(signals.index[i].date())
            }
            trades.append(trade)
    
    metrics = calculator.calculate_all_metrics(
        equity_curve=result['equity_curve'],
        daily_returns=[result['equity_curve'][i] / result['equity_curve'][i-1] - 1 
                      for i in range(1, len(result['equity_curve']))],
        trades=trades
    )
    
    print(f"   ✅ 计算完成")
    
    # 6. 展示结果
    print("\n" + "=" * 70)
    print("📊 回测结果")
    print("=" * 70)
    
    print(f"\n🎯 核心指标摘要:")
    print(f"  {metrics.summary()}")
    
    print(f"\n📈 详细指标:")
    for category, indicators in metrics.to_dict().items():
        print(f"\n  {category}:")
        for name, value in indicators.items():
            print(f"    {name}: {value}")
    
    # 7. 生成报告
    print(f"\n📄 步骤 6: 生成可视化报告...")
    report_data = {
        'strategy_name': f'{strategy_name} Strategy',
        'symbol': symbol,
        'start_date': start_date,
        'end_date': end_date,
        'trading_days': len(data),
        'metrics': {
            'total_return': metrics.total_return,
            'annual_return': metrics.annual_return,
            'sharpe_ratio': metrics.sharpe_ratio,
            'max_drawdown': metrics.max_drawdown,
            'win_rate': metrics.win_rate,
            'total_trades': metrics.total_trades,
        },
        'equity_curve': dict(zip(
            [str(d.date()) for d in signals.index],
            result['equity_curve']
        )),
        'monthly_returns': {},
        'trades': trades[:20]  # 只显示前 20 笔
    }
    
    report_path = generate_html_report(report_data, f"backtest_{symbol}_{strategy_name}.html")
    print(f"   ✅ 报告已生成：{report_path}")
    
    print("\n" + "=" * 70)
    print("✅ 回测完成！")
    print("=" * 70)
    
    return metrics


if __name__ == "__main__":
    # 运行示例
    metrics = run_backtest_example(
        symbol="600519",           # 贵州茅台
        strategy_name="dual_ma",   # 双均线策略
        start_date="2025-03-17",
        end_date="2026-03-17",
        initial_capital=100000
    )
    
    if metrics:
        print(f"\n💡 提示：打开 backtest_600519_dual_ma.html 查看可视化报告")

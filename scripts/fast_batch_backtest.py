#!/usr/bin/env python3
"""
快速批量回测 - 优化版

使用并行处理加速回测
"""
import sys
from pathlib import Path

# 动态添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import pandas as pd
import numpy as np
from concurrent.futures import ProcessPoolExecutor, as_completed
from agents.backtest.data_loader import get_data_loader
from agents.backtest.vectorized_strategies import get_vectorized_strategy
from agents.backtest.trading_cost import TradingCostCalculator

# 已下载的股票
SYNCED_STOCKS = [
    '600519', '002252', '002600', '300589', '600026',
    '600354', '601607', '601878', '688081', '688500'
]

# 策略配置（简化版）
STRATEGIES = [
    ('MACD', 'macd', {'fast': 12, 'slow': 26, 'signal': 9}),
    ('双均线 5-20', 'dual_ma', {'short_period': 5, 'long_period': 20}),
    ('双均线 10-50', 'dual_ma', {'short_period': 10, 'long_period': 50}),
    ('KDJ', 'kdj', {'n': 9, 'm1': 3, 'm2': 3}),
    ('RSI', 'rsi', {'period': 14, 'oversold': 30, 'overbought': 70}),
    ('布林带', 'bollinger', {'period': 20, 'std_dev': 2}),
    ('动量', 'momentum', {'lookback': 20, 'threshold': 0.05}),
]

cost_calc = TradingCostCalculator()


def backtest_worker(args):
    """回测工作函数"""
    symbol, strategy_name, params = args
    
    try:
        data_loader = get_data_loader()
        data = data_loader.load_klines(symbol, "2025-03-17", "2026-03-17")
        
        if data.empty or len(data) < 50:
            return None
        
        strategy = get_vectorized_strategy(strategy_name, **params)
        signals = strategy.generate_signals(data)
        result = strategy.backtest(signals, 100000)
        
        # 估算手续费影响（约 0.2% 每笔往返）
        cost_per_trade = 0.002
        total_cost = result['trades'] * cost_per_trade
        adjusted_return = result['total_returns'] - total_cost
        
        return {
            'symbol': symbol,
            'strategy': strategy_name,
            'total_return': result['total_returns'] * 100,
            'adjusted_return': adjusted_return * 100,
            'sharpe_ratio': result['sharpe_ratio'],
            'max_drawdown': result['max_drawdown'] * 100,
            'trades': result['trades'],
            'final_capital': result['equity_curve'][-1],
        }
    except Exception as e:
        return None


def run_fast_batch():
    """快速批量回测"""
    print("=" * 80)
    print("🚀 快速批量回测")
    print("=" * 80)
    
    # 生成任务列表
    tasks = [(stock, name, params) for stock in SYNCED_STOCKS for name, _, params in STRATEGIES]
    
    print(f"股票数：{len(SYNCED_STOCKS)}")
    print(f"策略数：{len(STRATEGIES)}")
    print(f"总任务数：{len(tasks)}")
    print("\n开始回测...\n")
    
    results = []
    
    # 并行执行
    with ProcessPoolExecutor(max_workers=4) as executor:
        futures = [executor.submit(backtest_worker, task) for task in tasks]
        
        for i, future in enumerate(as_completed(futures), 1):
            result = future.result()
            if result:
                results.append(result)
                if result['adjusted_return'] > 20:
                    print(f"✅ [{i}/{len(tasks)}] {result['symbol']} {result['strategy']}: "
                          f"{result['adjusted_return']:.1f}% (夏普:{result['sharpe_ratio']:.2f})")
            else:
                print(f"⏳ [{i}/{len(tasks)}] 完成")
    
    # 分析结果
    print("\n" + "=" * 80)
    print("📊 结果分析")
    print("=" * 80)
    
    df = pd.DataFrame(results)
    
    # 筛选 20%+
    excellent = df[df['adjusted_return'] > 20].sort_values('adjusted_return', ascending=False)
    
    print(f"\n总回测数：{len(df)}")
    print(f"年化 20%+：{len(excellent)} ({len(excellent)/len(df)*100:.1f}%)")
    
    if len(excellent) > 0:
        print(f"\n🏆 Top 10 优秀策略:")
        print("-" * 80)
        for i, (_, row) in enumerate(excellent.head(10).iterrows(), 1):
            print(f"{i:2d}. {row['symbol']:6s} {row['strategy']:12s} "
                  f"收益:{row['adjusted_return']:6.1f}% "
                  f"夏普:{row['sharpe_ratio']:5.2f} "
                  f"回撤:{row['max_drawdown']:6.1f}% "
                  f"交易:{int(row['trades']):3d}次 "
                  f"最终:¥{row['final_capital']:9.0f}")
    
    # 保存
    df.to_csv('backtest_all.csv', index=False)
    excellent.to_csv('backtest_excellent.csv', index=False)
    
    print(f"\n💾 已保存：backtest_all.csv, backtest_excellent.csv")
    print("=" * 80)
    
    return excellent


if __name__ == "__main__":
    excellent = run_fast_batch()
    print(f"\n✅ 找到 {len(excellent)} 个年化 20%+ 的策略！")

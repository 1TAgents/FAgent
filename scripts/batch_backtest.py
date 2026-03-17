#!/usr/bin/env python3
"""
批量策略回测 - 寻找年化 20%+ 的优秀策略

使用已下载的 16 只股票数据（1 年），初始资金 10W
测试 10+ 种策略，筛选优秀策略
"""
import sys
from pathlib import Path

# 动态添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import pandas as pd
import numpy as np
from datetime import datetime
from typing import List, Dict, Tuple
from agents.backtest.data_loader import get_data_loader
from agents.backtest.vectorized_strategies import get_vectorized_strategy
from agents.backtest.performance_metrics import MetricsCalculator
from agents.backtest.trading_cost import TradingCostCalculator

# 已下载的股票列表
SYNCED_STOCKS = [
    '600519',  # 贵州茅台
    '002252',  # 上海莱士
    '002600',  # 领益智造
    '300589',  # 江龙船艇
    '600026',  # 中远海能
    '600354',  # 敦煌种业
    '601607',  # 上海医药
    '601878',  # 浙商证券
    '688081',  # 和辉光电
    '688500',  # 萤石网络
]

# 手续费计算器
cost_calc = TradingCostCalculator()

# 策略配置
STRATEGY_CONFIGS = [
    # 趋势类策略
    {'name': 'MACD_优', 'type': 'macd', 'params': {'fast': 12, 'slow': 26, 'signal': 9}},
    {'name': '双均线_短', 'type': 'dual_ma', 'params': {'short_period': 5, 'long_period': 20}},
    {'name': '双均线_中', 'type': 'dual_ma', 'params': {'short_period': 10, 'long_period': 50}},
    {'name': '动量_强', 'type': 'momentum', 'params': {'lookback': 20, 'threshold': 0.05}},
    
    # 震荡类策略
    {'name': 'KDJ_优', 'type': 'kdj', 'params': {'n': 9, 'm1': 3, 'm2': 3}},
    {'name': 'RSI_优', 'type': 'rsi', 'params': {'period': 14, 'oversold': 30, 'overbought': 70}},
    {'name': '布林带_优', 'type': 'bollinger', 'params': {'period': 20, 'std_dev': 2}},
    
    # 组合策略
    {'name': 'MACD+KDJ', 'type': 'combo_macd_kdj', 'params': {}},
    {'name': '均线 +RSI', 'type': 'combo_ma_rsi', 'params': {}},
    {'name': '多因子', 'type': 'multi_factor', 'params': {}},
]


def backtest_single_stock(
    symbol: str,
    strategy_name: str,
    strategy_params: dict,
    start_date: str = "2025-03-17",
    end_date: str = "2026-03-17",
    initial_capital: float = 100000
) -> Dict:
    """
    单只股票回测
    
    Returns:
        回测结果字典
    """
    try:
        # 加载数据
        data_loader = get_data_loader()
        data = data_loader.load_klines(symbol, start_date, end_date)
        
        if data.empty or len(data) < 50:
            return None
        
        # 获取策略
        if strategy_name.startswith('combo_') or strategy_name.startswith('multi'):
            # 组合策略需要特殊处理
            signals = generate_combo_signals(data, strategy_name, strategy_params)
            result = simple_backtest(data, signals, initial_capital, symbol)
        else:
            strategy = get_vectorized_strategy(strategy_name, **strategy_params)
            signals = strategy.generate_signals(data)
            result = strategy.backtest(signals, initial_capital)
        
        # 计算手续费影响
        total_trades = result.get('trades', 0)
        avg_trade_value = initial_capital / total_trades if total_trades > 0 else 0
        round_trip_cost = cost_calc.calculate_round_trip_cost(
            data['close'].mean(), 
            int(avg_trade_value / data['close'].mean() / 100) * 100,
            int(avg_trade_value / data['close'].mean() / 100) * 100
        )
        cost_impact = total_trades * round_trip_cost
        
        # 调整后的收益
        adjusted_return = result['total_returns'] - (cost_impact / initial_capital)
        
        return {
            'symbol': symbol,
            'strategy': strategy_name,
            'params': strategy_params,
            'total_return': result['total_returns'],
            'adjusted_return': adjusted_return,  # 扣除手续费后
            'sharpe_ratio': result['sharpe_ratio'],
            'max_drawdown': result['max_drawdown'],
            'trades': result['trades'],
            'final_capital': result['equity_curve'][-1] if result['equity_curve'] else 0,
        }
        
    except Exception as e:
        print(f"   ❌ {symbol} {strategy_name} 失败：{e}")
        return None


def generate_combo_signals(data: pd.DataFrame, strategy_name: str, params: dict) -> pd.DataFrame:
    """生成组合策略信号"""
    df = data.copy()
    
    if strategy_name == 'combo_macd_kdj':
        # MACD + KDJ 组合
        macd = get_vectorized_strategy('macd')
        kdj = get_vectorized_strategy('kdj')
        
        macd_signals = macd.generate_signals(df)
        kdj_signals = kdj.generate_signals(df)
        
        # 两个策略都发出买入信号时才买入
        df['signal'] = 0
        df.loc[(macd_signals['signal'] == 1) & (kdj_signals['signal'] == 1), 'signal'] = 1
        df.loc[(macd_signals['signal'] == -1) | (kdj_signals['signal'] == -1), 'signal'] = -1
        
    elif strategy_name == 'combo_ma_rsi':
        # 均线 + RSI 组合
        ma = get_vectorized_strategy('dual_ma', short_period=5, long_period=20)
        rsi = get_vectorized_strategy('rsi', period=14)
        
        ma_signals = ma.generate_signals(df)
        rsi_signals = rsi.generate_signals(df)
        
        df['signal'] = 0
        df.loc[(ma_signals['signal'] == 1) & (rsi_signals['signal'] == 1), 'signal'] = 1
        df.loc[(ma_signals['signal'] == -1) | (rsi_signals['signal'] == -1), 'signal'] = -1
    
    elif strategy_name == 'multi_factor':
        # 多因子策略（动量 + 波动率）
        df['momentum'] = df['close'].pct_change(periods=20)
        df['volatility'] = df['close'].pct_change().rolling(20).std()
        
        df['signal'] = 0
        # 高动量 + 低波动 → 买入
        momentum_threshold = df['momentum'].quantile(0.6)
        vol_threshold = df['volatility'].quantile(0.4)
        
        df.loc[(df['momentum'] > momentum_threshold) & (df['volatility'] < vol_threshold), 'signal'] = 1
        df.loc[(df['momentum'] < -momentum_threshold) | (df['volatility'] > vol_threshold * 2), 'signal'] = -1
    
    return df


def simple_backtest(data: pd.DataFrame, signals: pd.DataFrame, initial_capital: float, symbol: str) -> Dict:
    """简单回测（用于组合策略）"""
    capital = initial_capital
    position = 0
    equity_curve = [initial_capital]
    trades = 0
    
    for i in range(1, len(signals)):
        signal = signals.iloc[i]['signal']
        price = data.iloc[i]['close']
        
        if signal == 1 and position == 0:
            # 买入
            quantity = int(capital * 0.95 / price / 100) * 100
            if quantity > 0:
                cost = cost_calc.calculate_cost(price, quantity, 'buy')
                capital -= (price * quantity + cost)
                position = quantity
                trades += 1
        
        elif signal == -1 and position > 0:
            # 卖出
            revenue = price * position
            cost = cost_calc.calculate_cost(price, position, 'sell')
            capital += (revenue - cost)
            position = 0
            trades += 1
        
        # 计算当前权益
        current_value = capital + (position * price if position > 0 else 0)
        equity_curve.append(current_value)
    
    total_return = (equity_curve[-1] - initial_capital) / initial_capital
    
    # 计算夏普比率
    daily_returns = np.diff(equity_curve) / equity_curve[:-1]
    sharpe = np.sqrt(252) * np.mean(daily_returns) / np.std(daily_returns) if np.std(daily_returns) > 0 else 0
    
    # 计算最大回撤
    equity = np.array(equity_curve)
    peak = np.maximum.accumulate(equity)
    max_dd = ((equity - peak) / peak).min()
    
    return {
        'total_returns': total_return,
        'sharpe_ratio': sharpe,
        'max_drawdown': max_dd,
        'trades': trades,
        'equity_curve': equity_curve,
    }


def run_batch_backtest():
    """批量回测"""
    print("=" * 80)
    print("🚀 批量策略回测 - 寻找年化 20%+ 的优秀策略")
    print("=" * 80)
    print(f"股票数量：{len(SYNCED_STOCKS)} 只")
    print(f"策略数量：{len(STRATEGY_CONFIGS)} 个")
    print(f"初始资金：¥100,000")
    print(f"手续费：印花税 0.1% + 佣金万 3 + 过户费万 0.2")
    print("=" * 80)
    
    all_results = []
    
    # 遍历所有股票和策略
    for i, stock in enumerate(SYNCED_STOCKS, 1):
        print(f"\n📈 [{i}/{len(SYNCED_STOCKS)}] 测试 {stock}...")
        
        for config in STRATEGY_CONFIGS:
            result = backtest_single_stock(
                symbol=stock,
                strategy_name=config['name'],
                strategy_params=config['params']
            )
            
            if result:
                all_results.append(result)
    
    # 分析结果
    print("\n" + "=" * 80)
    print("📊 回测结果分析")
    print("=" * 80)
    
    # 转换为 DataFrame
    df_results = pd.DataFrame(all_results)
    
    # 筛选年化 20%+ 的策略
    excellent = df_results[df_results['adjusted_return'] > 0.20].copy()
    
    print(f"\n总回测组合数：{len(df_results)}")
    print(f"年化 20%+ 组合数：{len(excellent)} ({len(excellent)/len(df_results)*100:.1f}%)")
    
    if len(excellent) > 0:
        print(f"\n🏆 优秀策略 Top 10:")
        print("-" * 80)
        
        # 按调整后收益排序
        excellent = excellent.sort_values('adjusted_return', ascending=False)
        
        for i, row in excellent.head(10).iterrows():
            print(f"\n{i+1}. {row['strategy']} @ {row['symbol']}")
            print(f"   总收益：{row['total_return']:.2%} | 扣除手续费后：{row['adjusted_return']:.2%}")
            print(f"   夏普比率：{row['sharpe_ratio']:.2f} | 最大回撤：{row['max_drawdown']:.2%}")
            print(f"   交易次数：{int(row['trades'])} | 最终资金：¥{row['final_capital']:,.0f}")
    
    # 策略表现统计
    print(f"\n\n📈 各策略平均表现:")
    print("-" * 80)
    
    strategy_stats = df_results.groupby('strategy').agg({
        'adjusted_return': ['mean', 'std', 'max'],
        'sharpe_ratio': 'mean',
        'max_drawdown': 'mean',
        'trades': 'mean'
    }).round(4)
    
    print(strategy_stats.to_string())
    
    # 保存结果
    df_results.to_csv('backtest_results.csv', index=False)
    excellent.head(20).to_csv('excellent_strategies.csv', index=False)
    
    print(f"\n💾 结果已保存到：backtest_results.csv, excellent_strategies.csv")
    print("=" * 80)
    
    return excellent


if __name__ == "__main__":
    excellent_strategies = run_batch_backtest()
    
    if len(excellent_strategies) > 0:
        print(f"\n✅ 成功找到 {len(excellent_strategies)} 个年化 20%+ 的策略组合！")
    else:
        print("\n⚠️ 未找到年化 20%+ 的策略，可能需要调整参数或使用更长周期数据")

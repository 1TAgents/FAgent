#!/usr/bin/env python3
"""
多股票组合策略测试 - 寻找年化 20%+ 的组合策略

策略逻辑：
1. 选股：从股票池中筛选符合条件的股票（如动量最强、RSI 超卖等）
2. 择时：根据信号决定买卖时机
3. 仓位：最多同时持有 5 只股票，等权重配置
4. 调仓：定期（如每周/每月）重新选股并调整仓位
"""
import sys
from pathlib import Path

# 动态添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import pandas as pd
import numpy as np
import sqlite3
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass

# 数据库路径
DB_PATH = Path(__file__).parent.parent / "data" / "stock_data.db"


@dataclass
class Position:
    """持仓信息"""
    symbol: str
    shares: int
    entry_date: str
    entry_price: float


@dataclass
class PortfolioStrategy:
    """组合策略配置"""
    name: str
    max_positions: int = 5  # 最多持股数
    rebalance_days: int = 20  # 调仓周期（交易日）
    initial_capital: float = 100000.0
    
    # 选股策略
    selection_method: str = "momentum"  # momentum, rsi_oversold, breakout
    
    # 选股参数
    top_n: int = 5  # 选前 N 只
    momentum_lookback: int = 20  # 动量计算周期
    rsi_period: int = 14
    rsi_oversold: int = 30
    
    # 择时策略
    exit_method: str = "rebalance"  # rebalance, stop_loss, signal
    stop_loss: float = 0.05  # 止损比例
    take_profit: float = 0.15  # 止盈比例


def load_all_klines(symbols: List[str], start_date: str, end_date: str) -> Dict[str, pd.DataFrame]:
    """
    批量加载多只股票的 K 线数据
    
    Returns:
        dict: symbol -> DataFrame
    """
    conn = sqlite3.connect(DB_PATH)
    data_dict = {}
    
    for symbol in symbols:
        query = """
        SELECT date, open, high, low, close, volume, turnover, change_percent
        FROM klines
        WHERE symbol = ?
        ORDER BY date
        """
        df = pd.read_sql_query(query, conn, params=(symbol,))
        
        if not df.empty:
            df['date'] = pd.to_datetime(df['date'])
            df = df.set_index('date')
            data_dict[symbol] = df
    
    conn.close()
    return data_dict


def calculate_momentum(data: pd.DataFrame, lookback: int = 20) -> float:
    """计算动量（N 日收益率）"""
    if len(data) < lookback:
        return 0.0
    return (data['close'].iloc[-1] / data['close'].iloc[-lookback]) - 1


def calculate_rsi(data: pd.DataFrame, period: int = 14) -> float:
    """计算 RSI"""
    if len(data) < period + 1:
        return 50.0
    
    delta = data['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    
    rs = gain / (loss + 1e-10)
    rsi = 100 - (100 / (1 + rs))
    
    return rsi.iloc[-1]


def select_stocks(
    data_dict: Dict[str, pd.DataFrame],
    current_date: pd.Timestamp,
    strategy: PortfolioStrategy
) -> List[str]:
    """
    选股策略：根据配置的方法筛选股票
    
    Args:
        data_dict: 所有股票的数据
        current_date: 当前日期
        strategy: 策略配置
    
    Returns:
        选中的股票列表
    """
    scores = []
    
    for symbol, data in data_dict.items():
        # 确保数据包含当前日期
        available_dates = data[data.index <= current_date]
        if len(available_dates) < strategy.momentum_lookback + 10:
            continue  # 数据不足，跳过
        
        # 获取截止到当前日期的数据
        cutoff_data = available_dates[available_dates.index <= current_date].tail(strategy.momentum_lookback + 10)
        
        if strategy.selection_method == "momentum":
            # 动量选股：选择动量最强的
            score = calculate_momentum(cutoff_data, strategy.momentum_lookback)
        
        elif strategy.selection_method == "rsi_oversold":
            # RSI 超卖选股：选择 RSI 最低的（超卖）
            rsi = calculate_rsi(cutoff_data, strategy.rsi_period)
            score = -rsi  # RSI 越低越好
        
        elif strategy.selection_method == "rsi_trend":
            # RSI 趋势：选择 RSI 从超卖区回升的
            rsi = calculate_rsi(cutoff_data, strategy.rsi_period)
            momentum = calculate_momentum(cutoff_data, 10)
            score = momentum if rsi < 50 else -1000  # RSI<50 且有动量
        
        else:
            score = 0
        
        scores.append((symbol, score))
    
    # 按分数排序，选前 N 只
    scores.sort(key=lambda x: x[1], reverse=True)
    selected = [s[0] for s in scores[:strategy.top_n]]
    
    return selected


def run_portfolio_backtest(
    data_dict: Dict[str, pd.DataFrame],
    strategy: PortfolioStrategy
) -> Dict:
    """
    执行组合策略回测
    
    Returns:
        回测结果字典
    """
    # 找到所有数据的共同日期范围
    all_dates = set()
    for data in data_dict.values():
        all_dates.update(data.index)
    
    dates = sorted(list(all_dates))
    
    if len(dates) < strategy.rebalance_days + 10:
        return {"error": "数据时间范围太短"}
    
    # 初始化
    cash = strategy.initial_capital
    positions: Dict[str, Position] = {}
    equity_curve = []
    trades = []
    
    # 调仓日列表
    rebalance_dates = dates[::strategy.rebalance_days]
    
    for i, current_date in enumerate(dates):
        # 检查是否需要调仓
        should_rebalance = current_date in rebalance_dates
        
        # 1. 检查持仓止损/止盈
        positions_to_close = []
        for symbol, pos in positions.items():
            if symbol not in data_dict:
                continue
            
            # 获取当前价格
            stock_data = data_dict[symbol]
            if current_date not in stock_data.index:
                continue
            
            current_price = stock_data.loc[current_date, 'close']
            pnl_ratio = (current_price - pos.entry_price) / pos.entry_price
            
            # 止损检查
            if strategy.exit_method == "stop_loss":
                if pnl_ratio <= -strategy.stop_loss:
                    positions_to_close.append(symbol)
                elif pnl_ratio >= strategy.take_profit:
                    positions_to_close.append(symbol)
        
        # 2. 如果调仓日，卖出所有持仓（简化：调仓时全部换仓）
        if should_rebalance and strategy.exit_method == "rebalance":
            positions_to_close = list(positions.keys())
        
        # 执行卖出
        for symbol in positions_to_close:
            pos = positions.pop(symbol)
            stock_data = data_dict[symbol]
            if current_date in stock_data.index:
                sell_price = stock_data.loc[current_date, 'close']
                sale_value = pos.shares * sell_price
                cash += sale_value
                
                trades.append({
                    "date": str(current_date.date()),
                    "symbol": symbol,
                    "action": "sell",
                    "price": sell_price,
                    "shares": pos.shares,
                    "pnl": (sell_price - pos.entry_price) * pos.shares
                })
        
        # 3. 选股并买入
        if should_rebalance:
            selected_stocks = select_stocks(data_dict, current_date, strategy)
            
            # 计算每只股票的仓位（等权重）
            if selected_stocks and cash > 0:
                position_value = cash / len(selected_stocks)
                
                for symbol in selected_stocks:
                    if symbol in positions:
                        continue  # 已持有
                    
                    stock_data = data_dict[symbol]
                    if current_date not in stock_data.index:
                        continue
                    
                    buy_price = stock_data.loc[current_date, 'close']
                    shares = int(position_value / buy_price / 100) * 100  # 100 股的整数倍
                    
                    if shares > 0 and cash >= shares * buy_price:
                        cash -= shares * buy_price
                        
                        positions[symbol] = Position(
                            symbol=symbol,
                            shares=shares,
                            entry_date=str(current_date.date()),
                            entry_price=buy_price
                        )
                        
                        trades.append({
                            "date": str(current_date.date()),
                            "symbol": symbol,
                            "action": "buy",
                            "price": buy_price,
                            "shares": shares
                        })
        
        # 4. 计算当日总资产
        total_value = cash
        for symbol, pos in positions.items():
            stock_data = data_dict[symbol]
            if current_date in stock_data.index:
                current_price = stock_data.loc[current_date, 'close']
                total_value += pos.shares * current_price
        
        equity_curve.append({
            "date": str(current_date.date()),
            "equity": total_value,
            "cash": cash,
            "positions": len(positions)
        })
    
    # 计算绩效指标
    if len(equity_curve) < 2:
        return {"error": "回测数据不足"}
    
    equity_df = pd.DataFrame(equity_curve)
    equity_df['date'] = pd.to_datetime(equity_df['date'])
    equity_df = equity_df.set_index('date')
    
    # 收益率计算
    equity_df['daily_return'] = equity_df['equity'].pct_change()
    
    total_return = (equity_df['equity'].iloc[-1] / strategy.initial_capital) - 1
    
    # 年化收益（假设 250 交易日）
    days = len(equity_df)
    annual_return = (1 + total_return) ** (250 / days) - 1
    
    # 夏普比率
    if equity_df['daily_return'].std() > 0:
        sharpe_ratio = (equity_df['daily_return'].mean() / equity_df['daily_return'].std()) * np.sqrt(250)
    else:
        sharpe_ratio = 0
    
    # 最大回撤
    equity_df['peak'] = equity_df['equity'].cummax()
    equity_df['drawdown'] = (equity_df['equity'] - equity_df['peak']) / equity_df['peak']
    max_drawdown = equity_df['drawdown'].min()
    
    # 交易统计
    num_trades = len([t for t in trades if t['action'] == 'sell'])
    winning_trades = len([t for t in trades if t['action'] == 'sell' and t.get('pnl', 0) > 0])
    win_rate = winning_trades / num_trades if num_trades > 0 else 0
    
    return {
        "strategy_name": strategy.name,
        "initial_capital": strategy.initial_capital,
        "final_capital": equity_df['equity'].iloc[-1],
        "total_return": total_return,
        "annual_return": annual_return,
        "sharpe_ratio": sharpe_ratio,
        "max_drawdown": max_drawdown,
        "num_trades": num_trades,
        "win_rate": win_rate,
        "trading_days": days,
        "num_stocks": len(data_dict),
        "max_positions": strategy.max_positions,
        "rebalance_days": strategy.rebalance_days,
        "selection_method": strategy.selection_method,
        "equity_curve": equity_df['equity'].tolist(),
        "dates": equity_df.index.strftime('%Y-%m-%d').tolist(),
        "trades": trades[:50]  # 只返回前 50 笔交易
    }


def main():
    """主函数"""
    print("\n")
    print("=" * 80)
    print(" " * 25 + "多股票组合策略测试 - 寻找年化 20%+ 策略")
    print("=" * 80)
    print()
    
    # 股票池（16 只股票）
    STOCK_POOL = [
        ("600519", "贵州茅台"),
        ("002252", "上海莱士"),
        ("002600", "领益智造"),
        ("300589", "江龙船艇"),
        ("600026", "中远海能"),
        ("600354", "盟固利"),
        ("600508", "上海能源"),
        ("601607", "上海医药"),
        ("601878", "浙商证券"),
        ("688081", "兴图新科"),
        ("688500", "慧辰股份"),
        ("688591", "泰凌微"),
    ]
    
    # 策略配置（测试不同组合）
    strategies = [
        # 动量选股 + 定期调仓
        PortfolioStrategy(
            name="动量选股 (20 日，20 天调仓)",
            selection_method="momentum",
            momentum_lookback=20,
            rebalance_days=20,
            max_positions=5,
            top_n=5
        ),
        PortfolioStrategy(
            name="动量选股 (10 日，10 天调仓)",
            selection_method="momentum",
            momentum_lookback=10,
            rebalance_days=10,
            max_positions=5,
            top_n=5
        ),
        
        # RSI 超卖选股
        PortfolioStrategy(
            name="RSI 超卖选股 (20 天调仓)",
            selection_method="rsi_oversold",
            rsi_period=14,
            rsi_oversold=30,
            rebalance_days=20,
            max_positions=5,
            top_n=5
        ),
        PortfolioStrategy(
            name="RSI 趋势选股 (15 天调仓)",
            selection_method="rsi_trend",
            rsi_period=14,
            rebalance_days=15,
            max_positions=5,
            top_n=5
        ),
        
        # 更分散的组合
        PortfolioStrategy(
            name="动量选股 (10 只选 5，10 天调仓)",
            selection_method="momentum",
            momentum_lookback=20,
            rebalance_days=10,
            max_positions=5,
            top_n=10
        ),
    ]
    
    # 加载所有股票数据
    print("📥 加载股票数据...")
    symbols = [s[0] for s in STOCK_POOL]
    data_dict = load_all_klines(symbols, "2025-03-17", "2026-03-17")
    
    valid_symbols = [s for s in symbols if s in data_dict and len(data_dict[s]) > 100]
    print(f"  成功加载 {len(valid_symbols)} 只股票，每只 {len(data_dict[valid_symbols[0]])} 行数据")
    print()
    
    # 测试每个策略
    results = []
    
    print("🚀 开始回测...")
    print("-" * 80)
    
    for strategy in strategies:
        print(f"\n策略：{strategy.name}")
        
        try:
            result = run_portfolio_backtest(data_dict, strategy)
            
            if "error" in result:
                print(f"  ❌ 错误：{result['error']}")
                continue
            
            # 标记年化 20%+ 的策略
            marker = "⭐" if result['annual_return'] >= 0.20 else "  "
            print(f"  {marker} 年化收益：{result['annual_return']*100:6.1f}%")
            print(f"     夏普比率：{result['sharpe_ratio']:5.2f} | "
                  f"最大回撤：{result['max_drawdown']*100:6.1f}% | "
                  f"交易次数：{result['num_trades']}")
            print(f"     胜率：{result['win_rate']*100:5.1f}% | "
                  f"总收益：{result['total_return']*100:6.1f}%")
            
            results.append(result)
            
        except Exception as e:
            print(f"  ❌ 失败：{e}")
            import traceback
            traceback.print_exc()
    
    # 汇总结果
    print("\n")
    print("=" * 80)
    print(" " * 35 + "优秀策略汇总（年化≥20%）")
    print("=" * 80)
    print()
    
    # 筛选年化 20%+ 的策略
    top_strategies = [r for r in results if r.get('annual_return', 0) >= 0.20]
    
    if not top_strategies:
        print("⚠️  未找到年化 20%+ 的策略")
        print()
        
        # 显示所有策略结果
        if results:
            print("所有策略结果（按年化排序）：")
            sorted_results = sorted(results, key=lambda x: x.get('annual_return', 0), reverse=True)
            for i, r in enumerate(sorted_results, 1):
                marker = "⭐" if r['annual_return'] >= 0.10 else "  "
                print(f"  {marker} {i}. {r['strategy_name']}")
                print(f"      年化：{r['annual_return']*100:6.1f}% | "
                      f"夏普：{r['sharpe_ratio']:5.2f} | "
                      f"回撤：{r['max_drawdown']*100:6.1f}% | "
                      f"胜率：{r['win_rate']*100:5.1f}%")
    else:
        print(f"🎉 找到 {len(top_strategies)} 个年化 20%+ 的策略！\n")
        
        # 按年化收益排序
        top_strategies.sort(key=lambda x: x['annual_return'], reverse=True)
        
        for i, r in enumerate(top_strategies, 1):
            print(f"{i}. {r['strategy_name']}")
            print(f"   年化：{r['annual_return']*100:.1f}% | "
                  f"夏普：{r['sharpe_ratio']:.2f} | "
                  f"回撤：{r['max_drawdown']*100:.1f}% | "
                  f"胜率：{r['win_rate']*100:.1f}%")
            print()
        
        # 最佳策略详情
        best = top_strategies[0]
        print("=" * 80)
        print("🏆 最佳策略详情")
        print("=" * 80)
        print(f"  策略：{best['strategy_name']}")
        print(f"  初始资金：{best['initial_capital']:,.0f}")
        print(f"  最终资金：{best['final_capital']:,.0f}")
        print(f"  年化收益：{best['annual_return']*100:.1f}%")
        print(f"  夏普比率：{best['sharpe_ratio']:.2f}")
        print(f"  最大回撤：{best['max_drawdown']*100:.1f}%")
        print(f"  交易次数：{best['num_trades']}")
        print(f"  胜率：{best['win_rate']*100:.1f}%")
    
    print()
    print("=" * 80)
    print("测试完成！")
    print("=" * 80)
    print()
    
    # 保存结果
    if results:
        # 保存 CSV
        output_file = Path(__file__).parent / "portfolio_results.csv"
        
        # 转换为 DataFrame（移除 equity_curve 等长字段）
        results_df = []
        for r in results:
            row = {k: v for k, v in r.items() if k not in ['equity_curve', 'dates', 'trades']}
            results_df.append(row)
        
        df = pd.DataFrame(results_df)
        df.to_csv(output_file, index=False, encoding="utf-8-sig")
        print(f"📊 结果已保存：{output_file}")
        
        # 保存最佳策略的详细交易记录
        if top_strategies:
            trades_file = Path(__file__).parent / "best_strategy_trades.csv"
            best_trades = pd.DataFrame(top_strategies[0].get('trades', []))
            if not best_trades.empty:
                best_trades.to_csv(trades_file, index=False, encoding="utf-8-sig")
                print(f"📊 交易记录已保存：{trades_file}")
    
    return results


if __name__ == "__main__":
    main()

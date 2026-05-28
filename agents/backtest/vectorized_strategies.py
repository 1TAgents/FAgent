"""
向量化策略库 - 使用 pandas/numpy 向量化计算，性能提升 10-100x

对比：
- 原始版本：逐日循环，~1 秒/250 天
- 向量化版本：矩阵运算，~0.01 秒/250 天
"""
import pandas as pd
import numpy as np
from typing import Any, Dict, Optional

from .trading_cost import TradingCostCalculator


EXECUTION_PARAM_CASTS = {
    "max_position": float,
    "lot_size": int,
    "slippage": float,
}


def split_vectorized_params(params: Optional[Dict[str, Any]]) -> tuple[Dict[str, Any], Dict[str, Any]]:
    """拆分策略参数和回测执行参数。"""
    strategy_params = {}
    execution_params = {}

    for key, value in (params or {}).items():
        if key in EXECUTION_PARAM_CASTS:
            if value is not None:
                cast_value = EXECUTION_PARAM_CASTS[key](value)
                if key == "lot_size" and cast_value < 1:
                    raise ValueError("lot_size 必须大于等于 1")
                if key == "max_position" and not 0 < cast_value <= 1:
                    raise ValueError("max_position 必须在 (0, 1] 区间内")
                if key == "slippage" and cast_value < 0:
                    raise ValueError("slippage 不能为负数")
                execution_params[key] = cast_value
        else:
            strategy_params[key] = value

    return strategy_params, execution_params


def run_long_only_backtest(
    data: pd.DataFrame,
    initial_capital: float = 100000.0,
    *,
    max_position: float = 0.95,
    lot_size: int = 100,
    slippage: float = 0.001,
    cost_calculator: Optional[TradingCostCalculator] = None,
) -> Dict:
    """
    执行单标的、只做多的向量化信号回测。

    signal 语义：
    - 1：空仓时买入
    - -1：持仓时卖出
    - 0：保持当前状态

    这里显式维护持仓状态，而不是把 signal 当作每日仓位，避免只在信号当天
    计算收益的错误。
    """
    if data.empty:
        return _empty_backtest_result(initial_capital)

    df = data.copy().sort_index()
    if "signal" not in df.columns:
        df["signal"] = 0

    cost_calculator = cost_calculator or TradingCostCalculator()

    cash = float(initial_capital)
    shares = 0
    avg_cost = 0.0
    entry_date = None
    entry_cost = 0.0
    equity_curve = []
    positions = []
    orders = []
    trades = []
    total_cost = 0.0

    for date, row in df.iterrows():
        price = float(row["close"])
        if not np.isfinite(price) or price <= 0:
            fallback_price = equity_curve[-1]["price"] if equity_curve else 0
            equity_curve.append({
                "date": _format_date(date),
                "equity": cash + shares * fallback_price,
                "price": fallback_price,
            })
            positions.append(shares)
            continue

        signal = int(row.get("signal", 0) or 0)
        date_text = _format_date(date)

        if signal > 0 and shares == 0:
            fill_price = price * (1 + slippage)
            target_cash = cash * max_position
            quantity = int(target_cash // fill_price // lot_size * lot_size)

            while quantity > 0:
                cost = cost_calculator.calculate_cost(fill_price, quantity, "buy")
                if fill_price * quantity + cost <= cash:
                    break
                quantity -= lot_size

            if quantity > 0:
                cost = cost_calculator.calculate_cost(fill_price, quantity, "buy")
                cash -= fill_price * quantity + cost
                shares = quantity
                avg_cost = fill_price
                entry_date = date_text
                entry_cost = cost
                total_cost += cost
                orders.append({
                    "date": date_text,
                    "side": "buy",
                    "price": fill_price,
                    "quantity": quantity,
                    "cost": cost,
                })

        elif signal < 0 and shares > 0:
            fill_price = price * (1 - slippage)
            cost = cost_calculator.calculate_cost(fill_price, shares, "sell")
            proceeds = fill_price * shares - cost
            pnl = (fill_price - avg_cost) * shares - entry_cost - cost
            pnl_percent = pnl / (avg_cost * shares) if avg_cost and shares else 0.0

            cash += proceeds
            total_cost += cost
            orders.append({
                "date": date_text,
                "side": "sell",
                "price": fill_price,
                "quantity": shares,
                "cost": cost,
            })
            trades.append({
                "symbol": str(row.get("symbol", "")) or "UNKNOWN",
                "entry_price": avg_cost,
                "exit_price": fill_price,
                "entry_time": entry_date or date_text,
                "exit_time": date_text,
                "quantity": shares,
                "side": "long",
                "pnl": pnl,
                "pnl_percent": pnl_percent,
                "commission_total": entry_cost + cost,
                "is_open": False,
                "exit_reason": "signal",
            })

            shares = 0
            avg_cost = 0.0
            entry_date = None
            entry_cost = 0.0

        equity = cash + shares * price
        equity_curve.append({"date": date_text, "equity": equity, "price": price})
        positions.append(shares)

    if shares > 0:
        last_date = equity_curve[-1]["date"]
        last_price = float(df.iloc[-1]["close"])
        unrealized_pnl = (last_price - avg_cost) * shares - entry_cost
        trades.append({
            "symbol": str(df.iloc[-1].get("symbol", "")) or "UNKNOWN",
            "entry_price": avg_cost,
            "exit_price": None,
            "entry_time": entry_date or last_date,
            "exit_time": None,
            "quantity": shares,
            "side": "long",
            "pnl": unrealized_pnl,
            "pnl_percent": unrealized_pnl / (avg_cost * shares) if avg_cost and shares else 0.0,
            "commission_total": entry_cost,
            "is_open": True,
            "exit_reason": None,
        })

    equity_values = pd.Series(
        [item["equity"] for item in equity_curve],
        index=pd.to_datetime([item["date"] for item in equity_curve]),
        dtype=float,
    )
    daily_returns = equity_values.pct_change().fillna(0.0)
    final_capital = float(equity_values.iloc[-1]) if not equity_values.empty else initial_capital
    total_returns = final_capital / initial_capital - 1 if initial_capital else 0.0
    benchmark_return = _buy_and_hold_return(df)
    trading_days = len(equity_values)
    annual_return = (1 + total_returns) ** (252 / trading_days) - 1 if trading_days and total_returns > -1 else -1.0
    volatility = float(daily_returns.std() * np.sqrt(252)) if len(daily_returns) > 1 else 0.0
    sharpe = float(np.sqrt(252) * daily_returns.mean() / daily_returns.std()) if daily_returns.std() > 0 else 0.0

    rolling_max = equity_values.cummax()
    drawdown = (equity_values - rolling_max) / rolling_max
    max_drawdown = float(drawdown.min()) if not drawdown.empty else 0.0

    closed_trades = [trade for trade in trades if not trade["is_open"]]
    winning_trades = [trade for trade in closed_trades if (trade.get("pnl") or 0) > 0]
    losing_trades = [trade for trade in closed_trades if (trade.get("pnl") or 0) < 0]
    gross_profit = sum(trade["pnl"] for trade in winning_trades)
    gross_loss = abs(sum(trade["pnl"] for trade in losing_trades))

    return {
        "total_returns": float(total_returns),
        "annual_return": float(annual_return),
        "benchmark_return": benchmark_return,
        "alpha": float(total_returns - benchmark_return),
        "volatility": volatility,
        "sharpe_ratio": sharpe,
        "max_drawdown": max_drawdown,
        "trades": len(orders),
        "closed_trades": len(closed_trades),
        "winning_trades": len(winning_trades),
        "losing_trades": len(losing_trades),
        "win_rate": len(winning_trades) / len(closed_trades) if closed_trades else 0.0,
        "profit_factor": gross_profit / gross_loss if gross_loss else (gross_profit if gross_profit else 0.0),
        "avg_win": gross_profit / len(winning_trades) if winning_trades else 0.0,
        "avg_loss": -gross_loss / len(losing_trades) if losing_trades else 0.0,
        "final_capital": final_capital,
        "total_pnl": final_capital - initial_capital,
        "total_cost": total_cost,
        "equity_curve": equity_values.tolist(),
        "dates": equity_values.index.tolist(),
        "positions": positions,
        "orders": orders,
        "trade_records": trades,
        "daily_returns": daily_returns.tolist(),
    }


def _empty_backtest_result(initial_capital: float) -> Dict:
    return {
        "total_returns": 0.0,
        "annual_return": 0.0,
        "benchmark_return": 0.0,
        "alpha": 0.0,
        "volatility": 0.0,
        "sharpe_ratio": 0.0,
        "max_drawdown": 0.0,
        "trades": 0,
        "closed_trades": 0,
        "winning_trades": 0,
        "losing_trades": 0,
        "win_rate": 0.0,
        "profit_factor": 0.0,
        "avg_win": 0.0,
        "avg_loss": 0.0,
        "final_capital": initial_capital,
        "total_pnl": 0.0,
        "total_cost": 0.0,
        "equity_curve": [],
        "dates": [],
        "positions": [],
        "orders": [],
        "trade_records": [],
        "daily_returns": [],
    }


def _format_date(value) -> str:
    if hasattr(value, "strftime"):
        return value.strftime("%Y-%m-%d")
    return str(value)[:10]


def _buy_and_hold_return(data: pd.DataFrame) -> float:
    prices = pd.to_numeric(data.get("close", pd.Series(dtype=float)), errors="coerce")
    prices = prices.replace([np.inf, -np.inf], np.nan).dropna()
    prices = prices[prices > 0]
    if len(prices) < 2:
        return 0.0
    return float(prices.iloc[-1] / prices.iloc[0] - 1)


def _relative_strength_index(close: pd.Series, period: int) -> pd.Series:
    close = pd.to_numeric(close, errors="coerce")
    delta = close.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)

    avg_gain = gain.rolling(window=period).mean()
    avg_loss = loss.rolling(window=period).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    rsi = rsi.where(avg_loss != 0, 100.0)
    rsi = rsi.where(~((avg_gain == 0) & (avg_loss == 0)), 50.0)
    return rsi


class VectorizedDualMA:
    """
    双均线策略（向量化版本）
    
    使用 pandas rolling 计算均线，numpy 生成信号
    性能：~0.01 秒（250 个交易日）
    """
    
    def __init__(self, short_period: int = 5, long_period: int = 20):
        self.short_period = short_period
        self.long_period = long_period
    
    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        生成交易信号（向量化）
        
        Args:
            data: DataFrame (index=date, columns=['close', 'open', 'high', 'low', ...])
            
        Returns:
            DataFrame 添加 signal 列（1=买入，-1=卖出，0=持仓）
        """
        df = data.copy()
        
        # 向量化计算均线
        df['short_ma'] = df['close'].rolling(window=self.short_period).mean()
        df['long_ma'] = df['close'].rolling(window=self.long_period).mean()
        
        # 向量化生成信号
        # 金叉：短均线上穿长均线
        df['golden_cross'] = (
            (df['short_ma'] > df['long_ma']) & 
            (df['short_ma'].shift(1) <= df['long_ma'].shift(1))
        )
        
        # 死叉：短均线下穿长均线
        df['death_cross'] = (
            (df['short_ma'] < df['long_ma']) & 
            (df['short_ma'].shift(1) >= df['long_ma'].shift(1))
        )
        
        # 信号列：1=买入，-1=卖出，0=持仓
        df['signal'] = 0
        df.loc[df['golden_cross'], 'signal'] = 1
        df.loc[df['death_cross'], 'signal'] = -1
        
        return df
    
    def backtest(self, data: pd.DataFrame, initial_capital: float = 100000.0, **execution_kwargs) -> Dict:
        """
        快速回测（向量化）
        
        Args:
            data: DataFrame (包含 signal 列)
            initial_capital: 初始资金
            
        Returns:
            绩效字典
        """
        return run_long_only_backtest(data, initial_capital, **execution_kwargs)


class VectorizedRSI:
    """
    RSI 策略（向量化版本）
    """
    
    def __init__(self, period: int = 14, oversold: float = 30, overbought: float = 70):
        self.period = period
        self.oversold = oversold
        self.overbought = overbought
    
    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """生成 RSI 信号"""
        df = data.copy()
        
        # 向量化计算 RSI
        delta = df['close'].diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        
        avg_gain = gain.rolling(window=self.period).mean()
        avg_loss = loss.rolling(window=self.period).mean()
        
        rs = avg_gain / avg_loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # 生成信号
        df['signal'] = 0
        df.loc[df['rsi'] < self.oversold, 'signal'] = 1
        df.loc[df['rsi'] > self.overbought, 'signal'] = -1
        
        return df
    
    def backtest(self, data: pd.DataFrame, initial_capital: float = 100000.0, **execution_kwargs) -> Dict:
        """快速回测"""
        return run_long_only_backtest(data, initial_capital, **execution_kwargs)


class VectorizedRSI2:
    """Connors RSI2 短线均值回归策略。"""

    def __init__(
        self,
        period: int = 2,
        trend_ma: int = 200,
        buy_below: float = 10,
        sell_above: float = 65,
    ):
        self.period = period
        self.trend_ma = trend_ma
        self.buy_below = buy_below
        self.sell_above = sell_above

    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        df = data.copy()
        df["trend_ma"] = df["close"].rolling(window=self.trend_ma).mean()
        df["rsi2"] = _relative_strength_index(df["close"], self.period)

        df["signal"] = 0
        df.loc[(df["close"] > df["trend_ma"]) & (df["rsi2"] <= self.buy_below), "signal"] = 1
        df.loc[df["rsi2"] >= self.sell_above, "signal"] = -1
        return df

    def backtest(self, data: pd.DataFrame, initial_capital: float = 100000.0, **execution_kwargs) -> Dict:
        return run_long_only_backtest(data, initial_capital, **execution_kwargs)


class VectorizedMACD:
    """
    MACD 策略（向量化版本）
    """
    
    def __init__(self, fast: int = 12, slow: int = 26, signal: int = 9):
        self.fast = fast
        self.slow = slow
        self.signal_period = signal
    
    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """生成 MACD 信号"""
        df = data.copy()
        
        # 计算 EMA
        ema_fast = df['close'].ewm(span=self.fast, adjust=False).mean()
        ema_slow = df['close'].ewm(span=self.slow, adjust=False).mean()
        
        # MACD 线
        df['macd'] = ema_fast - ema_slow
        
        # Signal 线
        df['signal_line'] = df['macd'].ewm(span=self.signal_period, adjust=False).mean()
        
        # MACD 柱
        df['macd_hist'] = df['macd'] - df['signal_line']
        
        # 生成信号
        df['signal'] = 0
        
        # 金叉：MACD 上穿 Signal
        golden_cross = (
            (df['macd'] > df['signal_line']) & 
            (df['macd'].shift(1) <= df['signal_line'].shift(1))
        )
        df.loc[golden_cross, 'signal'] = 1
        
        # 死叉：MACD 下穿 Signal
        death_cross = (
            (df['macd'] < df['signal_line']) & 
            (df['macd'].shift(1) >= df['signal_line'].shift(1))
        )
        df.loc[death_cross, 'signal'] = -1
        
        return df
    
    def backtest(self, data: pd.DataFrame, initial_capital: float = 100000.0, **execution_kwargs) -> Dict:
        """快速回测"""
        return run_long_only_backtest(data, initial_capital, **execution_kwargs)


class VectorizedBollinger:
    """
    布林带策略（向量化版本）
    """
    
    def __init__(self, period: int = 20, std_dev: float = 2.0):
        self.period = period
        self.std_dev = std_dev
    
    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """生成布林带信号"""
        df = data.copy()
        
        df['middle'] = df['close'].rolling(window=self.period).mean()
        rolling_std = df['close'].rolling(window=self.period).std()
        df['upper'] = df['middle'] + (self.std_dev * rolling_std)
        df['lower'] = df['middle'] - (self.std_dev * rolling_std)
        
        df['signal'] = 0
        df.loc[df['close'] < df['lower'], 'signal'] = 1
        df.loc[df['close'] > df['upper'], 'signal'] = -1
        df['bandwidth'] = (df['upper'] - df['lower']) / df['middle']
        
        return df
    
    def backtest(self, data: pd.DataFrame, initial_capital: float = 100000.0, **execution_kwargs) -> Dict:
        """快速回测"""
        return run_long_only_backtest(data, initial_capital, **execution_kwargs)


class VectorizedKDJ:
    """
    KDJ 策略（向量化版本）
    
    KDJ 是随机指标，适用于震荡市
    """
    
    def __init__(self, n: int = 9, m1: int = 3, m2: int = 3):
        """
        初始化
        
        Args:
            n: RSV 计算周期（默认 9）
            m1: K 值平滑周期（默认 3）
            m2: D 值平滑周期（默认 3）
        """
        self.n = n
        self.m1 = m1
        self.m2 = m2
    
    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """生成 KDJ 信号"""
        df = data.copy()
        
        # 计算 RSV（未成熟随机值）
        lowest_low = df['low'].rolling(window=self.n).min()
        highest_high = df['high'].rolling(window=self.n).max()
        
        rsv = (df['close'] - lowest_low) / (highest_high - lowest_low) * 100
        
        # 计算 K 值（3 日移动平均）
        df['k'] = rsv.ewm(com=self.m1-1, adjust=False).mean()
        
        # 计算 D 值（K 的 3 日移动平均）
        df['d'] = df['k'].ewm(com=self.m2-1, adjust=False).mean()
        
        # 计算 J 值（3 倍 K 减 2 倍 D）
        df['j'] = 3 * df['k'] - 2 * df['d']
        
        # 生成信号
        df['signal'] = 0
        
        # K 上穿 D（金叉）→ 买入
        golden_cross = (
            (df['k'] > df['d']) & 
            (df['k'].shift(1) <= df['d'].shift(1))
        )
        df.loc[golden_cross, 'signal'] = 1
        
        # K 下穿 D（死叉）→ 卖出
        death_cross = (
            (df['k'] < df['d']) & 
            (df['k'].shift(1) >= df['d'].shift(1))
        )
        df.loc[death_cross, 'signal'] = -1
        
        # 超卖区域（K<20）→ 买入信号增强
        df.loc[df['k'] < 20, 'signal'] = 1
        
        # 超买区域（K>80）→ 卖出信号增强
        df.loc[df['k'] > 80, 'signal'] = -1
        
        return df
    
    def backtest(self, data: pd.DataFrame, initial_capital: float = 100000.0, **execution_kwargs) -> Dict:
        """快速回测"""
        return run_long_only_backtest(data, initial_capital, **execution_kwargs)


class VectorizedMomentum:
    """
    动量策略（向量化版本）
    
    买入过去表现好的股票，卖出表现差的
    """
    
    def __init__(self, lookback: int = 20, threshold: float = 0.05):
        """
        初始化
        
        Args:
            lookback: 回看周期（默认 20 日）
            threshold: 动量阈值（默认 5%）
        """
        self.lookback = lookback
        self.threshold = threshold
    
    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """生成动量信号"""
        df = data.copy()
        
        # 计算动量（N 日收益率）
        df['momentum'] = df['close'].pct_change(periods=self.lookback)
        
        # 生成信号
        df['signal'] = 0
        
        # 动量为正且超过阈值 → 买入
        df.loc[df['momentum'] > self.threshold, 'signal'] = 1
        
        # 动量为负且低于阈值 → 卖出
        df.loc[df['momentum'] < -self.threshold, 'signal'] = -1
        
        return df
    
    def backtest(self, data: pd.DataFrame, initial_capital: float = 100000.0, **execution_kwargs) -> Dict:
        """快速回测"""
        return run_long_only_backtest(data, initial_capital, **execution_kwargs)


class VectorizedDonchianBreakout:
    """Donchian/Turtle 中线突破策略。"""

    def __init__(self, entry_window: int = 20, exit_window: int = 10):
        self.entry_window = entry_window
        self.exit_window = exit_window

    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        df = data.copy()
        df["entry_high"] = df["high"].rolling(window=self.entry_window).max().shift(1)
        df["exit_low"] = df["low"].rolling(window=self.exit_window).min().shift(1)

        df["signal"] = 0
        df.loc[df["close"] > df["entry_high"], "signal"] = 1
        df.loc[df["close"] < df["exit_low"], "signal"] = -1
        return df

    def backtest(self, data: pd.DataFrame, initial_capital: float = 100000.0, **execution_kwargs) -> Dict:
        return run_long_only_backtest(data, initial_capital, **execution_kwargs)


class VectorizedSMATrend:
    """长期均线趋势过滤策略。"""

    def __init__(self, ma_period: int = 200):
        self.ma_period = ma_period

    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        df = data.copy()
        df["long_ma"] = df["close"].rolling(window=self.ma_period).mean()

        df["signal"] = 0
        df.loc[df["close"] > df["long_ma"], "signal"] = 1
        df.loc[df["close"] < df["long_ma"], "signal"] = -1
        return df

    def backtest(self, data: pd.DataFrame, initial_capital: float = 100000.0, **execution_kwargs) -> Dict:
        return run_long_only_backtest(data, initial_capital, **execution_kwargs)


# 策略工厂
STRATEGY_MAP = {
    'dual_ma': VectorizedDualMA,
    'rsi': VectorizedRSI,
    'rsi2': VectorizedRSI2,
    'macd': VectorizedMACD,
    'bollinger': VectorizedBollinger,
    'kdj': VectorizedKDJ,
    'momentum': VectorizedMomentum,
    'donchian_breakout': VectorizedDonchianBreakout,
    'sma_trend': VectorizedSMATrend,
}


def get_vectorized_strategy(name: str, **params):
    """
    获取向量化策略实例
    
    Args:
        name: 策略名称
        **params: 策略参数
        
    Returns:
        策略实例
    """
    if name not in STRATEGY_MAP:
        raise ValueError(f"未知策略：{name}. 可用策略：{list(STRATEGY_MAP.keys())}")
    
    return STRATEGY_MAP[name](**params)

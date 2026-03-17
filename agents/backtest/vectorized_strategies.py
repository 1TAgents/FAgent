"""
向量化策略库 - 使用 pandas/numpy 向量化计算，性能提升 10-100x

对比：
- 原始版本：逐日循环，~1 秒/250 天
- 向量化版本：矩阵运算，~0.01 秒/250 天
"""
import pandas as pd
import numpy as np
from typing import List, Dict, Tuple
from datetime import datetime

from .models import TradingSignal, SignalType


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
    
    def backtest(self, data: pd.DataFrame, initial_capital: float = 100000.0) -> Dict:
        """
        快速回测（向量化）
        
        Args:
            data: DataFrame (包含 signal 列)
            initial_capital: 初始资金
            
        Returns:
            绩效字典
        """
        df = data.copy()
        
        # 计算策略收益
        df['returns'] = df['close'].pct_change()
        df['strategy_returns'] = df['signal'].shift(1) * df['returns']
        
        # 计算累计收益
        df['cumulative_returns'] = (1 + df['strategy_returns']).cumprod()
        df['equity'] = initial_capital * df['cumulative_returns']
        
        # 绩效指标
        total_returns = df['cumulative_returns'].iloc[-1] - 1
        daily_returns = df['strategy_returns'].dropna()
        
        # 夏普比率（年化）
        sharpe = np.sqrt(252) * daily_returns.mean() / daily_returns.std() if daily_returns.std() > 0 else 0
        
        # 最大回撤
        rolling_max = df['equity'].cummax()
        drawdown = (df['equity'] - rolling_max) / rolling_max
        max_drawdown = drawdown.min()
        
        # 交易次数
        trades = df['signal'].abs().sum()
        
        return {
            'total_returns': total_returns,
            'sharpe_ratio': sharpe,
            'max_drawdown': max_drawdown,
            'trades': trades,
            'equity_curve': df['equity'].tolist(),
            'dates': df.index.tolist()
        }


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
    
    def backtest(self, data: pd.DataFrame, initial_capital: float = 100000.0) -> Dict:
        """快速回测"""
        df = data.copy()
        df['returns'] = df['close'].pct_change()
        df['strategy_returns'] = df['signal'].shift(1) * df['returns']
        df['cumulative_returns'] = (1 + df['strategy_returns']).cumprod()
        df['equity'] = initial_capital * df['cumulative_returns']
        
        total_returns = df['cumulative_returns'].iloc[-1] - 1
        daily_returns = df['strategy_returns'].dropna()
        sharpe = np.sqrt(252) * daily_returns.mean() / daily_returns.std() if daily_returns.std() > 0 else 0
        
        rolling_max = df['equity'].cummax()
        drawdown = (df['equity'] - rolling_max) / rolling_max
        
        return {
            'total_returns': total_returns,
            'sharpe_ratio': sharpe,
            'max_drawdown': drawdown.min(),
            'trades': df['signal'].abs().sum(),
            'equity_curve': df['equity'].tolist(),
            'dates': df.index.tolist()
        }


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
    
    def backtest(self, data: pd.DataFrame, initial_capital: float = 100000.0) -> Dict:
        """快速回测"""
        df = data.copy()
        
        # 计算策略收益
        df['returns'] = df['close'].pct_change()
        df['strategy_returns'] = df['signal'].shift(1) * df['returns']
        
        # 累计收益
        df['cumulative_returns'] = (1 + df['strategy_returns']).cumprod()
        df['equity'] = initial_capital * df['cumulative_returns']
        
        # 绩效指标
        total_returns = df['cumulative_returns'].iloc[-1] - 1
        daily_returns = df['strategy_returns'].dropna()
        sharpe = np.sqrt(252) * daily_returns.mean() / daily_returns.std() if daily_returns.std() > 0 else 0
        
        # 最大回撤
        rolling_max = df['equity'].cummax()
        drawdown = (df['equity'] - rolling_max) / rolling_max
        max_drawdown = drawdown.min()
        
        trades = df['signal'].abs().sum()
        
        return {
            'total_returns': total_returns,
            'sharpe_ratio': sharpe,
            'max_drawdown': max_drawdown,
            'trades': trades,
            'equity_curve': df['equity'].tolist(),
            'dates': df.index.tolist()
        }


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
    
    def backtest(self, data: pd.DataFrame, initial_capital: float = 100000.0) -> Dict:
        """快速回测"""
        df = data.copy()
        df['returns'] = df['close'].pct_change()
        df['strategy_returns'] = df['signal'].shift(1) * df['returns']
        df['cumulative_returns'] = (1 + df['strategy_returns']).cumprod()
        df['equity'] = initial_capital * df['cumulative_returns']
        
        total_returns = df['cumulative_returns'].iloc[-1] - 1
        daily_returns = df['strategy_returns'].dropna()
        sharpe = np.sqrt(252) * daily_returns.mean() / daily_returns.std() if daily_returns.std() > 0 else 0
        
        rolling_max = df['equity'].cummax()
        drawdown = (df['equity'] - rolling_max) / rolling_max
        
        return {
            'total_returns': total_returns,
            'sharpe_ratio': sharpe,
            'max_drawdown': drawdown.min(),
            'trades': df['signal'].abs().sum(),
            'equity_curve': df['equity'].tolist(),
            'dates': df.index.tolist()
        }


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
    
    def backtest(self, data: pd.DataFrame, initial_capital: float = 100000.0) -> Dict:
        """快速回测"""
        df = data.copy()
        
        df['returns'] = df['close'].pct_change()
        df['strategy_returns'] = df['signal'].shift(1) * df['returns']
        df['cumulative_returns'] = (1 + df['strategy_returns']).cumprod()
        df['equity'] = initial_capital * df['cumulative_returns']
        
        total_returns = df['cumulative_returns'].iloc[-1] - 1
        daily_returns = df['strategy_returns'].dropna()
        sharpe = np.sqrt(252) * daily_returns.mean() / daily_returns.std() if daily_returns.std() > 0 else 0
        
        rolling_max = df['equity'].cummax()
        drawdown = (df['equity'] - rolling_max) / rolling_max
        
        return {
            'total_returns': total_returns,
            'sharpe_ratio': sharpe,
            'max_drawdown': drawdown.min(),
            'trades': df['signal'].abs().sum(),
            'equity_curve': df['equity'].tolist(),
            'dates': df.index.tolist()
        }


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
    
    def backtest(self, data: pd.DataFrame, initial_capital: float = 100000.0) -> Dict:
        """快速回测"""
        df = data.copy()
        
        df['returns'] = df['close'].pct_change()
        df['strategy_returns'] = df['signal'].shift(1) * df['returns']
        df['cumulative_returns'] = (1 + df['strategy_returns']).cumprod()
        df['equity'] = initial_capital * df['cumulative_returns']
        
        total_returns = df['cumulative_returns'].iloc[-1] - 1
        daily_returns = df['strategy_returns'].dropna()
        sharpe = np.sqrt(252) * daily_returns.mean() / daily_returns.std() if daily_returns.std() > 0 else 0
        
        rolling_max = df['equity'].cummax()
        drawdown = (df['equity'] - rolling_max) / rolling_max
        
        return {
            'total_returns': total_returns,
            'sharpe_ratio': sharpe,
            'max_drawdown': drawdown.min(),
            'trades': df['signal'].abs().sum(),
            'equity_curve': df['equity'].tolist(),
            'dates': df.index.tolist()
        }


# 策略工厂
STRATEGY_MAP = {
    'dual_ma': VectorizedDualMA,
    'rsi': VectorizedRSI,
    'macd': VectorizedMACD,
    'bollinger': VectorizedBollinger,
    'kdj': VectorizedKDJ,
    'momentum': VectorizedMomentum,
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

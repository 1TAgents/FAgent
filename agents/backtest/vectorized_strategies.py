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


# 策略工厂
STRATEGY_MAP = {
    'dual_ma': VectorizedDualMA,
    'rsi': VectorizedRSI,
    'macd': VectorizedMACD,
    'bollinger': VectorizedBollinger,
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

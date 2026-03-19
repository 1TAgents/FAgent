"""
期货策略 - 双均线策略（支持做多和做空）
Skill ID: future-dual-ma
"""
import pandas as pd
import numpy as np
from typing import List, Dict

from agents.backtest.models import (
    StrategyConfig, TradingSignal, SignalType, Portfolio, Position
)
from agents.backtest.engine import BaseStrategy


class FutureDualMAStrategy(BaseStrategy):
    """
    期货双均线交叉策略
    
    支持做多和做空双向交易
    
    参数:
        short_period: 短期均线周期（默认 10）
        long_period: 长期均线周期（默认 30）
        allow_short: 允许做空（默认 True）
    """
    
    def __init__(self, config: StrategyConfig):
        super().__init__(config)
        self.short_period = self.params.get('short_period', 10)
        self.long_period = self.params.get('long_period', 30)
        self.allow_short = self.params.get('allow_short', True)
        self.close_prices: List[float] = []
        self.dates: List[str] = []
        self.current_position = None  # None / 'long' / 'short'
    
    def generate_signals(
        self,
        row: pd.Series,
        portfolio: Portfolio,
        positions: Dict[str, Position]
    ) -> List[TradingSignal]:
        signals = []
        
        close = row.get('close', 0)
        self.close_prices.append(close)
        self.dates.append(row.get('date', str(row.name)))
        
        if len(self.close_prices) < self.long_period:
            return signals
        
        symbol = row.get('symbol', 'UNKNOWN')
        
        # 计算均线
        short_ma = np.mean(self.close_prices[-self.short_period:])
        long_ma = np.mean(self.close_prices[-self.long_period:])
        
        if len(self.close_prices) > self.long_period:
            prev_short_ma = np.mean(self.close_prices[-self.short_period-1:-1])
            prev_long_ma = np.mean(self.close_prices[-self.long_period-1:-1])
        else:
            return signals
        
        # 金叉：短均线上穿长均线
        if prev_short_ma <= prev_long_ma and short_ma > long_ma:
            # 如果有空仓，先平空
            if self.current_position == 'short':
                signals.append(TradingSignal(
                    signal_type=SignalType.EXIT_SHORT,
                    symbol=symbol,
                    price=close,
                    timestamp=self.dates[-1],
                    reason=f"金叉平仓：短均线{short_ma:.2f} > 长均线{long_ma:.2f}",
                ))
            
            # 开多
            if self.current_position is None:
                signals.append(TradingSignal(
                    signal_type=SignalType.ENTRY_LONG,
                    symbol=symbol,
                    price=close,
                    timestamp=self.dates[-1],
                    reason=f"金叉开多：短均线{short_ma:.2f} > 长均线{long_ma:.2f}",
                    position_size=0.8
                ))
                self.current_position = 'long'
        
        # 死叉：短均线下穿长均线
        elif prev_short_ma >= prev_long_ma and short_ma < long_ma:
            # 如果有多仓，先平多
            if self.current_position == 'long':
                signals.append(TradingSignal(
                    signal_type=SignalType.EXIT_LONG,
                    symbol=symbol,
                    price=close,
                    timestamp=self.dates[-1],
                    reason=f"死叉平仓：短均线{short_ma:.2f} < 长均线{long_ma:.2f}",
                ))
            
            # 开空
            if self.allow_short and self.current_position is None:
                signals.append(TradingSignal(
                    signal_type=SignalType.ENTRY_SHORT,
                    symbol=symbol,
                    price=close,
                    timestamp=self.dates[-1],
                    reason=f"死叉开空：短均线{short_ma:.2f} < 长均线{long_ma:.2f}",
                    position_size=0.8
                ))
                self.current_position = 'short'
        
        return signals

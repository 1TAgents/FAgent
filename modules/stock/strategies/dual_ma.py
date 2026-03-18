"""
股票策略 - 双均线策略
"""
import pandas as pd
import numpy as np
from typing import List, Dict

from agents.backtest.models import (
    StrategyConfig, TradingSignal, SignalType, Portfolio, Position
)
from agents.backtest.engine import BaseStrategy


class StockDualMAStrategy(BaseStrategy):
    """
    股票双均线交叉策略
    
    参数:
        short_period: 短期均线周期（默认 5）
        long_period: 长期均线周期（默认 20）
    """
    
    def __init__(self, config: StrategyConfig):
        super().__init__(config)
        self.short_period = self.params.get('short_period', 5)
        self.long_period = self.params.get('long_period', 20)
        self.close_prices: List[float] = []
        self.dates: List[str] = []
    
    def generate_signals(
        self,
        row: pd.Series,
        portfolio: Portfolio,
        positions: Dict[str, Position]
    ) -> List[TradingSignal]:
        signals = []
        
        close = row.get('close', row.get('收盘', 0))
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
        
        # 金叉：买入
        if prev_short_ma <= prev_long_ma and short_ma > long_ma:
            if symbol not in positions:
                signals.append(TradingSignal(
                    signal_type=SignalType.ENTRY_LONG,
                    symbol=symbol,
                    price=close,
                    timestamp=self.dates[-1],
                    reason=f"金叉：短均线{short_ma:.2f} > 长均线{long_ma:.2f}",
                    position_size=0.95
                ))
        
        # 死叉：卖出
        elif prev_short_ma >= prev_long_ma and short_ma < long_ma:
            if symbol in positions:
                signals.append(TradingSignal(
                    signal_type=SignalType.EXIT_LONG,
                    symbol=symbol,
                    price=close,
                    timestamp=self.dates[-1],
                    reason=f"死叉：短均线{short_ma:.2f} < 长均线{long_ma:.2f}"
                ))
        
        return signals

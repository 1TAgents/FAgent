"""
期货策略 - RSI 策略（支持做多和做空）
"""
import pandas as pd
import numpy as np
from typing import List, Dict

from agents.backtest.models import (
    StrategyConfig, TradingSignal, SignalType, Portfolio, Position
)
from agents.backtest.engine import BaseStrategy


class FutureRSIStrategy(BaseStrategy):
    """
    期货 RSI 相对强弱指标策略
    
    支持做多和做空双向交易
    
    参数:
        rsi_period: RSI 周期（默认 14）
        oversold: 超卖阈值（默认 30）
        overbought: 超买阈值（默认 70）
    """
    
    def __init__(self, config: StrategyConfig):
        super().__init__(config)
        self.rsi_period = self.params.get('rsi_period', 14)
        self.oversold = self.params.get('oversold', 30)
        self.overbought = self.params.get('overbought', 70)
        self.close_prices: List[float] = []
        self.dates: List[str] = []
        self.current_position = None  # None / 'long' / 'short'
    
    def _calculate_rsi(self) -> float:
        """计算 RSI"""
        if len(self.close_prices) < self.rsi_period + 1:
            return 50.0
        
        deltas = np.diff(self.close_prices[-self.rsi_period-1:])
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        
        avg_gain = np.mean(gains)
        avg_loss = np.mean(losses)
        
        if avg_loss == 0:
            return 100.0
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
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
        
        symbol = row.get('symbol', 'UNKNOWN')
        rsi = self._calculate_rsi()
        
        # 超卖 → 做多
        if rsi < self.oversold and self.current_position is None:
            signals.append(TradingSignal(
                signal_type=SignalType.ENTRY_LONG,
                symbol=symbol,
                price=close,
                timestamp=self.dates[-1],
                reason=f"RSI 超卖：{rsi:.1f} < {self.oversold}",
                position_size=0.5
            ))
            self.current_position = 'long'
        
        # 超买 → 做空
        elif rsi > self.overbought and self.current_position is None:
            signals.append(TradingSignal(
                signal_type=SignalType.ENTRY_SHORT,
                symbol=symbol,
                price=close,
                timestamp=self.dates[-1],
                reason=f"RSI 超买：{rsi:.1f} > {self.overbought}",
                position_size=0.5
            ))
            self.current_position = 'short'
        
        # RSI 回归中性 → 平仓
        elif self.oversold < rsi < self.overbought and self.current_position is not None:
            if self.current_position == 'long':
                signals.append(TradingSignal(
                    signal_type=SignalType.EXIT_LONG,
                    symbol=symbol,
                    price=close,
                    timestamp=self.dates[-1],
                    reason=f"RSI 回归：{rsi:.1f}",
                ))
            else:
                signals.append(TradingSignal(
                    signal_type=SignalType.EXIT_SHORT,
                    symbol=symbol,
                    price=close,
                    timestamp=self.dates[-1],
                    reason=f"RSI 回归：{rsi:.1f}",
                ))
            
            self.current_position = None
        
        return signals

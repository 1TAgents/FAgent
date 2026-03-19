"""
股票策略 - RSI 策略
Skill ID: stock-rsi
"""
import pandas as pd
import numpy as np
from typing import List, Dict

from agents.backtest.models import (
    StrategyConfig, TradingSignal, SignalType, Portfolio, Position
)
from agents.backtest.engine import BaseStrategy


class StockRSIStrategy(BaseStrategy):
    """
    股票 RSI 相对强弱指标策略
    
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
        
        close = row.get('close', row.get('收盘', 0))
        self.close_prices.append(close)
        self.dates.append(row.get('date', str(row.name)))
        
        symbol = row.get('symbol', 'UNKNOWN')
        rsi = self._calculate_rsi()
        
        # 超卖 → 买入
        if rsi < self.oversold and symbol not in positions:
            signals.append(TradingSignal(
                signal_type=SignalType.ENTRY_LONG,
                symbol=symbol,
                price=close,
                timestamp=self.dates[-1],
                reason=f"RSI 超卖：{rsi:.1f} < {self.oversold}",
                position_size=0.5
            ))
        
        # 超买 → 卖出
        elif rsi > self.overbought and symbol in positions:
            signals.append(TradingSignal(
                signal_type=SignalType.EXIT_LONG,
                symbol=symbol,
                price=close,
                timestamp=self.dates[-1],
                reason=f"RSI 超买：{rsi:.1f} > {self.overbought}"
            ))
        
        return signals

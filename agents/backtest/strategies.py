"""
示例策略库

包含常用交易策略实现
"""
import pandas as pd
import numpy as np
from typing import List, Dict

from .models import (
    StrategyConfig, TradingSignal, SignalType, Portfolio, Position
)
from .engine import BaseStrategy


# ==================== 双均线策略 ====================

class DualMovingAverageStrategy(BaseStrategy):
    """
    双均线交叉策略
    
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
        
        # 累积数据
        close = row.get('close', row.get('收盘', 0))
        self.close_prices.append(close)
        self.dates.append(row.get('date', str(row.name)))
        
        # 数据不足时不生成信号
        if len(self.close_prices) < self.long_period:
            return signals
        
        symbol = row.get('symbol', 'UNKNOWN')
        
        # 计算均线
        short_ma = np.mean(self.close_prices[-self.short_period:])
        long_ma = np.mean(self.close_prices[-self.long_period:])
        
        # 前一日均线
        if len(self.close_prices) > self.long_period:
            prev_short_ma = np.mean(self.close_prices[-self.short_period-1:-1])
            prev_long_ma = np.mean(self.close_prices[-self.long_period-1:-1])
        else:
            return signals
        
        # 金叉：短期均线上穿长期均线 → 买入
        if prev_short_ma <= prev_long_ma and short_ma > long_ma:
            if symbol not in positions:  # 无持仓才买入
                signals.append(TradingSignal(
                    signal_type=SignalType.ENTRY_LONG,
                    symbol=symbol,
                    price=close,
                    timestamp=self.dates[-1],
                    reason=f"金叉：短均线{short_ma:.2f} > 长均线{long_ma:.2f}",
                    position_size=0.95  # 95% 仓位
                ))
        
        # 死叉：短期均线下穿长期均线 → 卖出
        elif prev_short_ma >= prev_long_ma and short_ma < long_ma:
            if symbol in positions:  # 有持仓才卖出
                signals.append(TradingSignal(
                    signal_type=SignalType.EXIT_LONG,
                    symbol=symbol,
                    price=close,
                    timestamp=self.dates[-1],
                    reason=f"死叉：短均线{short_ma:.2f} < 长均线{long_ma:.2f}"
                ))
        
        return signals


# ==================== RSI 策略 ====================

class RSIStrategy(BaseStrategy):
    """
    RSI 相对强弱指标策略
    
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
        
        # 计算价格变化
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
                position_size=0.5  # 50% 仓位
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


# ==================== 布林带策略 ====================

class BollingerBandsStrategy(BaseStrategy):
    """
    布林带策略
    
    参数:
        period: 周期（默认 20）
        std_dev: 标准差倍数（默认 2）
    """
    
    def __init__(self, config: StrategyConfig):
        super().__init__(config)
        self.period = self.params.get('period', 20)
        self.std_dev = self.params.get('std_dev', 2)
        self.close_prices: List[float] = []
        self.dates: List[str] = []
    
    def _calculate_bands(self) -> tuple:
        """计算布林带"""
        if len(self.close_prices) < self.period:
            return 0, 0, 0
        
        closes = np.array(self.close_prices[-self.period:])
        middle = np.mean(closes)
        std = np.std(closes)
        upper = middle + self.std_dev * std
        lower = middle - self.std_dev * std
        
        return upper, middle, lower
    
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
        upper, middle, lower = self._calculate_bands()
        
        if lower == 0:  # 数据不足
            return signals
        
        # 跌破下轨 → 买入（超卖反弹）
        if close < lower and symbol not in positions:
            signals.append(TradingSignal(
                signal_type=SignalType.ENTRY_LONG,
                symbol=symbol,
                price=close,
                timestamp=self.dates[-1],
                reason=f"跌破下轨：{close:.2f} < {lower:.2f}",
                position_size=0.5
            ))
        
        # 突破上轨 → 卖出（超买回调）
        elif close > upper and symbol in positions:
            signals.append(TradingSignal(
                signal_type=SignalType.EXIT_LONG,
                symbol=symbol,
                price=close,
                timestamp=self.dates[-1],
                reason=f"突破上轨：{close:.2f} > {upper:.2f}"
            ))
        
        return signals


# 策略注册表
STRATEGY_REGISTRY = {
    'dual_ma': DualMovingAverageStrategy,
    'rsi': RSIStrategy,
    'bollinger': BollingerBandsStrategy,
}


def get_strategy_class(strategy_name: str):
    """获取策略类"""
    if strategy_name not in STRATEGY_REGISTRY:
        raise ValueError(f"未知策略：{strategy_name}. 可用策略：{list(STRATEGY_REGISTRY.keys())}")
    return STRATEGY_REGISTRY[strategy_name]

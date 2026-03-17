"""
Backtest Module - 回测模块
"""
from .models import (
    StrategyConfig, TradingSignal, SignalType, Order, OrderSide, OrderStatus,
    Trade, Position, Portfolio, BacktestReport, PerformanceMetrics,
    BacktestRequest, BacktestResponse
)
from .engine import BacktestEngine, BaseStrategy
from .strategies import (
    DualMovingAverageStrategy, RSIStrategy, BollingerBandsStrategy,
    get_strategy_class, STRATEGY_REGISTRY
)

__all__ = [
    # 模型
    'StrategyConfig', 'TradingSignal', 'SignalType', 'Order', 'OrderSide', 'OrderStatus',
    'Trade', 'Position', 'Portfolio', 'BacktestReport', 'PerformanceMetrics',
    'BacktestRequest', 'BacktestResponse',
    
    # 引擎
    'BacktestEngine', 'BaseStrategy',
    
    # 策略
    'DualMovingAverageStrategy', 'RSIStrategy', 'BollingerBandsStrategy',
    'get_strategy_class', 'STRATEGY_REGISTRY',
]

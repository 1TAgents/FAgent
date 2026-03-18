"""
股票策略模块
"""
from .registry import registry
from .dual_ma import StockDualMAStrategy
from .rsi import StockRSIStrategy

# 注册策略
registry.register(
    'dual_ma',
    StockDualMAStrategy,
    {
        'name': '双均线策略',
        'description': '经典趋势跟踪策略，基于短期均线和长期均线的交叉信号',
        'params': {
            'short_period': {'default': 5, 'description': '短期均线周期'},
            'long_period': {'default': 20, 'description': '长期均线周期'},
        },
    }
)

registry.register(
    'rsi',
    StockRSIStrategy,
    {
        'name': 'RSI 策略',
        'description': '基于 RSI 超买超卖的震荡策略',
        'params': {
            'rsi_period': {'default': 14, 'description': 'RSI 周期'},
            'oversold': {'default': 30, 'description': '超卖阈值'},
            'overbought': {'default': 70, 'description': '超买阈值'},
        },
    }
)

def get_strategy(strategy_id: str):
    """获取策略类"""
    return registry.get_strategy(strategy_id)

def list_strategies():
    """获取策略列表"""
    return registry.list_strategies()

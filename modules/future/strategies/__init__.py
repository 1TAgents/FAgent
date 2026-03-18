"""
期货策略模块
"""
from .registry import registry
from .dual_ma import FutureDualMAStrategy
from .rsi import FutureRSIStrategy

# 注册策略
registry.register(
    'future_dual_ma',
    FutureDualMAStrategy,
    {
        'name': '期货双均线策略',
        'description': '支持做多和做空的双均线策略',
        'params': {
            'short_period': {'default': 10, 'description': '短期均线周期'},
            'long_period': {'default': 30, 'description': '长期均线周期'},
            'allow_short': {'default': True, 'description': '允许做空'},
        },
    }
)

registry.register(
    'future_rsi',
    FutureRSIStrategy,
    {
        'name': '期货 RSI 策略',
        'description': '基于 RSI 超买超卖的震荡策略，支持双向交易',
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

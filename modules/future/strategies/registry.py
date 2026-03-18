"""
期货策略注册表
"""
from typing import Dict, List, Any, Type


class StrategyRegistry:
    """期货策略注册表"""
    
    _strategies: Dict[str, Dict[str, Any]] = {}
    
    @classmethod
    def register(cls, strategy_id: str, strategy_class: Type, metadata: Dict[str, Any]):
        """注册策略"""
        cls._strategies[strategy_id] = {
            'class': strategy_class,
            'metadata': metadata,
        }
    
    @classmethod
    def get_strategy(cls, strategy_id: str) -> Type:
        """获取策略类"""
        if strategy_id not in cls._strategies:
            raise ValueError(f"策略不存在：{strategy_id}")
        return cls._strategies[strategy_id]['class']
    
    @classmethod
    def list_strategies(cls) -> List[Dict[str, Any]]:
        """获取策略列表"""
        return [
            {
                'id': strategy_id,
                **info['metadata']
            }
            for strategy_id, info in cls._strategies.items()
        ]


# 全局实例
registry = StrategyRegistry()

"""
SubAgents - 子智能体

各领域专业智能体：
- base: SubAgent 基类
- chat_subagent: 通用对话（兜底）
- market_agent: 行情查询、K线分析
- strategy_agent: 策略生成、参数优化（未来）
- backtest_agent: 策略回测（未来）
- trading_agent: 交易执行（未来）
"""

from .base import BaseSubAgent
from .chat_subagent import ChatSubAgent, chat_subagent
from .market_agent import MarketSubAgent, market_subagent

__all__ = [
    "BaseSubAgent",
    "ChatSubAgent",
    "chat_subagent",
    "MarketSubAgent",
    "market_subagent",
]


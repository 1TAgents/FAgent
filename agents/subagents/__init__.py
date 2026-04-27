"""
SubAgents - 子智能体

各领域专业智能体：
- base: SubAgent 基类
- chat_subagent: 通用对话（兜底）
- market_agent: 行情查询、K线分析
- strategy_subagent: 策略问答/推荐（占位骨架）
- backtest_subagent: 回测/优化（占位骨架）
- trade_subagent: 交易执行（占位骨架）
"""

from .base import BaseSubAgent

__all__ = [
    "BaseSubAgent",
    "ChatSubAgent",
    "chat_subagent",
    "MarketSubAgent",
    "market_subagent",
    "StrategySubAgent",
    "strategy_subagent",
    "BacktestSubAgent",
    "backtest_subagent",
    "TradeSubAgent",
    "trade_subagent",
]


def __getattr__(name):
    if name in {"ChatSubAgent", "chat_subagent"}:
        from .chat_subagent import ChatSubAgent, chat_subagent

        exports = {
            "ChatSubAgent": ChatSubAgent,
            "chat_subagent": chat_subagent,
        }
        return exports[name]

    if name in {"MarketSubAgent", "market_subagent"}:
        from .market_agent import MarketSubAgent, market_subagent

        exports = {
            "MarketSubAgent": MarketSubAgent,
            "market_subagent": market_subagent,
        }
        return exports[name]

    if name in {"StrategySubAgent", "strategy_subagent"}:
        from .strategy_subagent import StrategySubAgent, strategy_subagent

        exports = {
            "StrategySubAgent": StrategySubAgent,
            "strategy_subagent": strategy_subagent,
        }
        return exports[name]

    if name in {"BacktestSubAgent", "backtest_subagent"}:
        from .backtest_subagent import BacktestSubAgent, backtest_subagent

        exports = {
            "BacktestSubAgent": BacktestSubAgent,
            "backtest_subagent": backtest_subagent,
        }
        return exports[name]

    if name in {"TradeSubAgent", "trade_subagent"}:
        from .trade_subagent import TradeSubAgent, trade_subagent

        exports = {
            "TradeSubAgent": TradeSubAgent,
            "trade_subagent": trade_subagent,
        }
        return exports[name]

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

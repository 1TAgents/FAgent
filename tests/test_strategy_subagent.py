import asyncio

from agents.router.models import TaskContext, TaskType
from agents.subagents.strategy_subagent import StrategySubAgent


class FakeMCP:
    async def list_backtest_strategies(self):
        return {
            "strategies": {
                "dual_ma": {
                    "name": "DualMovingAverageStrategy",
                    "description": "双均线交叉策略",
                },
                "custom": {
                    "name": "CustomStrategy",
                    "description": "测试策略",
                },
            }
        }


def test_list_strategies_returns_catalog_and_tool_items():
    agent = StrategySubAgent()
    agent.mcp = FakeMCP()
    context = TaskContext(
        task_type=TaskType.LIST_STRATEGIES,
        query="有哪些策略可以用",
    )

    content = asyncio.run(agent.process(context))

    assert "当前可用策略" in content
    assert "`dual_ma`" in content
    assert "双均线策略" in content
    assert "`rsi`" in content
    assert "`custom`" in content
    assert "默认参数" in content


def test_strategy_qa_explains_strategy_template():
    agent = StrategySubAgent()
    agent.mcp = FakeMCP()
    context = TaskContext(
        task_type=TaskType.STRATEGY_QA,
        query="解释一下 RSI 策略",
        params={"strategy_name": "rsi"},
    )

    content = asyncio.run(agent.process(context))

    assert "RSI 策略" in content
    assert "strategy_name" in content
    assert "`rsi`" in content
    assert "`period`" in content
    assert "主要风险" in content

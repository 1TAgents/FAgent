import asyncio

from agents.router.models import TaskContext, TaskType
from agents.subagents.backtest_subagent import BacktestSubAgent


class FakeMCP:
    def __init__(self):
        self.calls = []

    async def grid_search(self, **kwargs):
        self.calls.append(kwargs)
        return {
            "success": True,
            "best_params": {"short_period": 5, "long_period": 30},
            "best_performance": {
                "sharpe_ratio": 1.23,
                "total_returns": "12.30%",
                "max_drawdown": "-4.50%",
            },
            "total_combinations": 6,
            "elapsed_seconds": 0.12,
            "top_results": [
                {
                    "params": {"short_period": 5, "long_period": 30},
                    "sharpe": 1.23,
                    "returns": 0.123,
                    "max_drawdown": -0.045,
                }
            ],
        }


def test_optimize_backtest_calls_grid_search_with_inferred_grid():
    agent = BacktestSubAgent()
    agent.mcp = FakeMCP()
    context = TaskContext(
        task_type=TaskType.OPTIMIZE_BACKTEST,
        query="帮我优化双均线，短均线3到5，长均线20到30",
        params={
            "strategy_name": "dual_ma",
            "symbol": "600519",
            "start_date": "2025-01-01",
            "end_date": "2025-12-31",
            "initial_capital": 100000,
        },
    )

    content = asyncio.run(agent.process(context))

    assert "已完成 `双均线策略`" in content
    assert "最优参数" in content
    assert "过拟合" in content
    assert agent.mcp.calls[0]["strategy_name"] == "dual_ma"
    assert agent.mcp.calls[0]["symbol"] == "600519"
    assert agent.mcp.calls[0]["param_grid"] == {
        "short_period": [3, 4, 5],
        "long_period": [20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30],
    }


def test_optimize_backtest_prefers_explicit_param_grid():
    agent = BacktestSubAgent()
    agent.mcp = FakeMCP()
    context = TaskContext(
        task_type=TaskType.OPTIMIZE_BACKTEST,
        query="优化 RSI",
        params={
            "strategy_name": "rsi",
            "symbol": "000001",
            "start_date": "2025-01-01",
            "end_date": "2025-12-31",
            "param_grid": {"period": [6, 14], "oversold": 30},
        },
    )

    asyncio.run(agent.process(context))

    assert agent.mcp.calls[0]["param_grid"] == {
        "period": [6, 14],
        "oversold": [30],
    }

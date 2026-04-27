"""
Backtest SubAgent - 回测子智能体

当前阶段先提供统一入口和占位响应，后续逐步接入真实回测工具。
"""
import time
from typing import AsyncIterator

from .base import BaseSubAgent
from ..router.models import TaskContext, TaskType
from ..core.logging import log_subagent


class BacktestSubAgent(BaseSubAgent):
    """回测相关任务的占位子智能体。"""

    name = "backtest"

    async def process_stream(self, context: TaskContext) -> AsyncIterator[str]:
        start_time = time.time()
        log_subagent.start("BacktestSubAgent", context.task_type.value, context)

        yield self._build_placeholder_response(context)

        log_subagent.done("BacktestSubAgent", time.time() - start_time)

    async def process(self, context: TaskContext) -> str:
        return self._build_placeholder_response(context)

    def _build_placeholder_response(self, context: TaskContext) -> str:
        if context.task_type == TaskType.OPTIMIZE_BACKTEST:
            return (
                "BacktestSubAgent 已预留到主聊天链路，但参数优化和网格搜索工具还未接入。"
                " 当前先保留统一入口，后续再补执行能力和结果分析。"
            )

        if context.task_type == TaskType.RUN_BACKTEST:
            return (
                "BacktestSubAgent 已接入路由，但真实回测执行能力还未实现。"
                " 当前先保留统一入口，后续会逐步接入回测运行、结果汇总和指标解读。"
            )

        return (
            "BacktestSubAgent 已接入路由，但回测相关工具还未接入。"
            " 当前可以先用这个入口收口回测类请求，后续逐步补齐执行和分析能力。"
        )


backtest_subagent = BacktestSubAgent()

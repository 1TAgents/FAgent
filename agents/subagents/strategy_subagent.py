"""
Strategy SubAgent - 策略子智能体

当前阶段先提供统一入口和占位响应，后续逐步接入真实策略工具。
"""
import time
from typing import AsyncIterator

from .base import BaseSubAgent
from ..router.models import TaskContext, TaskType
from ..core.logging import log_subagent


class StrategySubAgent(BaseSubAgent):
    """策略相关任务的占位子智能体。"""

    name = "strategy"

    async def process_stream(self, context: TaskContext) -> AsyncIterator[str]:
        start_time = time.time()
        log_subagent.start("StrategySubAgent", context.task_type.value, context)

        yield self._build_placeholder_response(context)

        log_subagent.done("StrategySubAgent", time.time() - start_time)

    async def process(self, context: TaskContext) -> str:
        return self._build_placeholder_response(context)

    def _build_placeholder_response(self, context: TaskContext) -> str:
        if context.task_type == TaskType.LIST_STRATEGIES:
            return (
                "StrategySubAgent 已预留到主聊天链路，但策略列表工具还未接入。"
                " 当前先保留统一入口，后续会逐步补上策略清单、策略说明和参数模板。"
            )

        return (
            "StrategySubAgent 已接入路由，但真实策略能力还未实现。"
            " 当前可以先保留这类请求的统一入口，后续逐步补充策略推荐、策略比较和参数配置工具。"
        )


strategy_subagent = StrategySubAgent()

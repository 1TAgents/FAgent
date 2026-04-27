"""
Trade SubAgent - 交易子智能体

当前阶段先提供统一入口和占位响应，后续逐步接入真实交易或仿真交易工具。
"""
import time
from typing import AsyncIterator

from .base import BaseSubAgent
from ..router.models import TaskContext, TaskType
from ..core.logging import log_subagent


class TradeSubAgent(BaseSubAgent):
    """交易相关任务的占位子智能体。"""

    name = "trade"

    async def process_stream(self, context: TaskContext) -> AsyncIterator[str]:
        start_time = time.time()
        log_subagent.start("TradeSubAgent", context.task_type.value, context)

        yield self._build_placeholder_response(context)

        log_subagent.done("TradeSubAgent", time.time() - start_time)

    async def process(self, context: TaskContext) -> str:
        return self._build_placeholder_response(context)

    def _build_placeholder_response(self, context: TaskContext) -> str:
        if context.task_type == TaskType.PLACE_ORDER:
            return (
                "TradeSubAgent 已预留到主聊天链路，但还没有接入真实下单或仿真交易接口。"
                " 当前不会执行买卖动作，后续再补券商/模拟盘接入和风控确认。"
            )

        if context.task_type == TaskType.CANCEL_ORDER:
            return (
                "TradeSubAgent 已预留到主聊天链路，但撤单接口还未接入。"
                " 当前先保留统一入口，后续再补订单查询和撤单执行。"
            )

        if context.task_type == TaskType.CHECK_POSITIONS:
            return (
                "TradeSubAgent 已预留到主聊天链路，但持仓和订单查询接口还未接入。"
                " 当前先保留统一入口，后续再补账户、持仓和成交查询。"
            )

        return (
            "TradeSubAgent 已接入路由，但真实交易能力还未实现。"
            " 当前可以先收口交易类问题，后续再逐步接入下单、撤单、持仓和风控能力。"
        )


trade_subagent = TradeSubAgent()

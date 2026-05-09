"""
ReAct Router - 基于 ReAct 循环的主路由

替代传统 SubAgent 硬编码分发，让 LLM 自主决策工具调用。

流程：
1. Router 分析意图 → 确定 route type
2. 根据 route type 选择工具集和 system prompt
3. ReActAgentLoop 执行：LLM 自主决定调用哪些工具
4. 返回最终结果 + 执行轨迹

相比传统路由的优势：
- LLM 可以组合多个工具（如先 search_stock 再 get_quote）
- 不需要为每种任务类型写独立的 SubAgent
- 工具调用参数由 LLM 生成，不需要 Router 提取
"""
from __future__ import annotations

import time
import logging
from typing import AsyncIterator, List, Optional

from .models import TaskContext, RouteType
from ..services.llm import llm_service
from ..tools.registry import ToolRegistry, tool_registry
from ..tools.builtin import register_builtin_tools
from ..tools.builtin.market import get_market_tools
from ..react.loop import ReActAgentLoop, ReActResult
from ..core.logging import log_router, log_subagent
from ..core.prompt_builder import prompt_builder

logger = logging.getLogger(__name__)


# 路由类型对应的工具集选择
ROUTE_TOOLS: dict[RouteType, list] = {
    RouteType.MARKET: get_market_tools,
    RouteType.CHAT: lambda: [],
    RouteType.STRATEGY: lambda: [],  # 策略问答暂不需要工具
    RouteType.BACKTEST: lambda: [],   # 回测暂不需要工具
    RouteType.TRADE: lambda: [],      # 交易暂不需要工具
    RouteType.NEWS: lambda: [],       # 新闻暂不需要工具
}


class ReActRouter:
    """基于 ReAct 循环的路由器。"""

    def __init__(self):
        # 注册内置工具到全局 registry
        register_builtin_tools(tool_registry)

    def _get_tools_for_route(self, route: RouteType) -> list:
        """获取指定路由的工具集。"""
        factory = ROUTE_TOOLS.get(route, lambda: [])
        return factory()

    async def process_stream(
        self,
        route: RouteType,
        context: TaskContext,
        history: Optional[List[dict]] = None,
    ) -> AsyncIterator[str]:
        """流式处理（主入口）。

        Args:
            route: 路由类型（由 Router 决策得出）
            context: 任务上下文
            history: 对话历史消息列表

        Yields:
            流式文本片段
        """
        start_time = time.time()
        log_router.dispatch(
            f"ReAct({route.value})",
            context.task_type.value,
        )

        # 构建工具集
        tools = self._get_tools_for_route(route)

        # 构建系统提示词
        system_prompt = prompt_builder.build(
            route=route.value,
            tool_schemas=[t.schema for t in tools] if tools else None,
        )

        # 创建 ReAct 循环
        loop = ReActAgentLoop(
            llm_service=llm_service,
            system_prompt=system_prompt,
            registry=tool_registry if tools else None,
            max_turns=8,
            model=context.model,
            use_memory=True,
        )

        # 执行 ReAct 循环
        async for chunk in loop.run_stream(context.query, history):
            yield chunk

        duration = time.time() - start_time
        log_router.done(
            cid=context.cid or 0,
            duration=duration,
            route=route.value,
        )

    async def process(
        self,
        route: RouteType,
        context: TaskContext,
        history: Optional[List[dict]] = None,
    ) -> str:
        """非流式处理。"""
        result = ""
        async for chunk in self.process_stream(route, context, history):
            result += chunk
        return result


# 全局实例
react_router = ReActRouter()

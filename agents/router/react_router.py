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

import asyncio

from .models import TaskContext, RouteType
from ..services.llm import llm_service
from ..services.memory_extractor import memory_extractor
from ..tools.registry import ToolRegistry, tool_registry
from ..tools.builtin import register_builtin_tools
from ..tools.builtin.market import get_market_tools
from ..tools.builtin.backtest import get_backtest_tools
from ..tools.builtin.trading import get_trading_tools
from ..tools.permissions import permissions_for_route
from ..skills.registry import skill_registry
from ..skills.builtin import ALL_BUILTIN_SKILLS
from ..skills.load_skill import get_skill_tools
from ..services.memory_bridge import memory_bridge
from ..react.loop import ReActAgentLoop, ReActResult
from ..core.logging import log_router, log_subagent
from ..core.prompt_builder import prompt_builder
from ..core.tracing import ExecutionTrace
from ..core.session_state import session_state

logger = logging.getLogger(__name__)


# 路由类型对应的工具集选择
ROUTE_TOOLS: dict[RouteType, list] = {
    RouteType.MARKET: get_market_tools,
    RouteType.CHAT: lambda: [],
    RouteType.STRATEGY: lambda: get_backtest_tools()[:2],  # list_strategies + get_strategy_info
    RouteType.BACKTEST: get_backtest_tools,                 # 全部回测工具
    RouteType.TRADE: get_trading_tools,                     # place_order + cancel_order + check_positions
    RouteType.NEWS: lambda: [],
}


class ReActRouter:
    """基于 ReAct 循环的路由器。"""

    def __init__(self):
        # 注册内置工具到全局 registry
        register_builtin_tools(tool_registry)
        # 注册内置技能
        for skill in ALL_BUILTIN_SKILLS:
            skill_registry.register(skill)

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
        cid = context.cid or 0

        # 如果会话已在运行中，拒绝
        if session_state.is_running(cid):
            log_router.fallback(f"Session cid={cid} 已在处理中，拒绝新请求")
            yield "上一条消息仍在处理中，请稍后再试。"
            return

        log_router.dispatch(
            f"ReAct({route.value})",
            context.task_type.value,
        )

        # 启动会话
        session_state.start(cid, context.mid or 0)

        # 构建工具集
        tools = self._get_tools_for_route(route)

        # 注册 load_skill 工具（让 LLM 可以按需加载技能内容）
        skill_tools = get_skill_tools(skill_registry)
        for st in skill_tools:
            tool_registry.register(st)

        # 构建系统提示词（注入技能索引 + 记忆召回）
        skill_index_text = skill_registry.get_index_for_route(route.value)
        memories = memory_bridge.recall_all(limit_per_category=3)
        memory_lines = [e.to_prompt_line() for e in memories] if memories else None
        system_prompt = prompt_builder.build(
            route=route.value,
            tool_schemas=[t.schema for t in tools] if tools else None,
            skill_index=skill_index_text if skill_index_text else None,
            memories=memory_lines,
        )

        # 创建 ExecutionTrace
        import time as _time
        trace = ExecutionTrace(
            trace_id=f"rid_{int(_time.time() * 1000)}",
            cid=cid,
            mid=context.mid or 0,
            user_message=context.original_message or context.query,
            route=route.value,
            task_type=context.task_type.value,
            started_at=time.time(),
        )

        # 根据路由类型设置权限
        permissions = permissions_for_route(route.value)

        # 创建 ReAct 循环
        loop = ReActAgentLoop(
            llm_service=llm_service,
            system_prompt=system_prompt,
            registry=tool_registry,
            max_turns=8,
            model=context.model,
            use_memory=True,
            trace=trace,
            cid=cid,
            permissions=permissions,
        )

        # 执行 ReAct 循环
        full_response = ""
        try:
            async for chunk in loop.run_stream(context.query, history):
                full_response += chunk
                yield chunk
        except Exception as e:
            session_state.set_error(cid)
            raise
        finally:
            if not session_state.is_cancelled(cid):
                session_state.finish(cid)

        # 后台抽取记忆
        if full_response and not session_state.is_cancelled(cid):
            asyncio.create_task(
                memory_extractor.extract_and_store(
                    context.query,
                    full_response,
                    cid=cid,
                ),
            )

        duration = time.time() - start_time
        log_router.done(
            cid=cid,
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

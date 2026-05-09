"""
ReAct Market Agent - 基于 ReAct 循环的行情子智能体

替代原有的 MarketSubAgent 硬编码工具调用，让 LLM 自主决定：
1. 需要调用哪些工具（行情/K线/搜索/趋势分析）
2. 工具调用的参数
3. 如何综合工具结果生成分析

架构对比：
  旧: Router → MarketSubAgent → _execute_task() 硬编码 → LLM 分析
  新: Router → ReActMarketAgent → ReActLoop(LLM 决策工具) → 自动分析
"""
from __future__ import annotations

import sys
import os
import time
from typing import AsyncIterator

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from .base import BaseSubAgent
from ..router.models import TaskContext
from ..react.loop import ReActAgentLoop
from ..tools.builtin import register_builtin_tools
from ..tools.registry import ToolRegistry
from ..core.logging import log_subagent
from ..core.prompt_builder import prompt_builder
from ..services.llm import llm_service


class ReActMarketAgent(BaseSubAgent):
    """基于 ReAct 循环的行情子智能体。

    LLM 自主决定调用哪些工具，而不是硬编码路由。
    """

    name = "react_market"

    def __init__(self):
        super().__init__()
        # 创建专用的工具注册中心（只包含行情工具）
        self.registry = ToolRegistry()
        register_builtin_tools(self.registry)

        log_subagent.start("ReActMarketAgent", "market_react", None)

    async def process_stream(self, context: TaskContext) -> AsyncIterator[str]:
        """流式处理行情任务。"""
        start_time = time.time()

        # 使用 prompt builder 构建系统提示词
        system_prompt = prompt_builder.build(
            route="market",
            tool_schemas=self.registry.get_all_schemas(),
        )

        # 创建 ReAct 循环
        loop = ReActAgentLoop(
            llm_service=llm_service,
            system_prompt=system_prompt,
            registry=self.registry,
            max_turns=8,
            model=context.model,
        )

        # 构建历史消息（从 context 中提取）
        history = []
        if context.context_summary:
            history.append({
                "role": "system",
                "content": f"相关上下文: {context.context_summary}",
            })

        # 执行 ReAct 循环（流式）
        for chunk in loop.run_stream(context.query, history):
            yield chunk

        duration = time.time() - start_time
        log_subagent.done("ReActMarketAgent", duration)

    async def process(self, context: TaskContext) -> str:
        """非流式处理行情任务。"""
        start_time = time.time()

        system_prompt = prompt_builder.build(
            route="market",
            tool_schemas=self.registry.get_all_schemas(),
        )

        loop = ReActAgentLoop(
            llm_service=llm_service,
            system_prompt=system_prompt,
            registry=self.registry,
            max_turns=8,
            model=context.model,
        )

        history = []
        if context.context_summary:
            history.append({
                "role": "system",
                "content": f"相关上下文: {context.context_summary}",
            })

        result = loop.run(context.query, history)
        duration = time.time() - start_time
        log_subagent.done("ReActMarketAgent", duration)
        return result.content


# 全局实例
react_market_agent = ReActMarketAgent()

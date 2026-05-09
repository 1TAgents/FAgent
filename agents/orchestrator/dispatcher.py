"""
SubAgent Dispatcher - 并行任务分发

将任务同时分发到多个 SubAgent，等待所有结果返回。
设计参考：Vibe-Trading SwarmRuntime 的 ThreadPoolExecutor 并行层。
"""
from __future__ import annotations

import asyncio
import time
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from ..subagents.base import BaseSubAgent
from ..router.models import TaskContext

logger = logging.getLogger(__name__)


@dataclass
class DispatchResult:
    """单个 SubAgent 的分发结果。"""
    agent_name: str
    success: bool
    content: str = ""
    error: Optional[str] = None
    duration_ms: float = 0.0
    metadata: dict = field(default_factory=dict)

    @property
    def preview(self) -> str:
        return self.content[:200] if self.content else (self.error or "")


class SubAgentDispatcher:
    """子智能体并行分发器。

    用法：
        dispatcher = SubAgentDispatcher()
        dispatcher.register("market", market_subagent)
        dispatcher.register("strategy", strategy_subagent)
        results = await dispatcher.dispatch(context, ["market", "strategy"])
    """

    def __init__(self, timeout: float = 30.0):
        """
        Args:
            timeout: 单个 SubAgent 超时时间（秒）
        """
        self._agents: Dict[str, BaseSubAgent] = {}
        self.timeout = timeout

    def register(self, name: str, agent: BaseSubAgent) -> None:
        """注册 SubAgent。"""
        self._agents[name] = agent
        logger.debug(f"注册 SubAgent: {name}")

    def unregister(self, name: str) -> Optional[BaseSubAgent]:
        """注销 SubAgent。"""
        return self._agents.pop(name, None)

    @property
    def registered_agents(self) -> List[str]:
        return list(self._agents.keys())

    async def dispatch(
        self,
        context: TaskContext,
        targets: List[str],
    ) -> List[DispatchResult]:
        """并行分发到多个 SubAgent。

        Args:
            context: 任务上下文
            targets: 目标 SubAgent 名称列表

        Returns:
            DispatchResult 列表（按 targets 顺序）
        """
        if not targets:
            return []

        # 构建协程列表
        tasks = []
        for name in targets:
            agent = self._agents.get(name)
            if agent is None:
                tasks.append(self._missing_agent(name))
            else:
                tasks.append(self._dispatch_one(name, agent, context))

        # 并行执行
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 处理异常
        processed = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed.append(DispatchResult(
                    agent_name=targets[i],
                    success=False,
                    error=str(result),
                ))
            else:
                processed.append(result)

        return processed

    async def dispatch_first(
        self,
        context: TaskContext,
        targets: List[str],
    ) -> DispatchResult:
        """分发到多个 SubAgent，返回第一个成功的结果。

        按 targets 顺序尝试，遇到成功即返回。
        """
        for name in targets:
            agent = self._agents.get(name)
            if agent is None:
                continue
            result = await self._dispatch_one(name, agent, context)
            if result.success:
                return result
        return DispatchResult(
            agent_name="none",
            success=False,
            error=f"所有 SubAgent 均失败: {targets}",
        )

    async def _dispatch_one(
        self,
        name: str,
        agent: BaseSubAgent,
        context: TaskContext,
    ) -> DispatchResult:
        """分发到单个 SubAgent。"""
        start = time.monotonic()
        try:
            result = await asyncio.wait_for(
                agent.process(context),
                timeout=self.timeout,
            )
            duration = (time.monotonic() - start) * 1000
            return DispatchResult(
                agent_name=name,
                success=True,
                content=result,
                duration_ms=duration,
            )
        except asyncio.TimeoutError:
            duration = (time.monotonic() - start) * 1000
            logger.warning(f"SubAgent {name} 超时 ({self.timeout}s)")
            return DispatchResult(
                agent_name=name,
                success=False,
                error=f"超时 ({self.timeout}s)",
                duration_ms=duration,
            )
        except Exception as e:
            duration = (time.monotonic() - start) * 1000
            logger.error(f"SubAgent {name} 异常: {e}")
            return DispatchResult(
                agent_name=name,
                success=False,
                error=str(e),
                duration_ms=duration,
            )

    async def _missing_agent(self, name: str) -> DispatchResult:
        """处理未注册的 SubAgent。"""
        return DispatchResult(
            agent_name=name,
            success=False,
            error=f"SubAgent 未注册: {name}",
        )

"""
SystemPromptBuilder - 系统提示词构建器

按需组合系统提示词的不同部分：
- 基础角色（身份 + 行为准则）
- 路由场景模板（market/strategy/backtest/trade/chat）
- 工具上下文（可用工具摘要）
- 记忆召回（用户偏好、项目上下文）

使用场景：
- SubAgent 初始化时构建系统提示
- Router 决策时构建路由提示
- 未来支持动态技能/工具注入时使用
"""
from __future__ import annotations

from typing import List, Optional

from .prompts import (
    AGENT_IDENTITY,
    AGENT_BEHAVIOR,
    ROUTE_PROMPTS,
    ROUTER_SYSTEM_PROMPT,
    SUMMARY_SYSTEM_PROMPT,
)


class SystemPromptBuilder:
    """系统提示词构建器。

    按需组合提示词的不同部分，支持模板变量替换。
    """

    def __init__(self):
        self._base_identity = AGENT_IDENTITY.strip()
        self._base_behavior = AGENT_BEHAVIOR.strip()
        self._route_prompts = {
            k: v.strip() for k, v in ROUTE_PROMPTS.items()
        }

    def for_route(self, route: str) -> str:
        """获取指定路由的系统提示词。"""
        return self._route_prompts.get(route, self.default())

    def for_router(self) -> str:
        """Router 专用的系统提示词。"""
        return ROUTER_SYSTEM_PROMPT.strip()

    def for_summary(self) -> str:
        """会话总结/标题生成专用的系统提示词。"""
        return SUMMARY_SYSTEM_PROMPT.strip()

    def default(self) -> str:
        """默认系统提示词（chat 场景）。"""
        return self._route_prompts.get("chat", "")

    def with_tools(self, base_prompt: str, tool_schemas: List[dict]) -> str:
        """在系统提示词中添加工具描述。

        Args:
            base_prompt: 基础系统提示词
            tool_schemas: 工具 schema 列表

        Returns:
            添加了工具描述的完整提示词
        """
        if not tool_schemas:
            return base_prompt

        lines = ["\n【可用工具】"]
        for schema in tool_schemas:
            name = schema.get("name", "unknown")
            desc = schema.get("description", "")
            lines.append(f"- {name}: {desc}")
        lines.append("")

        return base_prompt + "\n" + "\n".join(lines)

    def with_memory(self, base_prompt: str, memories: Optional[List[str]] = None) -> str:
        """在系统提示词中添加记忆上下文。

        Args:
            base_prompt: 基础系统提示词
            memories: 记忆条目列表

        Returns:
            添加了记忆的完整提示词
        """
        if not memories:
            return base_prompt

        lines = ["\n【上下文记忆】"]
        lines.extend(memories)
        lines.append("")

        return base_prompt + "\n" + "\n".join(lines)

    def build(
        self,
        route: Optional[str] = None,
        tool_schemas: Optional[List[dict]] = None,
        memories: Optional[List[str]] = None,
        skill_index: Optional[str] = None,
    ) -> str:
        """一站式构建完整系统提示词。

        Args:
            route: 路由类型（market/strategy/backtest/trade/chat）
            tool_schemas: 工具 schema 列表
            memories: 记忆上下文
            skill_index: 技能索引文本（由 SkillRegistry 生成）

        Returns:
            完整的系统提示词
        """
        if route:
            prompt = self.for_route(route)
        else:
            prompt = self.default()

        if skill_index:
            prompt = prompt + "\n" + skill_index

        if tool_schemas:
            prompt = self.with_tools(prompt, tool_schemas)

        if memories:
            prompt = self.with_memory(prompt, memories)

        return prompt


# 全局单例
prompt_builder = SystemPromptBuilder()

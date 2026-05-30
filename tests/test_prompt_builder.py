"""
Prompt Builder 测试
"""
import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from agents.core.prompt_builder import SystemPromptBuilder
from agents.core.prompts import (
    ROUTER_SYSTEM_PROMPT,
    SUMMARY_SYSTEM_PROMPT,
    ROUTE_PROMPTS,
)


class TestSystemPromptBuilder:
    def test_for_route_returns_correct_prompt(self):
        builder = SystemPromptBuilder()
        for route, prompt in ROUTE_PROMPTS.items():
            result = builder.for_route(route)
            assert result.strip() == prompt.strip()

    def test_for_route_unknown_returns_default(self):
        builder = SystemPromptBuilder()
        result = builder.for_route("unknown_route")
        assert result == builder.default()

    def test_for_router(self):
        builder = SystemPromptBuilder()
        result = builder.for_router()
        assert "任务路由器" in result
        assert "market" in result
        assert "chat" in result
        assert "describe_self" in result

    def test_for_summary(self):
        builder = SystemPromptBuilder()
        result = builder.for_summary()
        assert "标题" in result

    def test_default_is_chat_prompt(self):
        builder = SystemPromptBuilder()
        assert builder.default() == builder.for_route("chat")

    def test_with_tools_appends_tool_list(self):
        builder = SystemPromptBuilder()
        base = "你是助手。"
        tools = [
            {"name": "get_quote", "description": "查行情"},
            {"name": "search_stock", "description": "搜股票"},
        ]
        result = builder.with_tools(base, tools)
        assert "【可用工具】" in result
        assert "get_quote" in result
        assert "查行情" in result
        assert "search_stock" in result

    def test_with_tools_empty_returns_base(self):
        builder = SystemPromptBuilder()
        base = "你是助手。"
        result = builder.with_tools(base, [])
        assert result == base

    def test_with_memory_appends_memories(self):
        builder = SystemPromptBuilder()
        base = "你是助手。"
        memories = ["用户偏好A股", "关注科技股"]
        result = builder.with_memory(base, memories)
        assert "【上下文记忆】" in result
        assert "A股" in result
        assert "科技股" in result

    def test_with_memory_empty_returns_base(self):
        builder = SystemPromptBuilder()
        base = "你是助手。"
        assert builder.with_memory(base, None) == base
        assert builder.with_memory(base, []) == base

    def test_build_combines_all_parts(self):
        builder = SystemPromptBuilder()
        result = builder.build(
            route="market",
            tool_schemas=[{"name": "get_quote", "description": "查行情"}],
            memories=["用户偏好科技股"],
        )
        assert "股票分析师" in result  # market prompt
        assert "【可用工具】" in result
        assert "get_quote" in result
        assert "【上下文记忆】" in result
        assert "科技股" in result

    def test_build_route_only(self):
        builder = SystemPromptBuilder()
        result = builder.build(route="chat")
        assert result == builder.for_route("chat")

    def test_build_no_args(self):
        builder = SystemPromptBuilder()
        result = builder.build()
        assert result == builder.default()

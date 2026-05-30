"""
ReAct Router 测试
"""
import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from agents.router.react_router import ReActRouter, ROUTE_TOOLS
from agents.router.models import RouteType, TaskContext, TaskType
from agents.tools.registry import tool_registry


class TestReActRouter:
    def test_route_tools_mapping(self):
        """验证每个路由类型都有对应的工具集。"""
        for route in RouteType:
            assert route in ROUTE_TOOLS, f"Missing tools for route: {route}"

    def test_market_route_has_tools(self):
        """验证 market 路由有行情工具。"""
        tools = ROUTE_TOOLS[RouteType.MARKET]()
        assert len(tools) > 0
        tool_names = [t.name for t in tools]
        assert "get_quote" in tool_names

    def test_chat_route_has_self_info_tool(self):
        """验证 chat 路由包含 FAgent 自我介绍工具。"""
        tools = ROUTE_TOOLS[RouteType.CHAT]()
        tool_names = [t.name for t in tools]
        assert tool_names == ["describe_fagent"]

    def test_registry_has_market_tools(self):
        """验证工具注册中心包含行情工具。"""
        from agents.tools.builtin import register_builtin_tools
        register_builtin_tools(tool_registry)
        assert tool_registry.has("get_quote")
        assert tool_registry.has("get_kline")
        assert tool_registry.has("search_stock")
        assert tool_registry.has("describe_fagent")

    def test_react_router_init(self):
        router = ReActRouter()
        assert router is not None

    def test_get_tools_for_route(self):
        router = ReActRouter()
        tools = router._get_tools_for_route(RouteType.MARKET)
        assert len(tools) > 0

    def test_context_for_react(self):
        """验证 TaskContext 可以正确传递给 ReAct 路由。"""
        ctx = TaskContext(
            task_type=TaskType.GET_QUOTE,
            query="茅台股价",
            params={"symbol": "600519"},
            model="qwen3.5-plus",
        )
        assert ctx.task_type == TaskType.GET_QUOTE
        assert ctx.params["symbol"] == "600519"

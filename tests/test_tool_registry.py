"""
Tool Registry Tests

验证工具注册、查询、schema 生成和执行的基本功能。
"""
import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from agents.tools import BaseTool, ToolRegistry, ToolResult
from agents.tools.builtin import (
    GetQuoteTool,
    GetKLineTool,
    SearchStockTool,
    AnalyzeTrendTool,
    register_builtin_tools,
)


@pytest.fixture(autouse=True)
def reset_registry():
    """每个测试前重置 registry 单例。"""
    ToolRegistry.reset()
    yield


class TestToolResult:
    def test_ok_factory(self):
        r = ToolResult.ok("test", data={"x": 1}, text="ok")
        assert r.success
        assert r.tool_name == "test"
        assert r.data == {"x": 1}
        assert r.text == "ok"
        assert r.error is None

    def test_fail_factory(self):
        r = ToolResult.fail("test", error="boom")
        assert not r.success
        assert r.tool_name == "test"
        assert r.error == "boom"

    def test_to_llm_content_success(self):
        r = ToolResult.ok("test", data={"a": 1}, text="result here")
        assert r.to_llm_content() == "result here"

    def test_to_llm_content_fallback_data(self):
        r = ToolResult.ok("test", data={"a": 1})
        assert r.to_llm_content() == "{'a': 1}"

    def test_to_llm_content_failure(self):
        r = ToolResult.fail("test", error="timeout")
        assert "timeout" in r.to_llm_content()

    def test_to_dict_success(self):
        r = ToolResult.ok("test", data={"x": 1}, text="ok")
        d = r.to_dict()
        assert d["success"] is True
        assert d["data"] == {"x": 1}
        assert "error" not in d

    def test_to_dict_failure(self):
        r = ToolResult.fail("test", error="nope")
        d = r.to_dict()
        assert d["success"] is False
        assert d["error"] == "nope"
        assert "data" not in d


class TestBaseTool:
    def test_schema_generation(self):
        tool = GetQuoteTool()
        schema = tool.schema
        assert schema["name"] == "get_quote"
        assert "description" in schema
        assert "parameters" in schema
        assert "symbol" in schema["parameters"]["properties"]

    def test_param_validation_required(self):
        tool = GetQuoteTool()
        valid, err = tool.validate_params({})
        assert not valid
        assert "symbol" in err

    def test_param_validation_pass(self):
        tool = GetQuoteTool()
        valid, err = tool.validate_params({"symbol": "600519"})
        assert valid
        assert err is None


class TestToolRegistry:
    def test_register_and_get(self):
        reg = ToolRegistry()
        tool = GetQuoteTool()
        reg.register(tool)
        assert reg.get("get_quote") is tool
        assert reg.has("get_quote")

    def test_register_duplicate_warns(self):
        reg = ToolRegistry()
        reg.register(GetQuoteTool())
        # Re-registering should not raise, and count stays at 1
        reg.register(GetQuoteTool())
        assert reg.count == 1

    def test_unregister(self):
        reg = ToolRegistry()
        reg.register(GetQuoteTool())
        old = reg.unregister("get_quote")
        assert old is not None
        assert not reg.has("get_quote")

    def test_bulk_register(self):
        reg = ToolRegistry()
        tools = [GetQuoteTool(), GetKLineTool(), SearchStockTool(), AnalyzeTrendTool()]
        reg.register_all(tools)
        assert reg.count == 4

    def test_list_by_category(self):
        reg = ToolRegistry()
        register_builtin_tools(reg)
        market_tools = reg.list_by_category("market")
        assert len(market_tools) == 4

    def test_get_all_schemas(self):
        reg = ToolRegistry()
        register_builtin_tools(reg)
        schemas = reg.get_all_schemas()
        assert len(schemas) == 11
        for s in schemas:
            assert "name" in s
            assert "description" in s
            assert "parameters" in s

    def test_summary(self):
        reg = ToolRegistry()
        register_builtin_tools(reg)
        summary = reg.summary()
        assert summary["total"] == 11
        assert "market" in summary["categories"]
        assert "backtest" in summary["categories"]
        assert "trading" in summary["categories"]

    def test_repr(self):
        reg = ToolRegistry()
        reg.register(GetQuoteTool())
        r = repr(reg)
        assert "ToolRegistry" in r
        assert "tools=1" in r


class TestBuiltinTools:
    def test_all_tools_registered(self):
        reg = ToolRegistry()
        register_builtin_tools(reg)
        assert reg.count == 11
        assert reg.has("get_quote")
        assert reg.has("get_kline")
        assert reg.has("search_stock")
        assert reg.has("analyze_trend")
        assert reg.has("list_strategies")
        assert reg.has("get_strategy_info")
        assert reg.has("run_backtest")
        assert reg.has("optimize_backtest")
        assert reg.has("place_order")
        assert reg.has("cancel_order")
        assert reg.has("check_positions")

    def test_tool_repr(self):
        tool = GetQuoteTool()
        assert "get_quote" in repr(tool)
        assert "market" in repr(tool)

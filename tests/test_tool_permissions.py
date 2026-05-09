"""
Tool Permissions 测试
"""
import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from agents.tools.permissions import ToolPermissions, permissions_for_route
from agents.tools.base import DangerLevel


class TestToolPermissions:
    def test_default_allows_read_only(self):
        p = ToolPermissions(max_danger_level=DangerLevel.READ_ONLY)
        assert p.is_allowed("get_quote", DangerLevel.READ_ONLY)
        assert not p.is_allowed("get_kline", DangerLevel.WRITE)

    def test_deny_list_overrides(self):
        p = ToolPermissions(
            max_danger_level=DangerLevel.TRADE,
            denied={"place_order"},
        )
        assert p.is_allowed("get_quote", DangerLevel.READ_ONLY)
        assert not p.is_allowed("place_order", DangerLevel.TRADE)

    def test_allow_list_overrides_danger_level(self):
        p = ToolPermissions(
            max_danger_level=DangerLevel.READ_ONLY,
            allowed={"analyze_trend"},
        )
        assert p.is_allowed("analyze_trend", DangerLevel.EXECUTE)

    def test_deny_reason(self):
        p = ToolPermissions(max_danger_level=DangerLevel.READ_ONLY)
        reason = p.deny_reason("place_order", DangerLevel.TRADE)
        assert "trade" in reason.lower() or "超过" in reason

    def test_clone(self):
        p = ToolPermissions(
            max_danger_level=DangerLevel.WRITE,
            allowed={"tool_a"},
            denied={"tool_b"},
        )
        clone = p.clone()
        assert clone.max_danger_level == p.max_danger_level
        assert clone.allowed == p.allowed
        assert clone.denied == p.denied
        # Ensure independence
        clone.allowed.add("tool_c")
        assert "tool_c" not in p.allowed


class TestPermissionsForRoute:
    def test_chat_is_read_only(self):
        p = permissions_for_route("chat")
        assert p.max_danger_level == DangerLevel.READ_ONLY

    def test_market_allows_execute(self):
        p = permissions_for_route("market")
        assert p.max_danger_level == DangerLevel.EXECUTE

    def test_trade_allows_all(self):
        p = permissions_for_route("trade")
        assert p.max_danger_level == DangerLevel.TRADE

    def test_unknown_defaults_to_read_only(self):
        p = permissions_for_route("unknown_route")
        assert p.max_danger_level == DangerLevel.READ_ONLY


class TestMarketToolsDangerLevel:
    def test_market_tools_are_read_only(self):
        from agents.tools.builtin.market import (
            GetQuoteTool, GetKLineTool, SearchStockTool, AnalyzeTrendTool,
        )
        assert GetQuoteTool().danger_level == DangerLevel.READ_ONLY
        assert GetKLineTool().danger_level == DangerLevel.READ_ONLY
        assert SearchStockTool().danger_level == DangerLevel.READ_ONLY
        assert AnalyzeTrendTool().danger_level == DangerLevel.READ_ONLY

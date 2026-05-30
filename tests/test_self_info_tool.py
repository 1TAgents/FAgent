import pytest

from agents.core.capabilities import (
    build_fagent_capability_data,
    format_fagent_capabilities,
)
from agents.tools.builtin.self_info import DescribeFAgentTool


def test_capability_data_covers_core_domains():
    data = build_fagent_capability_data()
    group_names = {item["name"] for item in data["capability_groups"]}

    assert "行情与个股分析" in group_names
    assert "量化策略研究" in group_names
    assert "回测与参数优化" in group_names
    assert "本地模拟交易" in group_names
    assert "会话与智能体体验" in group_names
    assert any(item["id"] == "dual_ma" for item in data["strategies"])


def test_format_fagent_capabilities_mentions_limits():
    text = format_fagent_capabilities()

    assert "回测与参数优化" in text
    assert "本地模拟交易" in text
    assert "不会提交真实订单" in text
    assert "用户记忆只作为上下文辅助" in text


@pytest.mark.asyncio
async def test_describe_fagent_tool_returns_authoritative_text():
    result = await DescribeFAgentTool().execute()

    assert result.success
    assert result.tool_name == "describe_fagent"
    assert "当前已接入的核心能力" in result.text
    assert "run_backtest" in result.text
    assert "place_order" in result.text
    assert result.data["identity"].startswith("FAgent")

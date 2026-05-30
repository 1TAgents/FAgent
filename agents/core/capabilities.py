"""Canonical FAgent capability description.

This module is the single source of truth for self-introduction answers. It is
kept separate from prompts so tests and tools can reuse the same capability
map instead of duplicating stale text.
"""
from __future__ import annotations

from typing import Any, Dict, List


FAGENT_IDENTITY = "FAgent 是一个面向股票研究、策略验证和本地模拟交易的智能交易助手。"

FAGENT_CAPABILITY_GROUPS: List[Dict[str, Any]] = [
    {
        "name": "行情与个股分析",
        "summary": "查询股票代码、实时行情、K 线数据，并基于均线做基础趋势判断。",
        "tools": ["search_stock", "get_quote", "get_kline", "analyze_trend"],
        "examples": [
            "帮我查一下贵州茅台的行情",
            "看下 600519 最近一周走势",
            "分析一下平安银行当前趋势",
        ],
    },
    {
        "name": "量化策略研究",
        "summary": "解释、比较和推荐已接入的经典量化策略，覆盖短线、中线和长线场景。",
        "tools": ["list_strategies", "get_strategy_info"],
        "examples": [
            "列出当前支持的策略",
            "均线策略适合什么股票",
            "比较 RSI2 和双均线策略",
        ],
    },
    {
        "name": "回测与参数优化",
        "summary": "对指定股票和策略执行回测，输出收益、回撤、夏普、胜率、交易次数、基准对比等指标，并支持网格搜索优化。",
        "tools": ["run_backtest", "optimize_backtest"],
        "examples": [
            "用双均线策略回测 600519",
            "优化一下 RSI2 策略参数",
            "解释这次回测里的最大回撤和夏普比率",
        ],
    },
    {
        "name": "本地模拟交易",
        "summary": "在本地纸面账户中模拟下单、撤单、查询持仓和订单状态，用于流程演练和风控验证。",
        "tools": ["place_order", "cancel_order", "check_positions"],
        "examples": [
            "模拟买入 600519 100 股",
            "查一下当前持仓",
            "撤销刚才的模拟订单",
        ],
    },
    {
        "name": "会话与智能体体验",
        "summary": "支持多轮上下文、流式输出、会话历史、基础用户记忆、技能索引和按任务路由到不同工具集。",
        "tools": ["describe_fagent", "load_skill"],
        "examples": [
            "你有哪些功能能力",
            "继续刚才那个股票分析",
            "根据我之前的偏好解释一下风险",
        ],
    },
]

FAGENT_LIMITATIONS = [
    "FAgent 不是券商交易终端；交易工具当前只做本地模拟，不会提交真实订单。",
    "当前工具链主要围绕股票研究、策略和回测；基金、债券、期货等可以做概念问答，但没有同等完整的专用工具链。",
    "行情和回测质量依赖本地或远端数据源、缓存和日期范围，缺失数据时应先说明限制。",
    "回测结果不代表未来收益，参数优化尤其需要警惕过拟合和样本外失效。",
    "用户记忆只作为上下文辅助；除非用户明确询问，不应主动列出具体记忆内容。",
]

FAGENT_EXAMPLE_PROMPTS = [
    "帮我找一下适合均线策略的股票，并说明筛选逻辑。",
    "用 RSI2 策略回测 600519 最近一年，并解释指标。",
    "列出短线、中线、长线分别适合的策略。",
    "模拟买入 000001 100 股后查看持仓。",
]


def _strategy_snapshot() -> List[Dict[str, str]]:
    """Return a lightweight strategy catalog snapshot."""
    try:
        from ..backtest.strategy_catalog import STRATEGY_CATALOG
    except Exception:
        return []

    return [
        {
            "id": strategy_id,
            "name": info.get("display_name", strategy_id),
            "horizon": info.get("horizon", ""),
            "category": info.get("category", ""),
        }
        for strategy_id, info in STRATEGY_CATALOG.items()
    ]


def build_fagent_capability_data() -> Dict[str, Any]:
    """Build structured capability data for tools, APIs and tests."""
    return {
        "identity": FAGENT_IDENTITY,
        "capability_groups": FAGENT_CAPABILITY_GROUPS,
        "strategies": _strategy_snapshot(),
        "limitations": FAGENT_LIMITATIONS,
        "example_prompts": FAGENT_EXAMPLE_PROMPTS,
    }


def format_fagent_capabilities(
    detail_level: str = "full",
    include_limits: bool = True,
    include_examples: bool = True,
) -> str:
    """Format the capability map as a concise Chinese answer."""
    data = build_fagent_capability_data()
    detail_level = detail_level if detail_level in {"short", "full"} else "full"

    lines = [
        FAGENT_IDENTITY,
        "",
        "当前已接入的核心能力：",
    ]

    for idx, group in enumerate(data["capability_groups"], 1):
        lines.append(f"{idx}. {group['name']}：{group['summary']}")
        if detail_level == "full":
            lines.append(f"   工具：{', '.join(group['tools'])}")

    if detail_level == "full" and data["strategies"]:
        strategy_text = "、".join(
            f"{item['name']}({item['horizon']})"
            for item in data["strategies"]
        )
        lines.extend(["", f"当前策略库：{strategy_text}。"])

    if include_limits:
        lines.extend(["", "重要边界："])
        lines.extend(f"- {item}" for item in data["limitations"])

    if include_examples:
        lines.extend(["", "你可以这样问："])
        lines.extend(f"- {item}" for item in data["example_prompts"])

    return "\n".join(lines)


FAGENT_CAPABILITY_SUMMARY = "\n".join(
    f"- {group['name']}：{group['summary']}"
    for group in FAGENT_CAPABILITY_GROUPS
)

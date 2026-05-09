"""内置工具集合。

按领域分组：
- market: 行情查询工具
- backtest: 回测执行工具
- trading: 模拟交易工具
"""
from .market import (
    GetQuoteTool,
    GetKLineTool,
    SearchStockTool,
    AnalyzeTrendTool,
)

__all__ = [
    "GetQuoteTool",
    "GetKLineTool",
    "SearchStockTool",
    "AnalyzeTrendTool",
]


def register_builtin_tools(registry=None):
    """注册所有内置工具到指定的 ToolRegistry。"""
    if registry is None:
        from ..registry import tool_registry as registry

    from .market import get_market_tools

    tools = get_market_tools()
    registry.register_all(tools)
    return tools

"""内置工具集合。

按领域分组：
- market: 行情查询工具
- backtest: 回测与策略工具
- trading: 模拟交易工具
"""
from .market import (
    GetQuoteTool,
    GetKLineTool,
    SearchStockTool,
    AnalyzeTrendTool,
)
from .backtest import (
    ListStrategiesTool,
    GetStrategyInfoTool,
    RunBacktestTool,
    OptimizeBacktestTool,
)
from .trading import (
    PlaceOrderTool,
    CancelOrderTool,
    CheckPositionsTool,
)

__all__ = [
    "GetQuoteTool",
    "GetKLineTool",
    "SearchStockTool",
    "AnalyzeTrendTool",
    "ListStrategiesTool",
    "GetStrategyInfoTool",
    "RunBacktestTool",
    "OptimizeBacktestTool",
    "PlaceOrderTool",
    "CancelOrderTool",
    "CheckPositionsTool",
]


def register_builtin_tools(registry=None):
    """注册所有内置工具到指定的 ToolRegistry。"""
    if registry is None:
        from ..registry import tool_registry as registry

    from .market import get_market_tools
    from .backtest import get_backtest_tools
    from .trading import get_trading_tools

    tools = get_market_tools() + get_backtest_tools() + get_trading_tools()
    registry.register_all(tools)
    return tools

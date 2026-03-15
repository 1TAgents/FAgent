"""
MCP - Model Context Protocol

提供标准化的工具调用接口，供所有 Agent 使用

快速开始:
    # Server 端
    from agents.mcp.server import app
    
    # Client 端
    from agents.mcp.client import MCPClient
    mcp = MCPClient()
    result = await mcp.call("stock_quote", symbol="600519")
"""

from .models import (
    StockQuote,
    KLineData,
    KLineItem,
    StockInfo,
    MarketType,
    KLinePeriod,
    ToolCallRequest,
    ToolCallResponse,
    ToolDefinition,
)

from .tools import tool_registry, ToolRegistry, RegisteredTool

from .client import MCPClient, MCPError, get_mcp_client

__all__ = [
    # Models
    "StockQuote",
    "KLineData",
    "KLineItem",
    "StockInfo",
    "MarketType",
    "KLinePeriod",
    "ToolCallRequest",
    "ToolCallResponse",
    "ToolDefinition",
    
    # Tools
    "tool_registry",
    "ToolRegistry",
    "RegisteredTool",
    
    # Client
    "MCPClient",
    "MCPError",
    "get_mcp_client",
]

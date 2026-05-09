"""
MCP Tools - MCP 工具适配层

将 MCP Server 暴露的工具适配为 BaseTool，注册到统一 ToolRegistry。
这样 ReAct Loop 可以像调用内置工具一样调用 MCP 工具。

设计：
- MCPTool: 动态工具类，从 MCP Server 的工具定义创建
- MCPToolRegistry: 扩展 ToolRegistry，支持从 MCP Server 发现并注册工具
"""
from __future__ import annotations

import logging
from typing import Optional

from .base import BaseTool
from .result import ToolResult
from ..core.logging import log_subagent

logger = logging.getLogger(__name__)


class MCPTool(BaseTool):
    """MCP 工具的 BaseTool 适配器。

    不直接连接 MCP Server，而是通过 MCPClient 调用远程工具。
    """

    category = "mcp"

    def __init__(self, name: str, description: str, parameters: dict, mcp_client):
        self._name = name
        self._description = description
        self._parameters = parameters
        self._mcp_client = mcp_client

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return self._description

    @property
    def parameters(self) -> dict:
        return self._parameters

    async def execute(self, **kwargs) -> ToolResult:
        try:
            data = await self._mcp_client.call(self._name, **kwargs)
            return ToolResult.ok(
                self.name,
                data=data,
                text=str(data)[:500],
            )
        except Exception as e:
            return ToolResult.fail(self.name, error=str(e))


async def discover_and_register_mcp_tools(
    registry=None,
    mcp_base_url: str = "http://localhost:8002",
    prefix: str = "mcp_",
) -> int:
    """从 MCP Server 发现并注册工具。

    Args:
        registry: ToolRegistry 实例
        mcp_base_url: MCP Server 地址
        prefix: 工具名称前缀（避免与内置工具冲突）

    Returns:
        注册的工具数量
    """
    if registry is None:
        from .registry import tool_registry as registry

    # 延迟导入避免循环依赖
    from ..mcp.client import MCPClient

    client = MCPClient(base_url=mcp_base_url)
    tools = await client.list_tools()

    if not tools:
        logger.warning(f"MCP Server ({mcp_base_url}) 未返回工具定义")
        return 0

    count = 0
    for tool_def in tools:
        name = tool_def.get("name", "")
        if not name:
            continue

        mcp_name = f"{prefix}{name}" if not name.startswith(prefix) else name
        description = tool_def.get("description", "")
        parameters = tool_def.get("inputSchema", tool_def.get("parameters", {}))

        tool = MCPTool(
            name=mcp_name,
            description=description,
            parameters=parameters,
            mcp_client=client,
        )
        registry.register(tool)
        count += 1
        logger.info(f"注册 MCP 工具: {mcp_name}")

    return count

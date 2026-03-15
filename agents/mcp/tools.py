"""
MCP Tools - 工具注册中心

参考 MCP (Model Context Protocol) 规范：
https://modelcontextprotocol.io/
"""
from typing import Callable, Dict, Any, List, Awaitable
from dataclasses import dataclass, field
import logging

from .models import ToolDefinition

logger = logging.getLogger(__name__)


@dataclass
class RegisteredTool:
    """已注册的工具"""
    definition: ToolDefinition
    handler: Callable[..., Awaitable[Dict[str, Any]]]
    enabled: bool = True


class ToolRegistry:
    """
    MCP 工具注册表
    
    用法:
        registry = ToolRegistry()
        registry.register("stock_quote", handler, description, parameters)
        tool = registry.get("stock_quote")
        result = await tool(symbol="600519")
    """
    
    def __init__(self):
        self._tools: Dict[str, RegisteredTool] = {}
        logger.info("ToolRegistry 初始化完成")
    
    def register(
        self,
        name: str,
        handler: Callable[..., Awaitable[Dict[str, Any]]],
        description: str = "",
        parameters: Dict[str, Any] = None,
        enabled: bool = True
    ):
        """
        注册工具
        
        Args:
            name: 工具名称（唯一标识）
            handler: 异步处理函数
            description: 工具描述（供 Agent 理解用途）
            parameters: JSON Schema 格式的参数定义
            enabled: 是否启用
        """
        self._tools[name] = RegisteredTool(
            definition=ToolDefinition(
                name=name,
                description=description,
                parameters=parameters or {}
            ),
            handler=handler,
            enabled=enabled
        )
        logger.info(f"工具注册成功：{name}")
    
    def unregister(self, name: str):
        """注销工具"""
        if name in self._tools:
            del self._tools[name]
            logger.info(f"工具已注销：{name}")
    
    def get(self, name: str) -> Callable[..., Awaitable[Dict[str, Any]]]:
        """
        获取工具处理器
        
        Args:
            name: 工具名称
            
        Returns:
            异步处理函数
            
        Raises:
            KeyError: 工具不存在
        """
        if name not in self._tools:
            raise KeyError(f"工具不存在：{name}")
        
        tool = self._tools[name]
        if not tool.enabled:
            raise RuntimeError(f"工具已禁用：{name}")
        
        return tool.handler
    
    def enable(self, name: str):
        """启用工具"""
        if name in self._tools:
            self._tools[name].enabled = True
    
    def disable(self, name: str):
        """禁用工具"""
        if name in self._tools:
            self._tools[name].enabled = False
    
    def list_all(self, enabled_only: bool = True) -> List[ToolDefinition]:
        """
        列出所有工具（供 Agent 发现）
        
        Args:
            enabled_only: 是否只返回启用的工具
            
        Returns:
            工具定义列表
        """
        tools = []
        for tool in self._tools.values():
            if enabled_only and not tool.enabled:
                continue
            tools.append(tool.definition)
        return tools
    
    def has(self, name: str) -> bool:
        """检查工具是否存在"""
        return name in self._tools
    
    @property
    def count(self) -> int:
        """返回已注册工具数量"""
        return len(self._tools)


# 全局注册表实例
tool_registry = ToolRegistry()

"""
ToolRegistry - 工具注册中心

集中管理所有工具的注册、查询、schema 生成。

设计参考：
- claude-code-rev: 模块化 tool registry，feature-gated
- Vibe-Trading: 按领域分组的工具集
- OpenManus: Pydantic-based tool schemas

核心能力：
- register(): 注册单个工具
- register_all(): 批量注册
- get(): 按名称获取工具
- get_all_schemas(): 生成所有工具的 LLM schema
- list_by_category(): 按类别列出工具
- execute(): 通过名称直接执行工具
"""
from __future__ import annotations

from typing import Dict, List, Optional, Type

from .base import BaseTool
from .result import ToolResult
from ..core.logging import logger


class ToolRegistry:
    """工具注册中心（单例模式）。

    维护工具名称 -> 实例的映射，提供统一的查询和执行接口。
    """

    _instance: Optional[ToolRegistry] = None

    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}
        self._categories: Dict[str, List[str]] = {}

    @classmethod
    def get_instance(cls) -> ToolRegistry:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset(cls):
        """重置单例（用于测试）。"""
        cls._instance = None

    # ========== 注册 ==========

    def register(self, tool: BaseTool) -> None:
        """注册单个工具。"""
        if not tool.name:
            raise ValueError(f"工具必须设置 name 属性: {tool}")
        if tool.name in self._tools:
            logger.warning(f"工具 {tool.name!r} 已存在，将被覆盖")
            old = self._tools.pop(tool.name)
            cat = old.category
            if cat in self._categories and tool.name in self._categories[cat]:
                self._categories[cat].remove(tool.name)

        self._tools[tool.name] = tool
        if tool.category not in self._categories:
            self._categories[tool.category] = []
        if tool.name not in self._categories[tool.category]:
            self._categories[tool.category].append(tool.name)
        logger.debug(f"注册工具: {tool.name} (category={tool.category})")

    def register_all(self, tools: List[BaseTool]) -> None:
        """批量注册工具。"""
        for tool in tools:
            self.register(tool)

    def unregister(self, name: str) -> Optional[BaseTool]:
        """注销工具。"""
        tool = self._tools.pop(name, None)
        if tool and tool.category in self._categories:
            if name in self._categories[tool.category]:
                self._categories[tool.category].remove(name)
        return tool

    # ========== 查询 ==========

    def get(self, name: str) -> Optional[BaseTool]:
        """按名称获取工具。"""
        return self._tools.get(name)

    def has(self, name: str) -> bool:
        return name in self._tools

    @property
    def tool_names(self) -> List[str]:
        return list(self._tools.keys())

    @property
    def count(self) -> int:
        return len(self._tools)

    def get_all_schemas(self) -> List[dict]:
        """生成所有工具的 LLM schema 列表。"""
        return [tool.schema for tool in self._tools.values()]

    def list_by_category(self, category: str) -> List[BaseTool]:
        """按类别列出工具。"""
        names = self._categories.get(category, [])
        return [self._tools[n] for n in names if n in self._tools]

    @property
    def categories(self) -> List[str]:
        return list(self._categories.keys())

    def summary(self) -> dict:
        """生成工具注册摘要。"""
        return {
            "total": self.count,
            "categories": {
                cat: len(names) for cat, names in self._categories.items()
            },
            "tools": self.tool_names,
        }

    # ========== 执行 ==========

    async def execute(self, name: str, **kwargs) -> ToolResult:
        """通过名称执行工具。

        Args:
            name: 工具名称
            **kwargs: 传递给工具执行的参数

        Returns:
            ToolResult: 执行结果
        """
        tool = self.get(name)
        if tool is None:
            return ToolResult.fail(name, error=f"未知工具: {name}")

        valid, err = tool.validate_params(kwargs)
        if not valid:
            return ToolResult.fail(name, error=err)

        return await tool(**kwargs)

    def __repr__(self) -> str:
        return f"<ToolRegistry tools={self.count} categories={len(self._categories)}>"


# 全局单例
tool_registry = ToolRegistry.get_instance()

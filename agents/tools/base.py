"""
BaseTool - 工具抽象基类

所有工具必须继承此类，通过 JSON Schema 声明参数，
通过 execute() 实现业务逻辑。

设计参考：claude-code-rev 的模块化 tool registry + Vibe-Trading 的工具分类。
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Optional

from .result import ToolResult


class BaseTool(ABC):
    """工具的抽象基类。

    子类需要实现：
    - name: 工具名称（唯一标识）
    - description: 工具描述（会展示给 LLM）
    - parameters: JSON Schema 参数定义
    - execute: 实际执行逻辑
    """

    name: str = ""
    description: str = ""
    category: str = "builtin"  # builtin | market | backtest | trading | mcp | external

    @property
    def parameters(self) -> dict:
        """返回 JSON Schema 格式的参数定义。

        子类应覆盖此方法返回具体 schema。
        默认返回空 schema（无参数工具）。
        """
        return {"type": "object", "properties": {}, "required": []}

    @property
    def schema(self) -> dict:
        """生成完整的工具 schema（供 LLM tool use 使用）。"""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
        }

    @abstractmethod
    async def execute(self, **kwargs) -> ToolResult:
        """执行工具逻辑。

        参数由 LLM 的 tool_call arguments 解包传入。
        必须返回 ToolResult 实例。
        """
        ...

    async def __call__(self, **kwargs) -> ToolResult:
        """便捷调用入口。"""
        import time
        start = time.monotonic()
        try:
            result = await self.execute(**kwargs)
        except Exception as e:
            result = ToolResult.fail(self.name, error=str(e))
        result.duration_ms = (time.monotonic() - start) * 1000
        return result

    def validate_params(self, params: dict) -> tuple[bool, Optional[str]]:
        """简单参数校验。

        检查 required 参数是否都存在。
        复杂校验应在 execute() 中做。
        """
        required = self.parameters.get("required", [])
        for key in required:
            if key not in params or params[key] is None:
                return False, f"缺少必需参数: {key}"
        return True, None

    def __repr__(self) -> str:
        return f"<Tool name={self.name!r} category={self.category!r}>"

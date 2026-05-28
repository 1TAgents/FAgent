"""
ToolResult - 统一的工具执行结果格式

所有工具执行后都返回此结构，确保下游（SubAgent、Router）能稳定处理。
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class ToolResult:
    """工具执行结果。

    统一字段设计：
    - success 决定处理路径
    - data 是结构化数据（供程序/LLM 使用）
    - text 是人类可读摘要（供直接展示）
    - error 仅在失败时有值
    """

    tool_name: str
    success: bool
    data: Optional[dict] = None
    text: str = ""
    error: Optional[str] = None
    duration_ms: float = 0.0
    metadata: dict = field(default_factory=dict)

    @classmethod
    def ok(cls, tool_name: str, data: Optional[dict] = None, text: str = "", **kw) -> ToolResult:
        return cls(tool_name=tool_name, success=True, data=data, text=text, **kw)

    @classmethod
    def fail(cls, tool_name: str, error: str, **kw) -> ToolResult:
        return cls(tool_name=tool_name, success=False, error=error, **kw)

    def to_llm_content(self, max_chars: int = 4000) -> str:
        """生成适合回写给 LLM 的内容。

        Args:
            max_chars: 最大字符数，超出部分会被截断并附加提示。
        """
        if self.success:
            if self.text:
                content = self.text
            elif self.data:
                content = str(self.data)
            else:
                content = "执行成功，无返回数据"
        else:
            content = f"工具执行失败: {self.error}"

        if len(content) > max_chars:
            content = content[:max_chars] + f"\n...(内容已截断，共 {len(content)} 字符)"
        return content

    def to_dict(self) -> dict:
        d = {
            "tool_name": self.tool_name,
            "success": self.success,
            "duration_ms": round(self.duration_ms, 2),
        }
        if self.success:
            d["data"] = self.data
            d["text"] = self.text
        else:
            d["error"] = self.error
        if self.metadata:
            d["metadata"] = self.metadata
        return d

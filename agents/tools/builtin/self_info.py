"""Self information tools for FAgent."""
from __future__ import annotations

from typing import Optional

from ..base import BaseTool, DangerLevel
from ..result import ToolResult
from ...core.capabilities import (
    build_fagent_capability_data,
    format_fagent_capabilities,
)


class DescribeFAgentTool(BaseTool):
    """Return the authoritative FAgent capability description."""

    name = "describe_fagent"
    description = (
        "权威说明 FAgent 当前真实能力、工具范围、策略/回测/模拟交易边界；"
        "当用户询问 FAgent 是什么、有哪些功能、能做什么、后台会做什么时必须调用。"
    )
    category = "self"
    danger_level = DangerLevel.READ_ONLY

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "detail_level": {
                    "type": "string",
                    "enum": ["short", "full"],
                    "description": "返回详细程度。short 为简版，full 包含工具、策略库、边界和示例。",
                    "default": "full",
                },
                "include_limits": {
                    "type": "boolean",
                    "description": "是否包含能力边界和风险说明。",
                    "default": True,
                },
                "include_examples": {
                    "type": "boolean",
                    "description": "是否包含可直接尝试的问题示例。",
                    "default": True,
                },
            },
            "required": [],
        }

    async def execute(
        self,
        detail_level: Optional[str] = "full",
        include_limits: bool = True,
        include_examples: bool = True,
        **kw,
    ) -> ToolResult:
        detail = detail_level if detail_level in {"short", "full"} else "full"
        data = build_fagent_capability_data()
        text = format_fagent_capabilities(
            detail_level=detail,
            include_limits=include_limits,
            include_examples=include_examples,
        )
        return ToolResult.ok(self.name, data=data, text=text)


def get_self_info_tools() -> list[BaseTool]:
    """Return all self-information tools."""
    return [DescribeFAgentTool()]

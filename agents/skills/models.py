"""
Skill Model — 定义 Skill 数据结构和路由关联规则。

Skill 与 Tool 的语义区别：
- Tool: 一个可被模型调用的函数（如 get_quote, place_order）
- Skill: 可复用的任务方法、领域流程、操作规程（如"如何分析一只股票"）
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List


@dataclass
class Skill:
    """一个可被 LLM 发现和加载的技能。

    属性：
        name: 技能唯一标识（如 "trend_analysis"）
        description: 简短描述，用于 skill index 展示
        keywords: 触发词列表，用于语义匹配
        content: 完整技能内容（Markdown 格式的 procedural knowledge）
        routes: 适用的路由类型列表（如 ["market", "strategy"]）
        version: 技能版本号
    """

    name: str
    description: str
    keywords: List[str] = field(default_factory=list)
    content: str = ""
    routes: List[str] = field(default_factory=list)
    version: str = "1.0"

    @property
    def index_entry(self) -> str:
        """生成 skill index 中的一行，用于注入系统提示。"""
        routes_str = ", ".join(self.routes) if self.routes else "all"
        return f"- **{self.name}**: {self.description} (适用: {routes_str})"

    def to_tool_schema(self) -> dict:
        """将技能转换为工具 schema，供 load_skill 工具使用。"""
        return {
            "type": "function",
            "function": {
                "name": "load_skill",
                "description": "加载指定技能的详细内容。仅在用户请求涉及该技能领域时使用。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "skill_name": {
                            "type": "string",
                            "description": f"技能名称。可选值: {self.name}",
                        },
                    },
                    "required": ["skill_name"],
                },
            },
        }

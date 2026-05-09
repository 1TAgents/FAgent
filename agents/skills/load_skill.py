"""
Load Skill Tool — 让 LLM 可以主动加载技能的详细内容。
"""
from __future__ import annotations

import logging
from typing import List

from ..tools.base import BaseTool, DangerLevel
from ..tools.result import ToolResult
from .registry import SkillRegistry, skill_registry

logger = logging.getLogger(__name__)


class LoadSkillTool(BaseTool):
    """加载指定技能的详细内容。"""

    name = "load_skill"
    description = "加载并查看指定技能的详细操作规程。当需要按专业流程完成某类任务时使用。"
    category = "skill"
    danger_level = DangerLevel.READ_ONLY

    def __init__(self, registry: SkillRegistry = None):
        self._registry = registry or skill_registry

    @property
    def parameters(self) -> dict:
        skill_names = self._registry.skill_names
        return {
            "type": "object",
            "properties": {
                "skill_name": {
                    "type": "string",
                    "description": f"技能名称。可选: {', '.join(skill_names) if skill_names else '无'}",
                    "enum": skill_names,
                },
            },
            "required": ["skill_name"],
        }

    async def execute(self, skill_name: str, **kw) -> ToolResult:
        skill = self._registry.get(skill_name)
        if not skill:
            available = ", ".join(self._registry.skill_names)
            return ToolResult.fail(
                self.name,
                error=f"技能 '{skill_name}' 不存在。可用技能: {available}",
            )
        return ToolResult.ok(
            self.name,
            data={"name": skill.name, "content": skill.content, "version": skill.version},
            text=skill.content,
        )


def get_skill_tools(registry: SkillRegistry = None) -> List[BaseTool]:
    """返回技能工具列表。"""
    return [LoadSkillTool(registry)]

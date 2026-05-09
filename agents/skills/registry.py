"""
Skill Registry — 技能注册中心。

职责：
- 管理技能的注册、发现和加载
- 按路由类型过滤可用技能
- 提供 skill index（精简版）供注入系统提示
"""
from __future__ import annotations

import logging
from typing import Dict, List, Optional

from .models import Skill

logger = logging.getLogger(__name__)


class SkillRegistry:
    """技能注册中心。

    技能按路由类型分组，只有与当前路由匹配的技能才会被注入。
    """

    def __init__(self):
        self._skills: Dict[str, Skill] = {}

    def register(self, skill: Skill) -> None:
        """注册一个技能。"""
        if skill.name in self._skills:
            logger.warning(f"技能 {skill.name} 已存在，将被覆盖")
        self._skills[skill.name] = skill
        logger.debug(f"技能已注册: {skill.name}")

    def get(self, name: str) -> Optional[Skill]:
        """按名称获取技能。"""
        return self._skills.get(name)

    def list_for_route(self, route: str) -> List[Skill]:
        """返回适用于指定路由的技能列表。"""
        result = []
        for skill in self._skills.values():
            if not skill.routes or route in skill.routes or "all" in skill.routes:
                result.append(skill)
        return result

    def get_index_for_route(self, route: str) -> str:
        """生成 skill index 文本，用于注入系统提示。

        返回精简版索引（仅名称和描述），不暴露完整内容。
        """
        skills = self.list_for_route(route)
        if not skills:
            return ""
        lines = ["\n## 可用技能\n以下是你可以调用的专业技能。当用户请求涉及相关领域时，使用 load_skill 工具加载详细内容："]
        for skill in skills:
            lines.append(skill.index_entry)
        return "\n".join(lines)

    @property
    def all_skills(self) -> List[Skill]:
        """返回所有已注册技能。"""
        return list(self._skills.values())

    @property
    def skill_names(self) -> List[str]:
        """返回所有技能名称。"""
        return list(self._skills.keys())


# 全局实例
skill_registry = SkillRegistry()

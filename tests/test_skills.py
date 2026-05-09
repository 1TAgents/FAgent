"""
Skill System 测试
"""
import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from agents.skills.models import Skill
from agents.skills.registry import SkillRegistry
from agents.skills.load_skill import LoadSkillTool


@pytest.fixture
def registry():
    """创建带测试技能的 registry。"""
    reg = SkillRegistry()
    reg.register(Skill(
        name="test_analysis",
        description="测试用分析技能",
        keywords=["测试", "分析"],
        content="# 测试技能内容\n这是测试用技能内容。",
        routes=["market", "chat"],
    ))
    reg.register(Skill(
        name="test_backtest",
        description="测试用回测技能",
        keywords=["回测", "策略"],
        content="# 测试回测内容",
        routes=["strategy", "backtest"],
    ))
    reg.register(Skill(
        name="test_universal",
        description="通用技能",
        keywords=[],
        content="通用内容",
        routes=["all"],
    ))
    return reg


class TestSkillModel:
    def test_index_entry(self):
        skill = Skill(
            name="test_skill",
            description="描述文本",
            routes=["market", "chat"],
        )
        entry = skill.index_entry
        assert "test_skill" in entry
        assert "描述文本" in entry
        assert "market, chat" in entry

    def test_index_entry_no_routes(self):
        skill = Skill(name="no_route", description="无路由")
        entry = skill.index_entry
        assert "all" in entry


class TestSkillRegistry:
    def test_register_and_get(self, registry):
        skill = registry.get("test_analysis")
        assert skill is not None
        assert skill.name == "test_analysis"

    def test_register_overwrite(self, registry):
        new_skill = Skill(name="test_analysis", description="新版本")
        registry.register(new_skill)
        assert registry.get("test_analysis").description == "新版本"

    def test_list_for_route(self, registry):
        skills = registry.list_for_route("market")
        names = [s.name for s in skills]
        assert "test_analysis" in names
        assert "test_universal" in names
        assert "test_backtest" not in names

    def test_list_for_backtest_route(self, registry):
        skills = registry.list_for_route("backtest")
        names = [s.name for s in skills]
        assert "test_backtest" in names
        assert "test_universal" in names
        assert "test_analysis" not in names

    def test_list_for_chat_route(self, registry):
        skills = registry.list_for_route("chat")
        names = [s.name for s in skills]
        assert "test_analysis" in names
        assert "test_universal" in names
        assert "test_backtest" not in names

    def test_skill_index_text(self, registry):
        idx = registry.get_index_for_route("market")
        assert "test_analysis" in idx
        assert "test_backtest" not in idx

    def test_skill_index_empty_route(self, registry):
        idx = registry.get_index_for_route("unknown_route")
        assert "test_universal" in idx  # "all" route matches

    def test_all_skills(self, registry):
        assert len(registry.all_skills) == 3

    def test_skill_names(self, registry):
        names = registry.skill_names
        assert set(names) == {"test_analysis", "test_backtest", "test_universal"}


class TestLoadSkillTool:
    def test_load_existing_skill(self, registry):
        tool = LoadSkillTool(registry)
        # execute is async, so we need to run it in an async context
        import asyncio
        result = asyncio.get_event_loop().run_until_complete(
            tool.execute(skill_name="test_analysis")
        )
        assert result.success
        assert "测试技能内容" in result.text

    def test_load_nonexistent_skill(self, registry):
        tool = LoadSkillTool(registry)
        import asyncio
        result = asyncio.get_event_loop().run_until_complete(
            tool.execute(skill_name="nonexistent")
        )
        assert not result.success
        assert "不存在" in result.error

    def test_parameters_include_skill_names(self, registry):
        tool = LoadSkillTool(registry)
        params = tool.parameters
        assert "test_analysis" in params["properties"]["skill_name"]["enum"]
        assert "test_backtest" in params["properties"]["skill_name"]["enum"]


class TestBuiltinSkills:
    def test_builtin_skills_exist(self):
        from agents.skills.builtin import ALL_BUILTIN_SKILLS
        assert len(ALL_BUILTIN_SKILLS) == 3
        names = [s.name for s in ALL_BUILTIN_SKILLS]
        assert "trend_analysis" in names
        assert "risk_assessment" in names
        assert "strategy_backtest" in names

    def test_builtin_skills_have_content(self):
        from agents.skills.builtin import ALL_BUILTIN_SKILLS
        for skill in ALL_BUILTIN_SKILLS:
            assert skill.content, f"Skill {skill.name} has no content"
            assert skill.description, f"Skill {skill.name} has no description"

    def test_builtin_skills_registered(self):
        from agents.skills.builtin import ALL_BUILTIN_SKILLS
        reg = SkillRegistry()
        for skill in ALL_BUILTIN_SKILLS:
            reg.register(skill)
        assert len(reg.all_skills) == 3
        assert reg.get("trend_analysis") is not None

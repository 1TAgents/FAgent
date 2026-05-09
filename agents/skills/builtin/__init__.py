"""
Built-in Skills — 内置金融领域技能。

每个技能都是一段 procedural knowledge（操作规程），
告诉 LLM 如何按专业流程完成特定领域的任务。
"""
from .market_analysis import TREND_ANALYSIS_SKILL
from .risk_assessment import RISK_ASSESSMENT_SKILL
from .strategy_backtest import STRATEGY_BACKTEST_SKILL

ALL_BUILTIN_SKILLS = [
    TREND_ANALYSIS_SKILL,
    RISK_ASSESSMENT_SKILL,
    STRATEGY_BACKTEST_SKILL,
]

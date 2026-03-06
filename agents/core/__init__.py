"""
Agent 核心组件
"""
from .prompts import DEFAULT_SYSTEM_PROMPT
from .logging import logger, log_router, log_subagent

__all__ = [
    "DEFAULT_SYSTEM_PROMPT",
    "logger",
    "log_router", 
    "log_subagent",
]


"""
FAgent 算法引擎模块

职责：
- System Prompt 管理
- LLM 调用
- 对话逻辑处理
- 多 Agent 编排（未来）
"""
from dotenv import load_dotenv, find_dotenv

# 在导入其他模块之前加载环境变量
load_dotenv(find_dotenv())

from .services.chat_agent import chat_agent

__all__ = ["chat_agent"]


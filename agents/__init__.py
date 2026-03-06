"""
FAgent 算法引擎模块

职责：
- System Prompt 管理
- LLM 调用
- 对话逻辑处理
- 多 Agent 编排（未来）
"""
import os

# 在导入任何第三方库之前，禁用系统代理
# macOS 系统代理会被 requests/urllib 自动检测，导致金融数据 API 连接失败
os.environ["http_proxy"] = ""
os.environ["https_proxy"] = ""
os.environ["HTTP_PROXY"] = ""
os.environ["HTTPS_PROXY"] = ""
os.environ["ALL_PROXY"] = ""
os.environ["all_proxy"] = ""
os.environ["no_proxy"] = "*"
os.environ["NO_PROXY"] = "*"

import urllib.request
urllib.request.getproxies = lambda: {}

import requests as _requests
import requests.sessions as _rsessions
_OrigSession = _rsessions.Session
class _NoProxySession(_OrigSession):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.trust_env = False
_rsessions.Session = _NoProxySession
_requests.Session = _NoProxySession

from dotenv import load_dotenv, find_dotenv

# 加载环境变量（不覆盖已设置的代理变量）
load_dotenv(find_dotenv(), override=False)

from .services.chat_agent import chat_agent

__all__ = ["chat_agent"]


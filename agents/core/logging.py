"""
Agents 日志配置模块 - 使用 loguru

使用方式:
    from agents.core.logging import logger, log_router, log_subagent, log_tool_call
    
    logger.info("信息日志")
    
    # Router 日志
    log_router.request(cid=123, message_id=456, user_message="查询茅台")
    log_router.intent(route="market", task="get_quote", confidence=0.95)
    log_router.context(task_context)
    log_router.dispatch("MarketSubAgent")
    
    # SubAgent 日志
    log_subagent.start("MarketSubAgent", "get_quote")
    log_subagent.tool_call("market_service.get_quote", {"symbol": "600519"})
    log_subagent.tool_result(success=True, summary="茅台 1850.00")
    log_subagent.done("MarketSubAgent", duration=1.5)
"""
import sys
import os
import json
from pathlib import Path
from datetime import datetime
from typing import Any, Optional, Dict
from loguru import logger

# 移除默认的 handler
logger.remove()

# 日志目录
LOG_DIR = Path(__file__).parent.parent.parent / "logs" / "agents"
LOG_DIR.mkdir(parents=True, exist_ok=True)

# 简洁格式（用于控制台）
CONSOLE_FORMAT = (
    "<green>{time:HH:mm:ss.SSS}</green> | "
    "<level>{level: <8}</level> | "
    "<cyan>{name}</cyan> | "
    "<level>{message}</level>"
)

# 文件格式（无颜色）
FILE_FORMAT = (
    "{time:YYYY-MM-DD HH:mm:ss.SSS} | "
    "{level: <8} | "
    "{name}:{function}:{line} | "
    "{message}"
)

# 获取日志级别（从环境变量，默认 DEBUG 便于排查）
LOG_LEVEL = os.getenv("LOG_LEVEL", "DEBUG").upper()

# 控制台输出
logger.add(
    sys.stderr,
    format=CONSOLE_FORMAT,
    level=LOG_LEVEL,
    colorize=True,
)

# 文件输出 - 所有日志
logger.add(
    LOG_DIR / "agents_{time:YYYY-MM-DD}.log",
    format=FILE_FORMAT,
    level="DEBUG",
    rotation="00:00",
    retention="7 days",
    compression="gz",
    encoding="utf-8",
)

# 文件输出 - 错误日志
logger.add(
    LOG_DIR / "error_{time:YYYY-MM-DD}.log",
    format=FILE_FORMAT,
    level="ERROR",
    rotation="00:00",
    retention="30 days",
    compression="gz",
    encoding="utf-8",
)

# Router 专用日志
logger.add(
    LOG_DIR / "router_{time:YYYY-MM-DD}.log",
    format=FILE_FORMAT,
    level="DEBUG",
    filter=lambda record: record["extra"].get("router_log"),
    rotation="00:00",
    retention="7 days",
    encoding="utf-8",
)

# SubAgent 专用日志
logger.add(
    LOG_DIR / "subagent_{time:YYYY-MM-DD}.log",
    format=FILE_FORMAT,
    level="DEBUG",
    filter=lambda record: record["extra"].get("subagent_log"),
    rotation="00:00",
    retention="7 days",
    encoding="utf-8",
)


def _safe_json(obj: Any, max_length: int = 3000) -> str:
    """安全地序列化对象为 JSON 字符串"""
    try:
        s = json.dumps(obj, ensure_ascii=False, default=str)
        if len(s) > max_length:
            return s[:max_length] + "...[truncated]"
        return s
    except Exception:
        return str(obj)[:max_length]


def _get_trace_prefix() -> str:
    """获取追踪前缀 [rid=xxx cid=yyy]"""
    try:
        from .context import get_trace_prefix
        return get_trace_prefix()
    except Exception:
        return ""


class RouterLogger:
    """Router 专用日志记录器"""
    
    def __init__(self):
        self._logger = logger.bind(router_log=True)
    
    def request(self, cid: int, message_id: int, user_message: str):
        """记录 Router 收到的请求"""
        prefix = _get_trace_prefix()
        self._logger.info(f"{prefix}[ROUTER_REQ] cid={cid} | message_id={message_id}")
        self._logger.debug(f"{prefix}[ROUTER_REQ] user_message={user_message}")
        logger.info(f"{prefix}[ROUTER_REQ] cid={cid} | message_id={message_id}")
    
    def history(self, cid: int, message_count: int, messages: list = None):
        """记录加载的历史消息"""
        prefix = _get_trace_prefix()
        self._logger.info(f"{prefix}[ROUTER_HISTORY] loaded={message_count} messages")
        if messages:
            self._logger.debug(f"{prefix}[ROUTER_HISTORY] messages={_safe_json(messages)}")
        logger.info(f"{prefix}[ROUTER_HISTORY] loaded={message_count} messages")
    
    def intent(
        self, 
        route: str, 
        task: str, 
        params: dict = None,
        raw_response: str = None,
    ):
        """记录意图分析结果"""
        prefix = _get_trace_prefix()
        self._logger.info(f"{prefix}[ROUTER_INTENT] route={route} | task={task} | params={params}")
        if raw_response:
            self._logger.debug(f"{prefix}[ROUTER_INTENT] llm_response={raw_response}")
        logger.info(f"{prefix}[ROUTER_INTENT] route={route} | task={task}")
    
    def context(self, context: Any):
        """记录构建的 TaskContext"""
        prefix = _get_trace_prefix()
        if hasattr(context, 'to_dict'):
            ctx_dict = context.to_dict()
        elif hasattr(context, '__dict__'):
            ctx_dict = context.__dict__
        else:
            ctx_dict = str(context)
        
        self._logger.info(f"{prefix}[ROUTER_CONTEXT] task_type={ctx_dict.get('task_type', 'unknown')}")
        self._logger.debug(f"{prefix}[ROUTER_CONTEXT] full={_safe_json(ctx_dict)}")
        logger.debug(f"{prefix}[ROUTER_CONTEXT] {_safe_json(ctx_dict, 500)}")
    
    def dispatch(self, subagent_name: str, task_type: str = None):
        """记录路由分发"""
        prefix = _get_trace_prefix()
        self._logger.info(f"{prefix}[ROUTER_DISPATCH] target={subagent_name} | task={task_type}")
        logger.info(f"{prefix}[ROUTER_DISPATCH] target={subagent_name}")
    
    def fallback(self, reason: str):
        """记录回退到默认处理"""
        prefix = _get_trace_prefix()
        self._logger.warning(f"{prefix}[ROUTER_FALLBACK] reason={reason}")
        logger.warning(f"{prefix}[ROUTER_FALLBACK] reason={reason}")
    
    def done(self, cid: int, duration: float, route: str = None):
        """记录 Router 完成"""
        prefix = _get_trace_prefix()
        self._logger.info(f"{prefix}[ROUTER_DONE] route={route} | duration={duration:.3f}s")
        logger.info(f"{prefix}[ROUTER_DONE] duration={duration:.3f}s")


class SubAgentLogger:
    """SubAgent 专用日志记录器"""
    
    def __init__(self):
        self._logger = logger.bind(subagent_log=True)
    
    def start(self, agent_name: str, task_type: str, context: Any = None):
        """记录 SubAgent 开始处理"""
        prefix = _get_trace_prefix()
        self._logger.info(f"{prefix}[SUBAGENT_START] agent={agent_name} | task={task_type}")
        if context:
            if hasattr(context, 'to_dict'):
                self._logger.debug(f"{prefix}[SUBAGENT_START] context={_safe_json(context.to_dict())}")
            else:
                self._logger.debug(f"{prefix}[SUBAGENT_START] context={_safe_json(context)}")
        logger.info(f"{prefix}[SUBAGENT_START] {agent_name}.{task_type}")
    
    def tool_call(self, tool_name: str, params: dict = None):
        """记录工具调用"""
        prefix = _get_trace_prefix()
        self._logger.info(f"{prefix}[TOOL_CALL] tool={tool_name} | params={_safe_json(params, 500)}")
        logger.info(f"{prefix}[TOOL_CALL] {tool_name}")
        logger.debug(f"{prefix}[TOOL_CALL] params={_safe_json(params)}")
    
    def tool_result(
        self, 
        tool_name: str,
        success: bool, 
        data: Any = None,
        error: str = None,
        duration: float = None,
    ):
        """记录工具调用结果"""
        prefix = _get_trace_prefix()
        if success:
            self._logger.info(f"{prefix}[TOOL_RESULT] tool={tool_name} | success=true | duration={duration:.3f}s" if duration else f"{prefix}[TOOL_RESULT] tool={tool_name} | success=true")
            if data:
                self._logger.debug(f"{prefix}[TOOL_RESULT] data={_safe_json(data)}")
            logger.info(f"{prefix}[TOOL_RESULT] {tool_name} | success")
        else:
            self._logger.warning(f"{prefix}[TOOL_RESULT] tool={tool_name} | success=false | error={error}")
            logger.warning(f"{prefix}[TOOL_RESULT] {tool_name} | failed | {error}")
    
    def llm_call(
        self, 
        model: str = None,
        messages_count: int = None,
        temperature: float = None,
    ):
        """记录 LLM 调用"""
        prefix = _get_trace_prefix()
        self._logger.info(f"{prefix}[LLM_CALL] model={model} | messages={messages_count} | temp={temperature}")
        logger.debug(f"{prefix}[LLM_CALL] model={model} | messages={messages_count}")
    
    def llm_stream(
        self,
        chunk_count: int = None,
        total_tokens: int = None,
        duration: float = None,
    ):
        """记录 LLM 流式响应完成"""
        prefix = _get_trace_prefix()
        self._logger.info(f"{prefix}[LLM_STREAM] chunks={chunk_count} | tokens={total_tokens} | duration={duration:.3f}s" if duration else f"{prefix}[LLM_STREAM] chunks={chunk_count} | tokens={total_tokens}")
        logger.debug(f"{prefix}[LLM_STREAM] chunks={chunk_count} | tokens={total_tokens}")
    
    def done(self, agent_name: str, duration: float, success: bool = True):
        """记录 SubAgent 完成"""
        prefix = _get_trace_prefix()
        if success:
            self._logger.info(f"{prefix}[SUBAGENT_DONE] agent={agent_name} | duration={duration:.3f}s")
            logger.info(f"{prefix}[SUBAGENT_DONE] {agent_name} | {duration:.3f}s")
        else:
            self._logger.warning(f"{prefix}[SUBAGENT_DONE] agent={agent_name} | duration={duration:.3f}s | success=false")
            logger.warning(f"{prefix}[SUBAGENT_DONE] {agent_name} | failed")


# 全局日志记录器实例
log_router = RouterLogger()
log_subagent = SubAgentLogger()


# 导出
__all__ = [
    "logger",
    "log_router",
    "log_subagent",
]

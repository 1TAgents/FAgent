"""
日志配置模块 - 使用 loguru

使用方式:
    from backend.core.logging import logger, log_request, log_response
    
    logger.info("信息日志")
    logger.debug("调试日志")
    
    # 请求日志
    log_request("POST", "/api/chat/send/stream", {"cid": 123, "msg": "hello"})
    log_response("POST", "/api/chat/send/stream", 200, duration=0.5)
"""
import sys
import os
import json
from pathlib import Path
from datetime import datetime
from typing import Any, Optional
from loguru import logger

# 移除默认的 handler
logger.remove()

# 日志目录
LOG_DIR = Path(__file__).parent.parent.parent / "logs" / "backend"
LOG_DIR.mkdir(parents=True, exist_ok=True)

# 日志格式
LOG_FORMAT = (
    "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
    "<level>{level: <8}</level> | "
    "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
    "<level>{message}</level>"
)

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
    LOG_DIR / "backend_{time:YYYY-MM-DD}.log",
    format=FILE_FORMAT,
    level="DEBUG",
    rotation="00:00",  # 每天午夜轮转
    retention="7 days",  # 保留 7 天
    compression="gz",   # 压缩旧日志
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

# 文件输出 - 请求日志（JSONL 格式，便于分析）
logger.add(
    LOG_DIR / "requests_{time:YYYY-MM-DD}.jsonl",
    format="{message}",
    level="INFO",
    filter=lambda record: record["extra"].get("request_log"),
    rotation="00:00",
    retention="7 days",
    encoding="utf-8",
)

# 文件输出 - Chain 日志（JSONL 格式，便于链路评估）
logger.add(
    LOG_DIR / "chain_{time:YYYY-MM-DD}.jsonl",
    format="{message}",
    level="INFO",
    filter=lambda record: record["extra"].get("chain_log"),
    rotation="00:00",
    retention="7 days",
    encoding="utf-8",
)


def _safe_json(obj: Any, max_length: int = 2000) -> str:
    """安全地序列化对象为 JSON 字符串"""
    try:
        s = json.dumps(obj, ensure_ascii=False, default=str)
        if len(s) > max_length:
            return s[:max_length] + "...[truncated]"
        return s
    except Exception:
        return str(obj)[:max_length]


def _get_trace_prefix() -> str:
    """获取追踪前缀 [cid=X mid=Y rid=Z]"""
    try:
        from .context import get_context
        ctx = get_context()
        parts = []
        if ctx.get("cid"):
            parts.append(f"cid={ctx['cid']}")
        if ctx.get("mid"):
            parts.append(f"mid={ctx['mid']}")
        if ctx.get("rid"):
            parts.append(f"rid={ctx['rid']}")
        if parts:
            return f"[{' '.join(parts)}] "
    except Exception:
        pass
    return ""


def log_chain_event(
    layer: str,
    event: str,
    **payload: Any,
):
    """记录结构化 chain 事件（JSONL）"""
    try:
        from .context import get_context
        ctx = get_context()
    except Exception:
        ctx = {}

    entry = {
        "timestamp": datetime.now().isoformat(),
        "service": "backend",
        "layer": layer,
        "event": event,
        "rid": ctx.get("rid"),
        "cid": ctx.get("cid"),
        "mid": ctx.get("mid"),
    }

    for key, value in payload.items():
        if value is not None:
            entry[key] = value

    logger.bind(chain_log=True).info(json.dumps(entry, ensure_ascii=False, default=str))


def log_request(
    method: str,
    path: str,
    body: Optional[dict] = None,
    query_params: Optional[dict] = None,
    cid: Optional[int] = None,
):
    """
    记录 API 请求
    
    示例:
        log_request("POST", "/api/chat/send/stream", {"cid": 123, "user_message": "hello"})
    """
    prefix = _get_trace_prefix()
    
    # 标准日志
    logger.info(f"{prefix}[REQ] {method} {path}")
    if body:
        logger.debug(f"{prefix}[REQ_BODY] {_safe_json(body)}")
    
    # 获取 request_id
    try:
        from .context import get_context
        ctx = get_context()
        rid = ctx.get("rid")
    except Exception:
        rid = None
    
    # 结构化日志（JSONL）
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "type": "request",
        "request_id": rid,
        "method": method,
        "path": path,
        "cid": cid,
        "body": body,
        "query_params": query_params,
    }
    logger.bind(request_log=True).info(json.dumps(log_entry, ensure_ascii=False, default=str))
    log_chain_event(
        layer="backend",
        event="request",
        method=method,
        path=path,
        params=query_params,
        body=body,
    )


def log_response(
    method: str,
    path: str,
    status_code: int,
    duration: float = 0,
    cid: Optional[int] = None,
    error: Optional[str] = None,
):
    """
    记录 API 响应
    
    示例:
        log_response("POST", "/api/chat/send/stream", 200, duration=1.23, cid=123)
    """
    prefix = _get_trace_prefix()
    
    # 标准日志
    if status_code >= 400:
        logger.warning(f"{prefix}[RES] {method} {path} | status={status_code} | duration={duration:.3f}s | error={error}")
    else:
        logger.info(f"{prefix}[RES] {method} {path} | status={status_code} | duration={duration:.3f}s")
    
    # 获取 request_id
    try:
        from .context import get_context
        ctx = get_context()
        rid = ctx.get("rid")
    except Exception:
        rid = None
    
    # 结构化日志（JSONL）
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "type": "response",
        "request_id": rid,
        "method": method,
        "path": path,
        "status_code": status_code,
        "duration": duration,
        "cid": cid,
        "error": error,
    }
    logger.bind(request_log=True).info(json.dumps(log_entry, ensure_ascii=False, default=str))
    log_chain_event(
        layer="backend",
        event="response",
        method=method,
        path=path,
        status_code=status_code,
        duration_ms=round(duration * 1000, 3),
        error=error,
    )


def log_call_agents(
    endpoint: str,
    payload: dict,
    cid: Optional[int] = None,
):
    """记录调用 Agents 服务"""
    prefix = _get_trace_prefix()
    logger.info(f"{prefix}[CALL_AGENTS] {endpoint}")
    logger.debug(f"{prefix}[CALL_AGENTS_BODY] {_safe_json(payload)}")
    log_chain_event(
        layer="backend",
        event="call_agents",
        name="agents.http",
        path=endpoint,
        params=payload,
        cid=cid,
    )


def log_store_message(
    cid: int,
    role: str,
    message_id: int,
    content_length: int,
):
    """记录消息存储"""
    prefix = _get_trace_prefix()
    logger.info(f"{prefix}[STORE] role={role} | msg_id={message_id} | len={content_length}")
    log_chain_event(
        layer="backend",
        event="store_message",
        name=role,
        message_id=message_id,
        content_length=content_length,
        cid=cid,
    )


# 导出
__all__ = [
    "logger",
    "log_chain_event",
    "log_request",
    "log_response", 
    "log_call_agents",
    "log_store_message",
]

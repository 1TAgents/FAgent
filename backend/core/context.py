"""
请求上下文管理 - 基于 contextvars 实现请求级别的上下文存储

使用方式:
    from backend.core.context import set_context, get_context, ctx_logger
    
    # 设置上下文
    set_context(rid="xxx", cid="yyy")
    
    # 获取上下文
    ctx = get_context()
    
    # 使用带上下文的日志
    ctx_logger.info("消息内容")  # 输出: [rid=xxx cid=yyy] 消息内容
"""
from contextvars import ContextVar
from typing import Optional, Dict, Any
import uuid
from loguru import logger


# 上下文变量
_request_context: ContextVar[Dict[str, Any]] = ContextVar("request_context", default={})


def generate_request_id() -> str:
    """生成短格式 request_id（UUID 前8位）"""
    return str(uuid.uuid4())[:8]


def set_context(
    rid: Optional[str] = None,
    cid: Optional[str] = None,
    **kwargs
) -> None:
    """
    设置请求上下文
    
    Args:
        rid: request_id，如果不提供则自动生成
        cid: conversation_id
        **kwargs: 其他自定义字段
    """
    ctx = _request_context.get().copy()
    
    if rid is not None:
        ctx["rid"] = rid
    elif "rid" not in ctx:
        ctx["rid"] = generate_request_id()
    
    if cid is not None:
        ctx["cid"] = cid
    
    ctx.update(kwargs)
    _request_context.set(ctx)


def get_context() -> Dict[str, Any]:
    """获取当前请求上下文"""
    return _request_context.get().copy()


def clear_context() -> None:
    """清空上下文"""
    _request_context.set({})


def format_context_prefix() -> str:
    """
    格式化上下文前缀
    
    Returns:
        格式化的字符串，如 "[rid=xxx cid=yyy]"
    """
    ctx = _request_context.get()
    if not ctx:
        return ""
    
    parts = []
    # 固定顺序：rid, cid, 其他
    if "rid" in ctx:
        parts.append(f"rid={ctx['rid']}")
    if "cid" in ctx:
        parts.append(f"cid={ctx['cid']}")
    
    # 其他字段
    for key, value in ctx.items():
        if key not in ("rid", "cid"):
            parts.append(f"{key}={value}")
    
    if parts:
        return f"[{' '.join(parts)}] "
    return ""


class ContextLogger:
    """
    带上下文的日志记录器
    
    自动在日志消息前添加上下文信息
    """
    
    def _log(self, level: str, message: str, *args, **kwargs):
        prefix = format_context_prefix()
        full_message = f"{prefix}{message}"
        getattr(logger.opt(depth=2), level)(full_message, *args, **kwargs)
    
    def debug(self, message: str, *args, **kwargs):
        self._log("debug", message, *args, **kwargs)
    
    def info(self, message: str, *args, **kwargs):
        self._log("info", message, *args, **kwargs)
    
    def warning(self, message: str, *args, **kwargs):
        self._log("warning", message, *args, **kwargs)
    
    def error(self, message: str, *args, **kwargs):
        self._log("error", message, *args, **kwargs)
    
    def critical(self, message: str, *args, **kwargs):
        self._log("critical", message, *args, **kwargs)


# 全局上下文日志实例
ctx_logger = ContextLogger()


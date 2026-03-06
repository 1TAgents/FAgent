"""
请求上下文管理 - Agents 服务

基于 contextvars 实现请求级别的上下文存储，
用于在整个请求链路中传递 request_id 和 cid。

使用方式:
    from agents.core.context import set_context, get_context, get_trace_prefix
    
    # 设置上下文（通常由中间件完成）
    set_context(rid="abc123", cid="5")
    
    # 获取上下文
    ctx = get_context()
    
    # 获取日志前缀
    prefix = get_trace_prefix()  # "[rid=abc123 cid=5] "
"""
from contextvars import ContextVar
from typing import Optional, Dict, Any
import uuid


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
        rid: request_id
        cid: conversation_id
        **kwargs: 其他自定义字段
    """
    ctx = _request_context.get().copy()
    
    if rid is not None:
        ctx["rid"] = rid
    
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


def get_trace_prefix() -> str:
    """
    获取追踪前缀
    
    Returns:
        格式化的字符串，如 "[rid=xxx cid=yyy] "
    """
    ctx = _request_context.get()
    if not ctx:
        return ""
    
    parts = []
    # 固定顺序：rid, cid, uid
    if ctx.get("rid"):
        parts.append(f"rid={ctx['rid']}")
    if ctx.get("cid"):
        parts.append(f"cid={ctx['cid']}")
    if ctx.get("uid"):
        parts.append(f"uid={ctx['uid']}")
    
    if parts:
        return f"[{' '.join(parts)}] "
    return ""

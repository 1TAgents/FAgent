"""
FastAPI 中间件 - 请求上下文处理

自动从请求 Header 获取或生成 request_id
"""
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from ..core.context import set_context, clear_context, generate_request_id, ctx_logger


class RequestContextMiddleware(BaseHTTPMiddleware):
    """
    请求上下文中间件
    
    - 从 Header 获取 X-Request-ID，如果没有则自动生成
    - 在请求开始时设置上下文
    - 在请求结束时清空上下文
    """
    
    async def dispatch(self, request: Request, call_next):
        # 获取或生成 request_id
        request_id = request.headers.get("X-Request-ID")
        if not request_id:
            request_id = generate_request_id()
        
        # 设置上下文
        set_context(rid=request_id)
        
        # 记录请求开始
        ctx_logger.info(f"请求开始 | {request.method} {request.url.path}")
        
        try:
            response = await call_next(request)
            ctx_logger.info(f"请求完成 | status={response.status_code}")
            return response
        except Exception as e:
            ctx_logger.error(f"请求异常 | error={str(e)}")
            raise
        finally:
            # 清空上下文
            clear_context()


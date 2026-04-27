"""
MCP Middleware - 限流和鉴权中间件
"""
import logging
import json
import time
from typing import Dict, Optional
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from collections import defaultdict

from agents.core.context import set_context, clear_context

logger = logging.getLogger(__name__)


class RequestContextMiddleware(BaseHTTPMiddleware):
    """
    请求上下文中间件

    从 Header 获取 rid/cid/mid，并在必要时从请求体补充 cid/mid。
    """

    async def dispatch(self, request: Request, call_next):
        rid = request.headers.get("X-Request-ID", "")
        cid = request.headers.get("X-CID")
        mid = request.headers.get("X-MID")

        if request.method in {"POST", "PUT", "PATCH"}:
            try:
                body = await request.body()
                if body:
                    body_data = json.loads(body.decode("utf-8"))
                    cid = cid or body_data.get("cid")
                    mid = mid or body_data.get("message_id")
            except Exception:
                pass

        set_context(
            rid=rid if rid else None,
            cid=str(cid) if cid else None,
            mid=str(mid) if mid else None,
        )

        try:
            return await call_next(request)
        finally:
            clear_context()


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    限流中间件
    
    基于 IP 地址进行限流
    """
    
    def __init__(
        self,
        app,
        requests_per_minute: int = 60,
        requests_per_hour: int = 1000
    ):
        """
        初始化限流器
        
        Args:
            requests_per_minute: 每分钟请求数限制
            requests_per_hour: 每小时请求数限制
        """
        super().__init__(app)
        self.rpm_limit = requests_per_minute
        self.rph_limit = requests_per_hour
        
        # 存储请求计数：{ip: [(timestamp, count)]}
        self._requests: Dict[str, list] = defaultdict(list)
    
    async def dispatch(self, request: Request, call_next):
        # 获取客户端 IP
        client_ip = self._get_client_ip(request)
        
        # 检查限流
        if not self._check_rate_limit(client_ip):
            logger.warning(f"限流触发 | ip={client_ip}")
            raise HTTPException(
                status_code=429,
                detail="Too many requests. Please try again later."
            )
        
        # 记录请求
        self._record_request(client_ip)
        
        # 继续处理
        response = await call_next(request)
        return response
    
    def _get_client_ip(self, request: Request) -> str:
        """获取客户端 IP"""
        # 检查 X-Forwarded-For
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        
        # 检查 X-Real-IP
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        #  fallback 到直接连接
        return request.client.host if request.client else "unknown"
    
    def _check_rate_limit(self, ip: str) -> bool:
        """检查是否超过限流"""
        now = time.time()
        minute_ago = now - 60
        hour_ago = now - 3600
        
        # 清理过期记录
        self._requests[ip] = [
            (ts, count) for ts, count in self._requests[ip]
            if ts > hour_ago
        ]
        
        # 统计请求数
        rpm = sum(count for ts, count in self._requests[ip] if ts > minute_ago)
        rph = sum(count for ts, count in self._requests[ip])
        
        # 检查是否超限
        if rpm >= self.rpm_limit:
            logger.warning(f"分钟限流 | ip={ip} | rpm={rpm}/{self.rpm_limit}")
            return False
        
        if rph >= self.rph_limit:
            logger.warning(f"小时限流 | ip={ip} | rph={rph}/{self.rph_limit}")
            return False
        
        return True
    
    def _record_request(self, ip: str):
        """记录请求"""
        now = time.time()
        self._requests[ip].append((now, 1))


class APIKeyMiddleware(BaseHTTPMiddleware):
    """
    API Key 鉴权中间件
    
    从 Header 中验证 API Key
    """
    
    def __init__(self, app, api_keys: Optional[list] = None):
        """
        初始化鉴权
        
        Args:
            api_keys: 有效的 API Key 列表
        """
        super().__init__(app)
        self.api_keys = set(api_keys) if api_keys else set()
        
        # 如果没有配置 API Key，则跳过鉴权
        self.enabled = len(self.api_keys) > 0
        
        if self.enabled:
            logger.info(f"API Key 鉴权已启用 | keys_count={len(self.api_keys)}")
        else:
            logger.warning("API Key 鉴权未配置，将跳过鉴权")
    
    async def dispatch(self, request: Request, call_next):
        # 如果未启用鉴权，直接通过
        if not self.enabled:
            return await call_next(request)
        
        # 跳过健康检查和工具列表接口
        if request.url.path in ["/health", "/tools", "/docs", "/openapi.json"]:
            return await call_next(request)
        
        # 获取 API Key
        api_key = request.headers.get("X-API-Key")
        
        if not api_key:
            logger.warning(f"缺少 API Key | path={request.url.path}")
            raise HTTPException(
                status_code=401,
                detail="Missing API Key. Please provide X-API-Key header."
            )
        
        if api_key not in self.api_keys:
            logger.warning(f"无效的 API Key | path={request.url.path}")
            raise HTTPException(
                status_code=403,
                detail="Invalid API Key."
            )
        
        # 鉴权通过
        return await call_next(request)


class RequestLogMiddleware(BaseHTTPMiddleware):
    """
    请求日志中间件
    
    记录所有请求的详细信息
    """
    
    async def dispatch(self, request: Request, call_next):
        # 记录请求
        start_time = time.time()
        
        response = await call_next(request)
        
        # 记录响应
        duration = time.time() - start_time
        logger.info(
            f"请求完成 | method={request.method} | path={request.url.path} | "
            f"status={response.status_code} | duration={duration:.3f}s"
        )
        
        return response

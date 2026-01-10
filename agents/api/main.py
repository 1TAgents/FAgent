"""
Agents FastAPI 主应用

独立的 Agents 服务，端口 8001

特性：
- SQLite 持久化缓存
- 按需加载，用到即缓存
- 完整日志记录
- 请求追踪（rid + cid）
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from .chat import router as chat_router
from .market import router as market_router
from .summary import router as summary_router

# 导入日志和上下文模块
from agents.core.logging import logger
from agents.core.context import set_context, clear_context


# ==================== 中间件 ====================

class RequestContextMiddleware(BaseHTTPMiddleware):
    """
    请求上下文中间件
    
    从 Header 获取 X-Request-ID，设置到上下文中
    注：cid 从 request body 获取，在具体 endpoint 中设置
    """
    
    async def dispatch(self, request: Request, call_next):
        # 从 Header 获取 request_id
        request_id = request.headers.get("X-Request-ID", "")
        
        # 设置上下文（只设置 rid）
        if request_id:
            set_context(rid=request_id)
        
        try:
            response = await call_next(request)
            return response
        finally:
            # 清空上下文
            clear_context()


# ==================== 生命周期管理 ====================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    from ..common.market.cache import market_cache
    
    logger.info("=" * 50)
    logger.info("FAgent Agents 服务启动中...")
    logger.info(f"日志目录: logs/agents/")
    logger.info(f"缓存状态: {market_cache.stats()}")
    logger.info("服务已就绪")
    logger.info("=" * 50)
    
    yield  # 应用运行中
    
    # 关闭时清理过期缓存
    logger.info("FAgent Agents 服务关闭中...")
    market_cache.cleanup_expired()
    logger.info("服务已关闭")


# ==================== FastAPI 应用 ====================

app = FastAPI(
    title="FAgent Agents API",
    description="智能股票交易助手 - Agents 服务",
    version="0.1.0",
    lifespan=lifespan,
)

# 中间件（注意顺序：先添加的后执行）
# 1. 请求上下文中间件
app.add_middleware(RequestContextMiddleware)

# 2. CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(chat_router)
app.include_router(market_router)
app.include_router(summary_router)


@app.get("/")
async def root():
    """根路径"""
    from ..common.market.cache import market_cache
    return {
        "service": "FAgent Agents",
        "version": "0.1.0",
        "docs": "/docs",
        "cache": market_cache.stats(),
    }


@app.get("/health")
async def health():
    """健康检查"""
    from ..common.market.cache import market_cache
    return {
        "status": "healthy",
        "service": "agents",
        "cache": market_cache.stats(),
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)

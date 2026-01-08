"""
Agents FastAPI 主应用

独立的 Agents 服务，端口 8001

特性：
- SQLite 持久化缓存
- 按需加载，用到即缓存
"""
import logging
from contextlib import asynccontextmanager

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .chat import router as chat_router
from .market import router as market_router
from .summary import router as summary_router


# ==================== 生命周期管理 ====================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    from ..common.market.cache import market_cache
    
    logging.info("=" * 50)
    logging.info("FAgent Agents 服务启动中...")
    logging.info(f"缓存状态: {market_cache.stats()}")
    logging.info("服务已就绪")
    logging.info("=" * 50)
    
    yield  # 应用运行中
    
    # 关闭时清理过期缓存
    logging.info("FAgent Agents 服务关闭中...")
    market_cache.cleanup_expired()
    logging.info("服务已关闭")


# ==================== FastAPI 应用 ====================

app = FastAPI(
    title="FAgent Agents API",
    description="智能股票交易助手 - Agents 服务",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS 配置
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

"""
FastAPI 主应用
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse
from .chat import router as chat_router
from .auth import router as auth_router
from .middleware import RequestContextMiddleware
from backend.core.logging import logger
from backend.core.rate_limiter import rate_limiter


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时
    logger.info("=" * 50)
    logger.info("FAgent Backend 服务启动中...")
    logger.info(f"日志目录: logs/backend/")
    logger.info(f"限流规则: {len(rate_limiter._rules)} 条")
    for rule in rate_limiter._rules:
        logger.info(f"  - {rule.name}: {rule.max_requests} req / {rule.window_seconds}s")
    logger.info("服务已就绪")
    logger.info("=" * 50)

    yield

    # 关闭时
    logger.info("FAgent Backend 服务关闭中...")
    logger.info("服务已关闭")


app = FastAPI(
    title="FAgent API",
    description="智能股票交易助手 API",
    version="0.1.0",
    lifespan=lifespan,
)


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    """HTTP 请求限流中间件。"""
    path = request.url.path

    # 跳过健康检查和文档路径
    if path in ("/health", "/", "/docs", "/openapi.json", "/redoc"):
        return await call_next(request)

    # 匹配限流规则
    rule = rate_limiter.match_rule(path)
    if rule:
        # 使用客户端 IP 或 User ID 作为标识
        client_id = request.headers.get("x-user-id") or request.client.host
        allowed, meta = rate_limiter.is_allowed(rule.name, client_id)
        if not allowed:
            logger.warning(f"限流触发 | client={client_id} | rule={rule.name}")
            return JSONResponse(
                status_code=429,
                content={
                    "error": "请求过于频繁，请稍后再试",
                    "limit": meta["limit"],
                    "reset_seconds": meta["reset_seconds"],
                },
                headers={
                    "X-RateLimit-Limit": str(meta["limit"]),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(meta["reset_seconds"]),
                },
            )
        # 附加限流头
        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(meta["limit"])
        response.headers["X-RateLimit-Remaining"] = str(meta["remaining"])
        return response

    return await call_next(request)


# 配置中间件（注意顺序：先添加的后执行）
# 1. 请求上下文中间件
app.add_middleware(RequestContextMiddleware)

# 2. CORS 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 开发环境允许所有来源
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(chat_router)
app.include_router(auth_router)


@app.get("/")
async def root():
    """根路径"""
    return {
        "message": "FAgent API",
        "version": "0.1.0",
        "docs": "/docs"
    }


@app.get("/health")
async def health():
    """健康检查"""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)


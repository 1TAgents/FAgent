"""
MCP Server - Model Context Protocol 服务

提供标准化的工具调用接口，供所有 Agent 使用

启动命令:
    cd agents && python -m uvicorn mcp.server:app --reload --port 8002

API 端点:
    GET  /tools          - 列出所有可用工具
    POST /tool/call      - 调用工具
    GET  /health         - 健康检查
"""
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from .models import ToolCallRequest, ToolCallResponse, ToolDefinition
from .tools import tool_registry
from .adapters.akshare_adapter import AKShareAdapter
from .middleware import RateLimitMiddleware, APIKeyMiddleware, RequestLogMiddleware

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
)
logger = logging.getLogger(__name__)


# ==================== 应用生命周期 ====================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时
    logger.info("=" * 50)
    logger.info("FAgent MCP Server 启动中...")
    
    # 初始化工具
    adapter = AKShareAdapter()
    
    # 注册工具 - 实时行情
    tool_registry.register(
        name="stock_quote",
        handler=adapter.get_quote,
        description="获取股票实时行情（价格、涨跌幅、成交量等）",
        parameters={
            "type": "object",
            "properties": {
                "symbol": {
                    "type": "string",
                    "description": "股票代码（如：600519, AAPL）"
                },
                "market": {
                    "type": "string",
                    "description": "市场类型",
                    "enum": ["A", "US", "HK"],
                    "default": "A"
                }
            },
            "required": ["symbol"]
        }
    )
    
    # 注册工具 - K 线数据
    tool_registry.register(
        name="stock_kline",
        handler=adapter.get_kline,
        description="获取股票 K 线数据（支持日线/周线/月线等周期）",
        parameters={
            "type": "object",
            "properties": {
                "symbol": {
                    "type": "string",
                    "description": "股票代码"
                },
                "period": {
                    "type": "string",
                    "description": "K 线周期",
                    "enum": ["daily", "weekly", "monthly", "1m", "5m", "15m", "30m", "60m"],
                    "default": "daily"
                },
                "count": {
                    "type": "integer",
                    "description": "返回条数",
                    "default": 100,
                    "minimum": 1,
                    "maximum": 1000
                },
                "market": {
                    "type": "string",
                    "description": "市场类型",
                    "enum": ["A", "US", "HK"],
                    "default": "A"
                }
            },
            "required": ["symbol"]
        }
    )
    
    # 注册工具 - 股票搜索
    tool_registry.register(
        name="stock_search",
        handler=adapter.search,
        description="根据关键词搜索股票（支持代码或名称搜索）",
        parameters={
            "type": "object",
            "properties": {
                "keyword": {
                    "type": "string",
                    "description": "搜索关键词（股票代码或名称）"
                },
                "market": {
                    "type": "string",
                    "description": "市场类型",
                    "enum": ["A", "US", "HK"],
                    "default": "A"
                },
                "limit": {
                    "type": "integer",
                    "description": "返回数量",
                    "default": 10,
                    "minimum": 1,
                    "maximum": 50
                }
            },
            "required": ["keyword"]
        }
    )
    
    # 注册工具 - 资金流向
    tool_registry.register(
        name="stock_fund_flow",
        handler=adapter.get_fund_flow,
        description="获取股票资金流向数据（主力/散户流入流出）",
        parameters={
            "type": "object",
            "properties": {
                "symbol": {
                    "type": "string",
                    "description": "股票代码"
                },
                "market": {
                    "type": "string",
                    "description": "市场类型",
                    "enum": ["A", "US", "HK"],
                    "default": "A"
                }
            },
            "required": ["symbol"]
        }
    )
    
    # 注册工具 - 股票排行
    tool_registry.register(
        name="stock_rank",
        handler=adapter.get_stock_rank,
        description="获取股票排行榜（涨幅榜/跌幅榜/成交额榜）",
        parameters={
            "type": "object",
            "properties": {
                "rank_type": {
                    "type": "string",
                    "description": "排行类型",
                    "enum": ["gain", "loss", "turnover", "volume"],
                    "default": "gain"
                },
                "market": {
                    "type": "string",
                    "description": "市场类型",
                    "enum": ["A", "US", "HK"],
                    "default": "A"
                },
                "limit": {
                    "type": "integer",
                    "description": "返回数量",
                    "default": 20,
                    "minimum": 1,
                    "maximum": 100
                }
            },
            "required": ["rank_type"]
        }
    )
    
    # 注册工具 - 财务指标
    tool_registry.register(
        name="stock_financial",
        handler=adapter.get_financial_indicator,
        description="获取股票财务指标（市盈率/市净率/ROE 等）",
        parameters={
            "type": "object",
            "properties": {
                "symbol": {
                    "type": "string",
                    "description": "股票代码"
                },
                "market": {
                    "type": "string",
                    "description": "市场类型",
                    "enum": ["A", "US", "HK"],
                    "default": "A"
                }
            },
            "required": ["symbol"]
        }
    )
    
    logger.info(f"已注册 {tool_registry.count} 个工具")
    logger.info("日志目录：logs/mcp/")
    logger.info("限流中间件已启用 | 60 次/分钟，1000 次/小时")
    
    # API Key 鉴权检查
    import os
    api_keys_str = os.getenv("MCP_API_KEYS", "")
    api_keys = [k.strip() for k in api_keys_str.split(",") if k.strip()]
    if api_keys:
        logger.info(f"API Key 鉴权已启用 | keys_count={len(api_keys)}")
    else:
        logger.warning("API Key 鉴权未配置（设置 MCP_API_KEYS 环境变量启用）")
    
    logger.info("服务已就绪")
    logger.info("=" * 50)
    
    yield
    
    # 关闭时
    logger.info("FAgent MCP Server 关闭中...")
    logger.info("服务已关闭")


# ==================== FastAPI 应用 ====================

app = FastAPI(
    title="FAgent MCP Server",
    description="Model Context Protocol 服务 - 提供标准化的金融数据工具接口",
    version="1.0.0",
    lifespan=lifespan
)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 限流中间件（60 次/分钟，1000 次/小时）
app.add_middleware(RateLimitMiddleware, requests_per_minute=60, requests_per_hour=1000)

# API Key 鉴权（可选）
import os
api_keys_str = os.getenv("MCP_API_KEYS", "")
api_keys = [k.strip() for k in api_keys_str.split(",") if k.strip()]
if api_keys:
    app.add_middleware(APIKeyMiddleware, api_keys=api_keys)

# 请求日志中间件
app.add_middleware(RequestLogMiddleware)


# ==================== API 端点 ====================

@app.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "tools_count": tool_registry.count
    }


@app.get("/tools", response_model=list[ToolDefinition])
async def list_tools():
    """
    列出所有可用工具
    
    供 Agent 发现和使用
    """
    return tool_registry.list_all(enabled_only=True)


@app.post("/tool/call", response_model=ToolCallResponse)
async def call_tool(request: ToolCallRequest):
    """
    调用工具
    
    Args:
        request: 工具调用请求
        
    Returns:
        工具调用结果
        
    Examples:
        POST /tool/call
        {
            "tool_name": "stock_quote",
            "arguments": {"symbol": "600519", "market": "A"}
        }
    """
    try:
        # 获取工具
        tool = tool_registry.get(request.tool_name)
        
        # 调用工具
        result = await tool(**request.arguments)
        
        logger.info(f"工具调用成功 | tool={request.tool_name} | args={request.arguments}")
        
        return ToolCallResponse(
            success=True,
            data=result
        )
        
    except KeyError as e:
        logger.warning(f"工具不存在 | tool={request.tool_name}")
        return ToolCallResponse(
            success=False,
            error=f"工具不存在：{request.tool_name}"
        )
        
    except Exception as e:
        logger.error(f"工具调用失败 | tool={request.tool_name} | error={e}")
        return ToolCallResponse(
            success=False,
            error=str(e)
        )


@app.get("/tool/{tool_name}")
async def get_tool_info(tool_name: str):
    """获取单个工具详情"""
    if not tool_registry.has(tool_name):
        raise HTTPException(status_code=404, detail=f"工具不存在：{tool_name}")
    
    tools = [t for t in tool_registry.list_all(enabled_only=False) if t.name == tool_name]
    if tools:
        return tools[0]
    raise HTTPException(status_code=404, detail="工具未找到")


# ==================== 主程序 ====================

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8002)

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
import time
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from .models import ToolCallRequest, ToolCallResponse, ToolDefinition
from .tools import tool_registry
from .adapters.akshare_adapter import AKShareAdapter
from .middleware import RateLimitMiddleware, APIKeyMiddleware, RequestLogMiddleware, RequestContextMiddleware
from .trace import log_chain_event
from agents.data_service import get_data_service
from agents.backtest.api import run_backtest, list_strategies
from agents.backtest.models import BacktestRequest, StrategyConfig

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
    
    # 初始化数据服务
    data_service = get_data_service(
        db_path="data/stock_data.db",
        redis_url="redis://localhost:6379",
        cache_enabled=True,
        auto_sync=True
    )
    logger.info("数据服务初始化完成")
    
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
    
    # 注册工具 - 数据服务（使用 DataService）
    tool_registry.register(
        name="data_quote",
        handler=data_service.get_quote,
        description="获取股票行情（优先从数据库/缓存，实时为辅）",
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
    
    tool_registry.register(
        name="data_kline",
        handler=data_service.get_kline,
        description="获取 K 线数据（从数据库，自动补充缺失）",
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
                    "enum": ["daily", "weekly", "monthly"],
                    "default": "daily"
                },
                "count": {
                    "type": "integer",
                    "description": "返回条数",
                    "default": 100
                }
            },
            "required": ["symbol"]
        }
    )
    
    tool_registry.register(
        name="data_sync",
        handler=data_service.sync_single_stock,
        description="手动同步单只股票数据",
        parameters={
            "type": "object",
            "properties": {
                "symbol": {
                    "type": "string",
                    "description": "股票代码"
                }
            },
            "required": ["symbol"]
        }
    )
    
    # ==================== 新增工具：指数行情 ====================
    
    tool_registry.register(
        name="index_quote",
        handler=adapter.get_index_quote,
        description="获取主流指数实时行情（沪深 300/中证 500/上证 50/科创 50/创业板指等）",
        parameters={
            "type": "object",
            "properties": {
                "symbol": {
                    "type": "string",
                    "description": "指数代码（如：000300=沪深 300, 000001=上证指数，000905=中证 500）"
                }
            },
            "required": ["symbol"]
        }
    )
    
    # ==================== 新增工具：指数 K 线 ====================
    
    tool_registry.register(
        name="index_kline",
        handler=adapter.get_index_kline,
        description="获取指数 K 线数据（支持日线/周线/月线）",
        parameters={
            "type": "object",
            "properties": {
                "symbol": {
                    "type": "string",
                    "description": "指数代码"
                },
                "period": {
                    "type": "string",
                    "description": "K 线周期",
                    "enum": ["daily", "weekly", "monthly"],
                    "default": "daily"
                },
                "count": {
                    "type": "integer",
                    "description": "返回条数",
                    "default": 100,
                    "minimum": 1,
                    "maximum": 1000
                }
            },
            "required": ["symbol"]
        }
    )
    
    # ==================== 新增工具：行业板块行情 ====================
    
    tool_registry.register(
        name="industry_quote",
        handler=adapter.get_industry_quote,
        description="获取行业板块行情（可查询单个行业或所有行业涨幅榜）",
        parameters={
            "type": "object",
            "properties": {
                "industry_name": {
                    "type": "string",
                    "description": "行业名称（如：半导体、银行、医药；不传则返回所有行业）"
                }
            },
            "required": []
        }
    )
    
    # ==================== 新增工具：行业 K 线 ====================
    
    tool_registry.register(
        name="industry_kline",
        handler=adapter.get_industry_kline,
        description="获取行业指数 K 线数据（支持日线/周线/月线）",
        parameters={
            "type": "object",
            "properties": {
                "industry_name": {
                    "type": "string",
                    "description": "行业名称（如：半导体、银行、医药）"
                },
                "period": {
                    "type": "string",
                    "description": "K 线周期",
                    "enum": ["daily", "weekly", "monthly"],
                    "default": "daily"
                },
                "count": {
                    "type": "integer",
                    "description": "返回条数",
                    "default": 100,
                    "minimum": 1,
                    "maximum": 1000
                }
            },
            "required": ["industry_name"]
        }
    )
    
    # ==================== 新增工具：行业成分股 ====================
    
    tool_registry.register(
        name="industry_detail",
        handler=adapter.get_industry_detail,
        description="获取行业成分股列表（包含成分股代码、名称、权重等）",
        parameters={
            "type": "object",
            "properties": {
                "industry_name": {
                    "type": "string",
                    "description": "行业名称（如：半导体、银行、医药）"
                }
            },
            "required": ["industry_name"]
        }
    )
    
    # ==================== 新增工具：龙虎榜 ====================
    
    tool_registry.register(
        name="stock_bill",
        handler=adapter.get_stock_bill,
        description="获取龙虎榜数据（每日榜单或个股历史）",
        parameters={
            "type": "object",
            "properties": {
                "date": {
                    "type": "string",
                    "description": "日期（YYYY-MM-DD 格式，不传则默认最近一个交易日）"
                },
                "symbol": {
                    "type": "string",
                    "description": "股票代码（可选，不传则返回全市场龙虎榜）"
                }
            },
            "required": []
        }
    )
    
    # ==================== 新增工具：涨跌停统计 ====================
    
    tool_registry.register(
        name="stock_limit_up",
        handler=adapter.get_limit_up_stats,
        description="获取涨跌停池统计（涨停/跌停数量及详情）",
        parameters={
            "type": "object",
            "properties": {
                "date": {
                    "type": "string",
                    "description": "日期（YYYY-MM-DD 格式，不传则默认最近一个交易日）"
                }
            },
            "required": []
        }
    )
    
    # ==================== 新增工具：大宗交易 ====================
    
    tool_registry.register(
        name="stock_block_trade",
        handler=adapter.get_block_trade,
        description="获取大宗交易数据（全市场或单只股票）",
        parameters={
            "type": "object",
            "properties": {
                "date": {
                    "type": "string",
                    "description": "日期（YYYY-MM-DD 格式，不传则默认最近一个交易日）"
                },
                "symbol": {
                    "type": "string",
                    "description": "股票代码（可选）"
                }
            },
            "required": []
        }
    )
    
    # ==================== 新增工具：融资融券 ====================
    
    tool_registry.register(
        name="stock_margin",
        handler=adapter.get_margin_data,
        description="获取融资融券数据（市场汇总或个股历史）",
        parameters={
            "type": "object",
            "properties": {
                "symbol": {
                    "type": "string",
                    "description": "股票代码（可选，不传则返回市场汇总）"
                },
                "market": {
                    "type": "string",
                    "description": "市场（SH=上交所，SZ=深交所）",
                    "enum": ["SH", "SZ"],
                    "default": "SH"
                },
                "date": {
                    "type": "string",
                    "description": "日期（可选）"
                }
            },
            "required": []
        }
    )
    
    # ==================== 新增工具：策略回测 ====================
    
    async def run_backtest_tool(
        strategy_name: str,
        symbol: str,
        start_date: str,
        end_date: str,
        initial_capital: float = 100000.0,
        params: dict = None,
        metadata: dict = None,
    ) -> dict:
        """回测工具包装器"""
        from agents.backtest.api import run_backtest
        from agents.backtest.models import BacktestRequest
        
        request = BacktestRequest(
            strategy_name=strategy_name,
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
            initial_capital=initial_capital,
            params=params or {},
            metadata=metadata or {},
        )
        
        response = await run_backtest(request)
        
        if response.success:
            return {
                "success": True,
                "report": response.report.model_dump() if response.report else None,
                "summary": response.report.summary() if response.report else None,
                "report_id": response.report_id,
                "artifacts_dir": response.artifacts_dir,
                "engine": response.engine,
            }
        else:
            return {
                "success": False,
                "error": response.error
            }
    
    tool_registry.register(
        name="backtest_run",
        handler=run_backtest_tool,
        description="执行策略回测（支持双均线/RSI/布林带等策略）",
        parameters={
            "type": "object",
            "properties": {
                "strategy_name": {
                    "type": "string",
                    "description": "策略名称（dual_ma/rsi/bollinger）",
                    "enum": ["dual_ma", "rsi", "bollinger"]
                },
                "symbol": {
                    "type": "string",
                    "description": "回测标的（股票代码）"
                },
                "start_date": {
                    "type": "string",
                    "description": "开始日期（YYYY-MM-DD）"
                },
                "end_date": {
                    "type": "string",
                    "description": "结束日期（YYYY-MM-DD）"
                },
                "initial_capital": {
                    "type": "number",
                    "description": "初始资金",
                    "default": 100000.0
                },
                "params": {
                    "type": "object",
                    "description": "策略参数（如 short_period, long_period 等）",
                    "default": {}
                },
                "metadata": {
                    "type": "object",
                    "description": "附加元数据（如 query/rid/cid）",
                    "default": {}
                }
            },
            "required": ["strategy_name", "symbol", "start_date", "end_date"]
        }
    )
    
    async def list_strategies_tool() -> dict:
        """列出策略工具包装器"""
        from agents.backtest.strategies import STRATEGY_REGISTRY
        
        strategies = {}
        for name, cls in STRATEGY_REGISTRY.items():
            strategies[name] = {
                "name": cls.__name__,
                "description": cls.__doc__.split('\n')[0] if cls.__doc__ else "",
            }
        
        return {"strategies": strategies}
    
    tool_registry.register(
        name="backtest_strategies",
        handler=list_strategies_tool,
        description="列出所有可用回测策略",
        parameters={
            "type": "object",
            "properties": {}
        }
    )
    
    # ==================== 新增工具：参数网格搜索 ====================
    
    async def backtest_grid_search(
        strategy_name: str,
        symbol: str,
        start_date: str,
        end_date: str,
        param_grid: dict,
        initial_capital: float = 100000.0
    ) -> dict:
        """网格搜索工具包装器"""
        from agents.backtest.api import grid_search
        
        response = await grid_search(
            strategy_name=strategy_name,
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
            param_grid=param_grid,
            initial_capital=initial_capital
        )
        
        if response.get('success'):
            best = response.get('best_result', {})
            return {
                "success": True,
                "best_params": response.get('best_params'),
                "best_performance": {
                    "sharpe_ratio": best.get('sharpe_ratio', 0),
                    "total_returns": f"{best.get('total_returns', 0):.2%}",
                    "max_drawdown": f"{best.get('max_drawdown', 0):.2%}"
                },
                "total_combinations": response.get('total_combinations'),
                "elapsed_seconds": response.get('elapsed_seconds'),
                "top_results": response.get('all_results', [])[:5]
            }
        else:
            return {
                "success": False,
                "error": response.get('error')
            }
    
    tool_registry.register(
        name="backtest_grid_search",
        handler=backtest_grid_search,
        description="参数网格搜索（自动寻找最优策略参数）",
        parameters={
            "type": "object",
            "properties": {
                "strategy_name": {
                    "type": "string",
                    "description": "策略名称（dual_ma/rsi/macd/bollinger）",
                    "enum": ["dual_ma", "rsi", "macd", "bollinger"]
                },
                "symbol": {
                    "type": "string",
                    "description": "股票代码"
                },
                "start_date": {
                    "type": "string",
                    "description": "开始日期（YYYY-MM-DD）"
                },
                "end_date": {
                    "type": "string",
                    "description": "结束日期（YYYY-MM-DD）"
                },
                "param_grid": {
                    "type": "object",
                    "description": "参数网格（如 {\"short_period\": [5, 10, 20], \"long_period\": [20, 50, 100]}）"
                },
                "initial_capital": {
                    "type": "number",
                    "description": "初始资金",
                    "default": 100000.0
                }
            },
            "required": ["strategy_name", "symbol", "start_date", "end_date", "param_grid"]
        }
    )
    
    logger.info(f"已注册 {tool_registry.count} 个工具")
    logger.info("日志目录：logs/mcp/")
    logger.info("数据服务：SQLite + Redis 缓存 + 定时同步")
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

# 请求上下文中间件
app.add_middleware(RequestContextMiddleware)

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
    start_time = time.time()
    log_chain_event(
        layer="mcp",
        event="tool_call",
        name=request.tool_name,
        params=request.arguments,
    )

    try:
        # 获取工具
        tool = tool_registry.get(request.tool_name)
        
        # 调用工具
        result = await tool(**request.arguments)
        
        logger.info(f"工具调用成功 | tool={request.tool_name} | args={request.arguments}")
        log_chain_event(
            layer="mcp",
            event="tool_result",
            name=request.tool_name,
            success=True,
            duration_ms=round((time.time() - start_time) * 1000, 3),
            result={
                "keys": sorted(result.keys()) if isinstance(result, dict) else None,
                "items_count": len(result.get("items", [])) if isinstance(result, dict) and isinstance(result.get("items"), list) else None,
            },
        )
        
        return ToolCallResponse(
            success=True,
            data=result
        )
        
    except KeyError as e:
        logger.warning(f"工具不存在 | tool={request.tool_name}")
        log_chain_event(
            layer="mcp",
            event="tool_result",
            name=request.tool_name,
            success=False,
            error=f"工具不存在：{request.tool_name}",
            duration_ms=round((time.time() - start_time) * 1000, 3),
        )
        return ToolCallResponse(
            success=False,
            error=f"工具不存在：{request.tool_name}"
        )
        
    except Exception as e:
        logger.error(f"工具调用失败 | tool={request.tool_name} | error={e}")
        log_chain_event(
            layer="mcp",
            event="tool_result",
            name=request.tool_name,
            success=False,
            error=str(e),
            duration_ms=round((time.time() - start_time) * 1000, 3),
        )
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

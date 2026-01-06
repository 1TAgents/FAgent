"""
Market API - 行情数据接口

提供行情数据的 HTTP API，供 Backend 和前端调用
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List
from enum import Enum

from ..subagents import market_subagent
from ..subagents.market_agent import MarketQuery, MarketIntent
from ..common.market import KLinePeriod

router = APIRouter(prefix="/market", tags=["market"])


# ==================== Request/Response Models ====================

class QuoteResponse(BaseModel):
    """行情响应"""
    success: bool
    data: Optional[dict] = None
    summary: str = ""
    error: Optional[str] = None


class KLineRequest(BaseModel):
    """K线请求"""
    symbol: str
    period: str = "daily"  # daily, weekly, 5min, 15min, 30min, 60min
    count: int = 30


class SearchResponse(BaseModel):
    """搜索响应"""
    success: bool
    results: List[dict] = []
    summary: str = ""
    error: Optional[str] = None


class AnalysisResponse(BaseModel):
    """分析响应"""
    success: bool
    data: Optional[dict] = None
    summary: str = ""
    error: Optional[str] = None


# ==================== API Endpoints ====================

@router.get("/quote/{symbol}", response_model=QuoteResponse)
async def get_quote(symbol: str):
    """
    获取股票实时行情
    
    - **symbol**: 股票代码（A股如 600519，美股如 AAPL）
    """
    query = MarketQuery(
        intent=MarketIntent.GET_QUOTE,
        symbol=symbol,
    )
    result = market_subagent.process(query)
    
    return QuoteResponse(
        success=result.success,
        data=result.data,
        summary=result.summary,
        error=result.error,
    )


@router.get("/kline/{symbol}", response_model=QuoteResponse)
async def get_kline(
    symbol: str,
    period: str = Query("daily", description="K线周期: daily, weekly, 5min, 15min, 30min, 60min"),
    count: int = Query(30, description="返回条数", ge=1, le=500),
):
    """
    获取股票 K 线数据
    
    - **symbol**: 股票代码
    - **period**: K线周期
    - **count**: 返回条数
    """
    # 映射周期
    period_map = {
        "daily": KLinePeriod.DAILY,
        "weekly": KLinePeriod.WEEKLY,
        "monthly": KLinePeriod.MONTHLY,
        "1min": KLinePeriod.MIN_1,
        "5min": KLinePeriod.MIN_5,
        "15min": KLinePeriod.MIN_15,
        "30min": KLinePeriod.MIN_30,
        "60min": KLinePeriod.MIN_60,
    }
    
    kline_period = period_map.get(period, KLinePeriod.DAILY)
    
    query = MarketQuery(
        intent=MarketIntent.GET_KLINE,
        symbol=symbol,
        period=kline_period,
        count=count,
    )
    result = market_subagent.process(query)
    
    return QuoteResponse(
        success=result.success,
        data=result.data,
        summary=result.summary,
        error=result.error,
    )


@router.get("/search", response_model=SearchResponse)
async def search_stock(
    keyword: str = Query(..., description="搜索关键词（代码或名称）"),
    limit: int = Query(10, description="返回条数", ge=1, le=50),
):
    """
    搜索股票
    
    - **keyword**: 搜索关键词
    - **limit**: 返回条数
    """
    query = MarketQuery(
        intent=MarketIntent.SEARCH_STOCK,
        keyword=keyword,
    )
    result = market_subagent.process(query)
    
    return SearchResponse(
        success=result.success,
        results=result.data.get("results", []) if result.data else [],
        summary=result.summary,
        error=result.error,
    )


@router.get("/analysis/{symbol}", response_model=AnalysisResponse)
async def analyze_trend(
    symbol: str,
    days: int = Query(30, description="分析天数", ge=5, le=120),
):
    """
    股票趋势分析
    
    - **symbol**: 股票代码
    - **days**: 分析的历史天数
    """
    query = MarketQuery(
        intent=MarketIntent.ANALYZE_TREND,
        symbol=symbol,
        count=days,
    )
    result = market_subagent.process(query)
    
    return AnalysisResponse(
        success=result.success,
        data=result.data,
        summary=result.summary,
        error=result.error,
    )


# ==================== 便捷接口（返回纯文本摘要） ====================

@router.get("/quick/quote/{symbol}")
async def quick_quote(symbol: str) -> dict:
    """快速获取行情摘要（供 LLM 调用）"""
    summary = market_subagent.quick_quote(symbol)
    return {"summary": summary}


@router.get("/quick/analysis/{symbol}")
async def quick_analysis(symbol: str) -> dict:
    """快速趋势分析（供 LLM 调用）"""
    summary = market_subagent.quick_analysis(symbol)
    return {"summary": summary}


# ==================== 缓存管理 ====================

@router.get("/cache/stats")
async def cache_stats() -> dict:
    """获取缓存统计信息"""
    from ..common.market.cache import market_cache
    return market_cache.stats()


@router.get("/cache/keys")
async def cache_keys() -> dict:
    """获取所有缓存 key"""
    from ..common.market.cache import market_cache
    return {"keys": market_cache.keys()}


@router.delete("/cache/clear")
async def clear_cache() -> dict:
    """清空缓存"""
    from ..common.market.cache import market_cache
    market_cache.clear()
    return {"message": "缓存已清空"}


@router.post("/cache/cleanup")
async def cleanup_cache() -> dict:
    """清理过期缓存"""
    from ..common.market.cache import market_cache
    market_cache.cleanup_expired()
    return {"message": "过期缓存已清理", "stats": market_cache.stats()}


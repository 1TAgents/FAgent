"""
Market Service - 行情数据服务

提供股票行情数据的统一访问层：
- 实时行情查询
- K线历史数据
- 股票搜索
- 技术指标计算

数据源：AKShare（开源免费，支持 A股/港股/美股）
"""

from .service import MarketService, market_service
from .models import StockQuote, KLineData, StockInfo, Market, KLinePeriod

__all__ = [
    "MarketService",
    "market_service",
    "StockQuote",
    "KLineData",
    "StockInfo",
    "Market",
    "KLinePeriod",
]


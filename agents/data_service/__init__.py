"""
Data Service - 数据服务层

提供统一的股票数据访问接口，整合缓存、数据库、外部数据源

架构：
┌─────────────────┐
│  DataService    │  ← 统一接口
└────────┬────────┘
         │
    ┌────┴────┐
    │         │
┌───▼───┐ ┌──▼──────┐
│ Cache │ │Database │  ← 分层存储
│(Redis)│ │(SQLite) │
└───┬───┘ └───┬─────┘
    │         │
    └────┬────┘
         │
    ┌────▼────┐
    │  Sync   │  ← 定时同步
    │ Manager │
    └────┬────┘
         │
    ┌────▼────┐
    │ AKShare │  ← 外部数据源
    └─────────┘
"""

from .service import DataService, get_data_service
from .database import StockDatabase
from .cache import DataCache
from .sync import DataSyncManager

__all__ = [
    "DataService",
    "get_data_service",
    "StockDatabase",
    "DataCache",
    "DataSyncManager",
]

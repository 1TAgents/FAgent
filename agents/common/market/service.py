"""
Market Service - 行情数据服务

提供行情数据的业务层封装，供所有 Agent 调用
"""

import logging
from typing import Optional, List
from datetime import datetime

from .client import get_client, AKShareClient
from ...core.logging import log_chain_event
from .models import (
    StockQuote,
    KLineData,
    StockInfo,
    Market,
    KLinePeriod,
)

logger = logging.getLogger(__name__)


class MarketService:
    """
    行情服务
    
    统一的行情数据访问层，封装数据源调用
    """
    
    def __init__(self):
        self._client: Optional[AKShareClient] = None
        logger.info("MarketService 初始化")
    
    @property
    def client(self) -> AKShareClient:
        """延迟加载客户端"""
        if self._client is None:
            self._client = get_client()
        return self._client
    
    # ==================== 实时行情 ====================
    
    def get_quote(self, symbol: str, market: Market = None) -> Optional[StockQuote]:
        """
        获取股票实时行情
        
        Args:
            symbol: 股票代码
            market: 市场类型（自动识别：6位数字=A股，字母=美股）
            
        Returns:
            StockQuote 或 None
        """
        # 自动识别市场
        if market is None:
            market = self._detect_market(symbol)
        
        logger.debug(f"获取行情 | symbol={symbol} | market={market.value}")
        log_chain_event(
            layer="market_service",
            event="call",
            name="get_quote",
            params={
                "symbol": symbol,
                "market": market.value,
            },
        )
        
        if market == Market.A_SHARE:
            result = self.client.get_a_share_quote(symbol)
        elif market == Market.US:
            result = self.client.get_us_stock_quote(symbol)
        else:
            logger.warning(f"暂不支持的市场: {market}")
            result = None

        log_chain_event(
            layer="market_service",
            event="result",
            name="get_quote",
            success=result is not None,
            result={
                "symbol": result.symbol,
                "name": result.name,
            } if result else None,
        )
        return result
    
    def get_quote_summary(self, symbol: str) -> str:
        """
        获取行情摘要（供 LLM 使用）
        
        Args:
            symbol: 股票代码
            
        Returns:
            行情摘要文本
        """
        quote = self.get_quote(symbol)
        if quote:
            return quote.summary()
        else:
            return f"未能获取 {symbol} 的行情数据"
    
    # ==================== K线数据 ====================
    
    def get_kline(
        self,
        symbol: str,
        period: KLinePeriod = KLinePeriod.DAILY,
        count: int = 100,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> Optional[KLineData]:
        """
        获取 K 线数据
        
        Args:
            symbol: 股票代码
            period: K线周期
            count: 返回条数
            start_date: 开始日期 (YYYYMMDD)
            end_date: 结束日期 (YYYYMMDD)
            
        Returns:
            KLineData 或 None
        """
        market = self._detect_market(symbol)
        logger.debug(f"获取K线 | symbol={symbol} | period={period.value} | count={count}")
        log_chain_event(
            layer="market_service",
            event="call",
            name="get_kline",
            params={
                "symbol": symbol,
                "market": market.value,
                "period": period.value,
                "count": count,
                "start_date": start_date,
                "end_date": end_date,
            },
        )
        
        if market == Market.A_SHARE:
            result = self.client.get_a_share_kline(
                symbol=symbol,
                period=period,
                start_date=start_date,
                end_date=end_date,
                count=count,
            )
        else:
            logger.warning(f"暂不支持 {market.value} 的 K 线数据")
            result = None

        log_chain_event(
            layer="market_service",
            event="result",
            name="get_kline",
            success=result is not None,
            result={
                "symbol": result.symbol,
                "period": result.period.value,
                "count": len(result.data),
            } if result else None,
        )
        return result
    
    def get_kline_summary(
        self, 
        symbol: str, 
        period: KLinePeriod = KLinePeriod.DAILY,
        recent_days: int = 5
    ) -> str:
        """
        获取 K 线摘要（供 LLM 使用）
        
        Args:
            symbol: 股票代码
            period: K线周期
            recent_days: 最近多少个交易日
            
        Returns:
            K线摘要文本
        """
        kline = self.get_kline(symbol, period, count=recent_days + 10)
        if kline:
            return kline.summary(recent_days)
        else:
            return f"未能获取 {symbol} 的 K 线数据"
    
    # ==================== 股票搜索 ====================
    
    def search(self, keyword: str, market: Market = None, limit: int = 10) -> List[StockInfo]:
        """
        搜索股票
        
        Args:
            keyword: 关键词（代码或名称）
            market: 市场类型（None 表示搜索所有市场）
            limit: 返回条数
            
        Returns:
            StockInfo 列表
        """
        log_chain_event(
            layer="market_service",
            event="call",
            name="search",
            params={
                "keyword": keyword,
                "market": market.value if market else None,
                "limit": limit,
            },
        )
        results = []
        
        # A股搜索
        if market is None or market == Market.A_SHARE:
            a_share_results = self.client.search_a_share(keyword, limit)
            results.extend(a_share_results)
        
        # TODO: 添加美股、港股搜索
        result_items = results[:limit]
        log_chain_event(
            layer="market_service",
            event="result",
            name="search",
            success=bool(result_items),
            result={
                "count": len(result_items),
                "symbols": [item.symbol for item in result_items[:5]],
            },
        )
        return result_items
    
    # ==================== 辅助方法 ====================
    
    def _detect_market(self, symbol: str) -> Market:
        """
        自动识别市场类型
        
        规则：
        - 6位纯数字 → A股
        - 包含字母 → 美股
        """
        if symbol.isdigit() and len(symbol) == 6:
            return Market.A_SHARE
        elif symbol.upper().startswith(("6", "0", "3")) and len(symbol) == 6:
            return Market.A_SHARE
        else:
            return Market.US


# 全局服务实例
market_service = MarketService()

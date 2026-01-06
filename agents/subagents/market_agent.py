"""
Market SubAgent - 行情子智能体

职责：
1. 理解用户的行情查询意图
2. 调用 Market Service 获取数据
3. 生成结构化的行情分析结果

可处理的意图：
- 查询实时行情（股价、涨跌幅）
- 查询 K 线数据
- 股票搜索
- 简单技术分析
"""

import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from enum import Enum

from ..common.market import (
    market_service,
    StockQuote,
    KLineData,
    StockInfo,
    KLinePeriod,
)

logger = logging.getLogger(__name__)


class MarketIntent(Enum):
    """行情查询意图"""
    GET_QUOTE = "get_quote"           # 查询实时行情
    GET_KLINE = "get_kline"           # 查询 K 线
    SEARCH_STOCK = "search_stock"     # 搜索股票
    ANALYZE_TREND = "analyze_trend"   # 趋势分析
    UNKNOWN = "unknown"


@dataclass
class MarketQuery:
    """行情查询请求"""
    intent: MarketIntent
    symbol: Optional[str] = None       # 股票代码
    keyword: Optional[str] = None      # 搜索关键词
    period: KLinePeriod = KLinePeriod.DAILY
    count: int = 30                    # K线条数
    
    @classmethod
    def from_dict(cls, data: dict) -> "MarketQuery":
        return cls(
            intent=MarketIntent(data.get("intent", "unknown")),
            symbol=data.get("symbol"),
            keyword=data.get("keyword"),
            period=KLinePeriod(data.get("period", "daily")),
            count=data.get("count", 30),
        )


@dataclass
class MarketResult:
    """行情查询结果"""
    success: bool
    intent: MarketIntent
    data: Optional[Dict[str, Any]] = None  # 原始数据
    summary: str = ""                       # 摘要文本（供 LLM 使用）
    error: Optional[str] = None
    
    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "intent": self.intent.value,
            "data": self.data,
            "summary": self.summary,
            "error": self.error,
        }


class MarketSubAgent:
    """
    行情子智能体
    
    处理行情相关的查询请求，返回结构化结果
    """
    
    def __init__(self):
        self.service = market_service
        logger.info("MarketSubAgent 初始化完成")
    
    def process(self, query: MarketQuery) -> MarketResult:
        """
        处理行情查询
        
        Args:
            query: 查询请求
            
        Returns:
            MarketResult
        """
        logger.debug(f"MarketSubAgent.process | intent={query.intent.value}")
        
        try:
            if query.intent == MarketIntent.GET_QUOTE:
                return self._get_quote(query.symbol)
            
            elif query.intent == MarketIntent.GET_KLINE:
                return self._get_kline(query.symbol, query.period, query.count)
            
            elif query.intent == MarketIntent.SEARCH_STOCK:
                return self._search_stock(query.keyword)
            
            elif query.intent == MarketIntent.ANALYZE_TREND:
                return self._analyze_trend(query.symbol, query.count)
            
            else:
                return MarketResult(
                    success=False,
                    intent=query.intent,
                    error="未知的查询意图",
                )
        except Exception as e:
            logger.error(f"MarketSubAgent 处理失败 | error={e}")
            return MarketResult(
                success=False,
                intent=query.intent,
                error=str(e),
            )
    
    def _get_quote(self, symbol: str) -> MarketResult:
        """获取实时行情"""
        if not symbol:
            return MarketResult(
                success=False,
                intent=MarketIntent.GET_QUOTE,
                error="请提供股票代码",
            )
        
        quote = self.service.get_quote(symbol)
        if quote:
            return MarketResult(
                success=True,
                intent=MarketIntent.GET_QUOTE,
                data=quote.to_dict(),
                summary=quote.summary(),
            )
        else:
            return MarketResult(
                success=False,
                intent=MarketIntent.GET_QUOTE,
                error=f"未能获取 {symbol} 的行情数据",
            )
    
    def _get_kline(
        self, 
        symbol: str, 
        period: KLinePeriod,
        count: int
    ) -> MarketResult:
        """获取 K 线数据"""
        if not symbol:
            return MarketResult(
                success=False,
                intent=MarketIntent.GET_KLINE,
                error="请提供股票代码",
            )
        
        kline = self.service.get_kline(symbol, period, count)
        if kline:
            return MarketResult(
                success=True,
                intent=MarketIntent.GET_KLINE,
                data=kline.to_dict(),
                summary=kline.summary(),
            )
        else:
            return MarketResult(
                success=False,
                intent=MarketIntent.GET_KLINE,
                error=f"未能获取 {symbol} 的 K 线数据",
            )
    
    def _search_stock(self, keyword: str) -> MarketResult:
        """搜索股票"""
        if not keyword:
            return MarketResult(
                success=False,
                intent=MarketIntent.SEARCH_STOCK,
                error="请提供搜索关键词",
            )
        
        results = self.service.search(keyword)
        if results:
            data = [info.to_dict() for info in results]
            summary = f"找到 {len(results)} 只相关股票：" + "、".join(
                f"{r.name}({r.symbol})" for r in results[:5]
            )
            if len(results) > 5:
                summary += f" 等"
            
            return MarketResult(
                success=True,
                intent=MarketIntent.SEARCH_STOCK,
                data={"results": data},
                summary=summary,
            )
        else:
            return MarketResult(
                success=False,
                intent=MarketIntent.SEARCH_STOCK,
                error=f"未找到与 '{keyword}' 相关的股票",
            )
    
    def _analyze_trend(self, symbol: str, days: int = 30) -> MarketResult:
        """
        趋势分析
        
        基于 K 线数据进行简单的趋势分析：
        - 计算均线（MA5, MA10, MA20）
        - 判断趋势方向
        - 识别金叉/死叉
        """
        if not symbol:
            return MarketResult(
                success=False,
                intent=MarketIntent.ANALYZE_TREND,
                error="请提供股票代码",
            )
        
        kline = self.service.get_kline(symbol, KLinePeriod.DAILY, days + 20)
        if not kline or not kline.data:
            return MarketResult(
                success=False,
                intent=MarketIntent.ANALYZE_TREND,
                error=f"未能获取 {symbol} 的 K 线数据",
            )
        
        # 提取收盘价
        closes = [d["close"] for d in kline.data]
        
        # 计算均线
        ma5 = self._calculate_ma(closes, 5)
        ma10 = self._calculate_ma(closes, 10)
        ma20 = self._calculate_ma(closes, 20)
        
        # 判断趋势
        current_price = closes[-1] if closes else 0
        trend = self._determine_trend(current_price, ma5, ma10, ma20)
        
        # 检测金叉/死叉
        signal = self._detect_cross(ma5, ma10)
        
        analysis = {
            "symbol": symbol,
            "current_price": current_price,
            "ma5": ma5,
            "ma10": ma10,
            "ma20": ma20,
            "trend": trend,
            "signal": signal,
        }
        
        # 生成摘要
        summary = (
            f"{symbol} 趋势分析：当前价格 {current_price:.2f} 元，"
            f"MA5={ma5:.2f}，MA10={ma10:.2f}，MA20={ma20:.2f}。"
            f"趋势判断：{trend}。"
        )
        if signal:
            summary += f"信号：{signal}。"
        
        return MarketResult(
            success=True,
            intent=MarketIntent.ANALYZE_TREND,
            data=analysis,
            summary=summary,
        )
    
    def _calculate_ma(self, prices: List[float], period: int) -> float:
        """计算移动平均线"""
        if len(prices) < period:
            return 0.0
        return sum(prices[-period:]) / period
    
    def _determine_trend(
        self, 
        price: float, 
        ma5: float, 
        ma10: float, 
        ma20: float
    ) -> str:
        """判断趋势"""
        if price > ma5 > ma10 > ma20:
            return "强势上涨"
        elif price > ma5 > ma10:
            return "上涨趋势"
        elif price > ma5:
            return "短期反弹"
        elif price < ma5 < ma10 < ma20:
            return "强势下跌"
        elif price < ma5 < ma10:
            return "下跌趋势"
        elif price < ma5:
            return "短期回调"
        else:
            return "震荡整理"
    
    def _detect_cross(self, ma_fast: float, ma_slow: float) -> Optional[str]:
        """检测金叉/死叉（简化版，仅比较当前值）"""
        # 实际应比较前后两天，这里简化处理
        if ma_fast > ma_slow * 1.01:  # 快线高于慢线 1% 以上
            return "短期均线金叉"
        elif ma_fast < ma_slow * 0.99:  # 快线低于慢线 1% 以上
            return "短期均线死叉"
        return None
    
    # ==================== 便捷方法 ====================
    
    def quick_quote(self, symbol: str) -> str:
        """快速获取行情摘要"""
        result = self._get_quote(symbol)
        return result.summary if result.success else result.error
    
    def quick_kline(self, symbol: str, days: int = 5) -> str:
        """快速获取 K 线摘要"""
        result = self._get_kline(symbol, KLinePeriod.DAILY, days + 10)
        return result.summary if result.success else result.error
    
    def quick_analysis(self, symbol: str) -> str:
        """快速趋势分析"""
        result = self._analyze_trend(symbol)
        return result.summary if result.success else result.error


# 全局实例
market_subagent = MarketSubAgent()


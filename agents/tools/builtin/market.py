"""
Market Tools - 行情查询工具

将 MarketSubAgent 中硬编码的行情调用改为独立的 Tool 实现。
每个工具都有明确的 JSON Schema，供 LLM tool use 使用。
"""
from __future__ import annotations

from typing import List

from ..base import BaseTool, DangerLevel
from ..result import ToolResult
from ...common.market import market_service, KLinePeriod
from ...core.logging import logger


class GetQuoteTool(BaseTool):
    """获取股票实时行情。"""

    name = "get_quote"
    description = "查询股票实时行情，包括当前价、涨跌幅、成交量等"
    category = "market"
    danger_level = DangerLevel.READ_ONLY

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "symbol": {
                    "type": "string",
                    "description": "股票代码，如 600519（茅台）、000001（平安）",
                },
                "market": {
                    "type": "string",
                    "description": "市场类型：A=A股, US=美股",
                    "default": "A",
                },
            },
            "required": ["symbol"],
        }

    async def execute(self, symbol: str, market: str = "A", **kw) -> ToolResult:
        from ...common.market.models import Market
        m = Market.A_SHARE if market.upper() == "A" else Market.US
        quote = market_service.get_quote(symbol, m)
        if quote:
            return ToolResult.ok(
                self.name,
                data=quote.to_dict(),
                text=quote.summary(),
            )
        return ToolResult.fail(self.name, error=f"未能获取 {symbol} 的行情数据")


class GetKLineTool(BaseTool):
    """获取股票K线数据。"""

    name = "get_kline"
    description = "查询股票K线数据（日K/周K/月K/分钟K），返回OHLCV数据"
    category = "market"
    danger_level = DangerLevel.READ_ONLY

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "symbol": {
                    "type": "string",
                    "description": "股票代码",
                },
                "period": {
                    "type": "string",
                    "description": "K线周期",
                    "enum": ["daily", "weekly", "monthly", "1min", "5min", "15min", "30min", "60min"],
                    "default": "daily",
                },
                "count": {
                    "type": "integer",
                    "description": "返回K线条数",
                    "default": 30,
                },
                "market": {
                    "type": "string",
                    "description": "市场类型：A=A股, US=美股",
                    "default": "A",
                },
            },
            "required": ["symbol"],
        }

    async def execute(self, symbol: str, period: str = "daily", count: int = 30, market: str = "A", **kw) -> ToolResult:
        from ...common.market.models import Market, KLinePeriod
        m = Market.A_SHARE if market.upper() == "A" else Market.US
        p = KLinePeriod(period)
        kline = market_service.get_kline(symbol, p, count)
        if kline and kline.data:
            return ToolResult.ok(
                self.name,
                data=kline.to_dict(),
                text=kline.summary(),
            )
        return ToolResult.fail(self.name, error=f"未能获取 {symbol} 的K线数据")


class SearchStockTool(BaseTool):
    """搜索股票。"""

    name = "search_stock"
    description = "根据关键词搜索股票，支持名称、拼音等搜索方式"
    category = "market"
    danger_level = DangerLevel.READ_ONLY

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "keyword": {
                    "type": "string",
                    "description": "搜索关键词，可以是股票名称、代码或拼音",
                },
                "market": {
                    "type": "string",
                    "description": "市场类型：A=A股, US=美股",
                    "default": "A",
                },
                "limit": {
                    "type": "integer",
                    "description": "返回结果数量上限",
                    "default": 10,
                },
            },
            "required": ["keyword"],
        }

    async def execute(self, keyword: str, market: str = "A", limit: int = 10, **kw) -> ToolResult:
        from ...common.market.models import Market
        m = Market.A_SHARE if market.upper() == "A" else Market.US
        results = market_service.search(keyword, market=m)
        if results:
            data = [info.to_dict() for info in results[:limit]]
            summary = f"找到 {len(results)} 只相关股票：" + "、".join(
                f"{r.name}({r.symbol})" for r in results[:5]
            )
            return ToolResult.ok(self.name, data={"results": data}, text=summary)
        return ToolResult.fail(self.name, error=f"未找到与 '{keyword}' 相关的股票")


class AnalyzeTrendTool(BaseTool):
    """趋势分析工具。基于K线数据计算均线、判断趋势方向、识别金叉死叉。"""

    name = "analyze_trend"
    description = "对指定股票进行趋势分析，计算均线(MA5/MA10/MA20)、判断趋势方向、识别金叉/死叉信号"
    category = "market"
    danger_level = DangerLevel.READ_ONLY

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "symbol": {
                    "type": "string",
                    "description": "股票代码",
                },
                "days": {
                    "type": "integer",
                    "description": "分析天数（需要获取的K线数量）",
                    "default": 30,
                },
            },
            "required": ["symbol"],
        }

    async def execute(self, symbol: str, days: int = 30, **kw) -> ToolResult:
        kline = market_service.get_kline(symbol, KLinePeriod.DAILY, days + 20)
        if not kline or not kline.data:
            return ToolResult.fail(self.name, error=f"未能获取 {symbol} 的K线数据")

        closes = [d["close"] for d in kline.data]
        ma5 = _calc_ma(closes, 5)
        ma10 = _calc_ma(closes, 10)
        ma20 = _calc_ma(closes, 20)
        price = closes[-1] if closes else 0
        trend = _determine_trend(price, ma5, ma10, ma20)
        signal = _detect_cross(ma5, ma10)

        analysis = {
            "symbol": symbol,
            "current_price": price,
            "ma5": round(ma5, 2),
            "ma10": round(ma10, 2),
            "ma20": round(ma20, 2),
            "trend": trend,
            "signal": signal,
        }
        summary = (
            f"{symbol} 趋势分析：当前价格 {price:.2f} 元，"
            f"MA5={ma5:.2f}，MA10={ma10:.2f}，MA20={ma20:.2f}。"
            f"趋势判断：{trend}。"
        )
        if signal:
            summary += f"信号：{signal}。"

        return ToolResult.ok(self.name, data=analysis, text=summary)


# ---------- 内部辅助函数（复用 MarketSubAgent 中的逻辑） ----------

def _calc_ma(prices: list, period: int) -> float:
    if len(prices) < period:
        return 0.0
    return sum(prices[-period:]) / period


def _determine_trend(price: float, ma5: float, ma10: float, ma20: float) -> str:
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
    return "震荡整理"


def _detect_cross(ma_fast: float, ma_slow: float) -> str | None:
    if ma_fast > ma_slow * 1.01:
        return "短期均线金叉"
    elif ma_fast < ma_slow * 0.99:
        return "短期均线死叉"
    return None


def get_market_tools() -> list[BaseTool]:
    """返回所有行情工具实例。"""
    return [GetQuoteTool(), GetKLineTool(), SearchStockTool(), AnalyzeTrendTool()]

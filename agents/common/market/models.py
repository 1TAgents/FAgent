"""
Market Models - 行情数据模型

定义行情相关的数据结构
"""

from dataclasses import dataclass, field
from datetime import datetime, date
from typing import Optional, List
from enum import Enum


class Market(Enum):
    """市场类型"""
    A_SHARE = "a_share"      # A股
    HK = "hk"                # 港股
    US = "us"                # 美股


class KLinePeriod(Enum):
    """K线周期"""
    DAILY = "daily"          # 日K
    WEEKLY = "weekly"        # 周K
    MONTHLY = "monthly"      # 月K
    MIN_1 = "1min"           # 1分钟
    MIN_5 = "5min"           # 5分钟
    MIN_15 = "15min"         # 15分钟
    MIN_30 = "30min"         # 30分钟
    MIN_60 = "60min"         # 60分钟


@dataclass
class StockInfo:
    """股票基本信息"""
    symbol: str              # 股票代码
    name: str                # 股票名称
    market: Market           # 市场
    industry: Optional[str] = None  # 行业
    
    def to_dict(self) -> dict:
        return {
            "symbol": self.symbol,
            "name": self.name,
            "market": self.market.value,
            "industry": self.industry,
        }


@dataclass
class StockQuote:
    """股票实时行情"""
    symbol: str              # 股票代码
    name: str                # 股票名称
    price: float             # 当前价格
    change: float            # 涨跌额
    change_pct: float        # 涨跌幅 (%)
    open: float              # 开盘价
    high: float              # 最高价
    low: float               # 最低价
    prev_close: float        # 昨收价
    volume: int              # 成交量
    amount: float            # 成交额
    timestamp: datetime      # 数据获取时间
    market: Market = Market.A_SHARE
    trade_date: Optional[date] = None  # 交易日期（如果能获取）
    
    def to_dict(self) -> dict:
        return {
            "symbol": self.symbol,
            "name": self.name,
            "price": self.price,
            "change": self.change,
            "change_pct": self.change_pct,
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "prev_close": self.prev_close,
            "volume": self.volume,
            "amount": self.amount,
            "timestamp": self.timestamp.isoformat(),
            "market": self.market.value,
            "trade_date": self.trade_date.isoformat() if self.trade_date else None,
        }
    
    def summary(self) -> str:
        """生成行情摘要（供 LLM 使用）"""
        direction = "上涨" if self.change >= 0 else "下跌"
        
        # 日期描述
        date_str = ""
        if self.trade_date:
            date_str = f"（{self.trade_date.strftime('%Y-%m-%d')}）"
        
        return (
            f"{self.name}({self.symbol}){date_str} "
            f"价格 {self.price:.2f} 元，"
            f"{direction} {abs(self.change_pct):.2f}%，"
            f"成交额 {self.amount / 1e8:.2f} 亿元"
        )


@dataclass
class KLineData:
    """K线数据"""
    symbol: str              # 股票代码
    period: KLinePeriod      # K线周期
    data: List[dict] = field(default_factory=list)  # K线数据列表
    # 每条数据包含: date, open, high, low, close, volume, amount
    
    def to_dict(self) -> dict:
        return {
            "symbol": self.symbol,
            "period": self.period.value,
            "count": len(self.data),
            "data": self.data,
        }
    
    def summary(self, recent_days: int = 5) -> str:
        """生成 K 线摘要（供 LLM 使用）"""
        if not self.data:
            return f"{self.symbol} 暂无 K 线数据"
        
        recent = self.data[-recent_days:] if len(self.data) >= recent_days else self.data
        
        # 计算区间涨跌幅
        if len(recent) >= 2:
            start_close = recent[0].get("close", 0)
            end_close = recent[-1].get("close", 0)
            if start_close > 0:
                period_change = (end_close - start_close) / start_close * 100
            else:
                period_change = 0
        else:
            period_change = 0
        
        return (
            f"{self.symbol} 最近 {len(recent)} 个交易日，"
            f"累计涨跌幅 {period_change:.2f}%，"
            f"最新收盘价 {recent[-1].get('close', 0):.2f} 元"
        )


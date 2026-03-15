"""
MCP Models - 数据模型定义
"""
from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional
from enum import Enum


class MarketType(str, Enum):
    """市场类型"""
    A_SHARE = "A"       # A 股
    US = "US"           # 美股
    HK = "HK"           # 港股


class KLinePeriod(str, Enum):
    """K 线周期"""
    DAILY = "daily"         # 日线
    WEEKLY = "weekly"       # 周线
    MONTHLY = "monthly"     # 月线
    MINUTE_1 = "1m"         # 1 分钟
    MINUTE_5 = "5m"         # 5 分钟
    MINUTE_15 = "15m"       # 15 分钟
    MINUTE_30 = "30m"       # 30 分钟
    MINUTE_60 = "60m"       # 60 分钟


# ==================== 工具调用请求/响应 ====================

class ToolCallRequest(BaseModel):
    """工具调用请求"""
    tool_name: str = Field(..., description="工具名称")
    arguments: Dict[str, Any] = Field(default_factory=dict, description="工具参数")


class ToolCallResponse(BaseModel):
    """工具调用响应"""
    success: bool = Field(..., description="是否成功")
    data: Optional[Dict[str, Any]] = Field(None, description="返回数据")
    error: Optional[str] = Field(None, description="错误信息")


# ==================== 行情数据模型 ====================

class StockQuote(BaseModel):
    """实时行情"""
    symbol: str = Field(..., description="股票代码")
    name: str = Field(..., description="股票名称")
    market: MarketType = Field(..., description="市场类型")
    
    # 价格信息
    price: float = Field(0.0, description="当前价格")
    open: float = Field(0.0, description="开盘价")
    high: float = Field(0.0, description="最高价")
    low: float = Field(0.0, description="最低价")
    close: float = Field(0.0, description="昨收价")
    
    # 涨跌信息
    change: float = Field(0.0, description="涨跌额")
    change_percent: float = Field(0.0, description="涨跌幅%")
    
    # 成交信息
    volume: int = Field(0, description="成交量 (股)")
    turnover: float = Field(0.0, description="成交额 (元)")
    amount: float = Field(0.0, description="成交额 (万元)")
    
    # 其他
    pe_ratio: Optional[float] = Field(None, description="市盈率")
    pb_ratio: Optional[float] = Field(None, description="市净率")
    total_market_cap: Optional[float] = Field(None, description="总市值 (元)")
    float_market_cap: Optional[float] = Field(None, description="流通市值 (元)")
    
    # 时间戳
    timestamp: Optional[str] = Field(None, description="数据时间")
    
    def summary(self) -> str:
        """生成摘要（供 LLM 使用）"""
        return (
            f"{self.name}({self.symbol}) 当前股价 {self.price:.2f} 元，"
            f"涨跌 {self.change:+.2f} ({self.change_percent:+.2f}%)，"
            f"成交量 {self.volume/10000:.1f}万手，成交额 {self.amount:.2f}万元"
        )


class KLineItem(BaseModel):
    """单根 K 线"""
    date: str = Field(..., description="日期")
    open: float = Field(0.0, description="开盘价")
    high: float = Field(0.0, description="最高价")
    low: float = Field(0.0, description="最低价")
    close: float = Field(0.0, description="收盘价")
    volume: int = Field(0, description="成交量")
    turnover: Optional[float] = Field(None, description="成交额")
    change_percent: Optional[float] = Field(None, description="涨跌幅%")


class KLineData(BaseModel):
    """K 线数据"""
    symbol: str = Field(..., description="股票代码")
    name: str = Field(..., description="股票名称")
    period: KLinePeriod = Field(..., description="周期")
    items: List[KLineItem] = Field(default_factory=list, description="K 线列表")
    
    def summary(self, recent_days: int = 5) -> str:
        """生成摘要（供 LLM 使用）"""
        if not self.items:
            return f"未能获取 {self.symbol} 的 K 线数据"
        
        recent = self.items[-recent_days:] if len(self.items) >= recent_days else self.items
        latest = self.items[-1]
        
        summary = f"{self.name}({self.symbol}) {self.period.value}K 线，"
        summary += f"最新收盘价 {latest.close:.2f} 元 ({latest.date})"
        
        if len(recent) >= 2:
            start = recent[0]
            period_change = ((latest.close - start.close) / start.close) * 100
            summary += f"，近{len(recent)}个交易日{period_change:+.2f}%"
        
        return summary


class StockInfo(BaseModel):
    """股票基本信息"""
    symbol: str = Field(..., description="股票代码")
    name: str = Field(..., description="股票名称")
    market: MarketType = Field(..., description="市场类型")
    
    # 基本信息
    list_date: Optional[str] = Field(None, description="上市日期")
    industry: Optional[str] = Field(None, description="所属行业")
    area: Optional[str] = Field(None, description="地区")
    
    def summary(self) -> str:
        """生成摘要"""
        info = f"{self.name}({self.symbol})"
        if self.industry:
            info += f" - {self.industry}"
        if self.area:
            info += f" - {self.area}"
        return info


# ==================== 工具定义 ====================

class ToolDefinition(BaseModel):
    """工具定义（供 Agent 发现）"""
    name: str = Field(..., description="工具名称")
    description: str = Field(..., description="工具描述")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="参数定义 (JSON Schema)")

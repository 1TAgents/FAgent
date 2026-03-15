"""
MCP Client - Agent 端 SDK

供 SubAgent 调用 MCP 服务的客户端

用法:
    from agents.mcp.client import MCPClient
    
    mcp = MCPClient()
    
    # 调用工具
    result = await mcp.call("stock_quote", symbol="600519")
    
    # 或使用快捷方法
    quote = await mcp.get_quote("600519")
    kline = await mcp.get_kline("600519", period="daily", count=30)
"""
import logging
from typing import Any, Dict, List, Optional
import httpx

from .models import StockQuote, KLineData, KLineItem, StockInfo, MarketType

logger = logging.getLogger(__name__)


class MCPClient:
    """
    MCP 客户端
    
    封装 HTTP 调用，提供便捷的工具调用接口
    """
    
    def __init__(self, base_url: str = "http://localhost:8002"):
        """
        初始化客户端
        
        Args:
            base_url: MCP Server 地址
        """
        self.base_url = base_url.rstrip('/')
        logger.info(f"MCP Client 初始化 | base_url={self.base_url}")
    
    async def call(self, tool_name: str, **kwargs) -> Dict[str, Any]:
        """
        调用工具
        
        Args:
            tool_name: 工具名称
            **kwargs: 工具参数
            
        Returns:
            工具返回数据
            
        Raises:
            MCPError: 调用失败
        """
        url = f"{self.base_url}/tool/call"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    url,
                    json={
                        "tool_name": tool_name,
                        "arguments": kwargs
                    }
                )
                response.raise_for_status()
                result = response.json()
                
                if not result.get("success"):
                    error_msg = result.get("error", "未知错误")
                    logger.error(f"工具调用失败 | tool={tool_name} | error={error_msg}")
                    raise MCPError(error_msg)
                
                logger.debug(f"工具调用成功 | tool={tool_name}")
                return result.get("data", {})
                
        except httpx.HTTPError as e:
            logger.error(f"HTTP 请求失败 | tool={tool_name} | error={e}")
            raise MCPError(f"HTTP 错误：{str(e)}")
        except Exception as e:
            logger.error(f"工具调用异常 | tool={tool_name} | error={e}")
            raise MCPError(str(e))
    
    async def list_tools(self) -> List[Dict[str, Any]]:
        """
        列出所有可用工具
        
        Returns:
            工具定义列表
        """
        url = f"{self.base_url}/tools"
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url)
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error(f"获取工具列表失败 | error={e}")
            return []
    
    # ==================== 快捷方法 ====================
    
    async def get_quote(self, symbol: str, market: str = "A") -> StockQuote:
        """
        获取实时行情（快捷方法）
        
        Args:
            symbol: 股票代码
            market: 市场类型 (A=股，US=美股，HK=港股)
            
        Returns:
            StockQuote 对象
        """
        data = await self.call("stock_quote", symbol=symbol, market=market)
        return StockQuote(**data)
    
    async def get_kline(
        self,
        symbol: str,
        period: str = "daily",
        count: int = 100,
        market: str = "A"
    ) -> KLineData:
        """
        获取 K 线数据（快捷方法）
        
        Args:
            symbol: 股票代码
            period: K 线周期
            count: 返回条数
            market: 市场类型
            
        Returns:
            KLineData 对象
        """
        data = await self.call("stock_kline", symbol=symbol, period=period, count=count, market=market)
        
        # 转换 items
        items = [KLineItem(**item) for item in data.get("items", [])]
        
        return KLineData(
            symbol=data.get("symbol", ""),
            name=data.get("name", ""),
            period=period,
            items=items
        )
    
    async def search(self, keyword: str, market: str = "A", limit: int = 10) -> List[StockInfo]:
        """
        搜索股票（快捷方法）
        
        Args:
            keyword: 关键词
            market: 市场类型
            limit: 返回数量
            
        Returns:
            StockInfo 列表
        """
        data = await self.call("stock_search", keyword=keyword, market=market, limit=limit)
        
        items = []
        for item in data.get("items", []):
            items.append(StockInfo(**item))
        
        return items
    
    # ==================== 工具摘要方法（供 LLM 使用） ====================
    
    async def get_quote_summary(self, symbol: str, market: str = "A") -> str:
        """获取行情摘要（供 LLM 使用）"""
        quote = await self.get_quote(symbol, market)
        return quote.summary()
    
    async def get_kline_summary(
        self,
        symbol: str,
        period: str = "daily",
        count: int = 30,
        market: str = "A"
    ) -> str:
        """获取 K 线摘要（供 LLM 使用）"""
        kline = await self.get_kline(symbol, period, count, market)
        return kline.summary(recent_days=5)


class MCPError(Exception):
    """MCP 调用错误"""
    pass


# 全局客户端实例（可选）
_mcp_client: Optional[MCPClient] = None


def get_mcp_client(base_url: str = "http://localhost:8002") -> MCPClient:
    """获取全局 MCP 客户端实例"""
    global _mcp_client
    if _mcp_client is None:
        _mcp_client = MCPClient(base_url)
    return _mcp_client

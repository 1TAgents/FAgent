"""
Market Module - 市场模块抽象基类

所有市场模块（股票/期货/期权等）必须实现此接口
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional


class MarketModule(ABC):
    """
    市场模块抽象基类
    
    定义统一接口，路由层通过此接口调用各模块
    """
    
    @property
    @abstractmethod
    def module_name(self) -> str:
        """
        模块名称（英文）
        
        Returns:
            如 "stock" / "future"
        """
        pass
    
    @property
    @abstractmethod
    def display_name(self) -> str:
        """
        显示名称（中文 + 图标）
        
        Returns:
            如 "📈 股票" / "📉 期货"
        """
        pass
    
    # ========== 数据查询接口 ==========
    
    @abstractmethod
    def query_quote(self, symbol: str) -> Dict[str, Any]:
        """
        查询实时行情
        
        Args:
            symbol: 品种代码（股票：600519，期货：IF2403）
        
        Returns:
            {
                "symbol": str,
                "name": str,
                "last_price": float,
                "change_percent": float,
                "volume": float,
                "turnover": float,
                "timestamp": str,
                # 期货特有:
                "open_interest": float (optional),
            }
        """
        pass
    
    @abstractmethod
    def query_klines(
        self,
        symbol: str,
        period: str,
        start_date: str,
        end_date: str,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        查询 K 线数据
        
        Args:
            symbol: 品种代码
            period: 周期（1m/5m/daily/weekly/monthly）
            start_date: 开始日期（YYYY-MM-DD）
            end_date: 结束日期
            limit: 返回数量限制
        
        Returns:
            [
                {
                    "timestamp": str,
                    "open": float,
                    "high": float,
                    "low": float,
                    "close": float,
                    "volume": float,
                    # 期货特有:
                    "open_interest": float (optional),
                },
                ...
            ]
        """
        pass
    
    @abstractmethod
    def search_instruments(self, keyword: str, limit: int = 20) -> List[Dict[str, Any]]:
        """
        搜索品种
        
        Args:
            keyword: 搜索关键词
            limit: 返回数量限制
        
        Returns:
            [
                {
                    "symbol": str,
                    "name": str,
                    "exchange": str,
                    "type": str,
                    # 期货特有:
                    "contract_month": str (optional),
                },
                ...
            ]
        """
        pass
    
    # ========== 策略回测接口 ==========
    
    @abstractmethod
    def list_strategies(self) -> List[Dict[str, Any]]:
        """
        获取可用策略列表
        
        Returns:
            [
                {
                    "id": str,
                    "name": str,
                    "description": str,
                    "params": dict,
                },
                ...
            ]
        """
        pass
    
    @abstractmethod
    def run_backtest(
        self,
        strategy_id: str,
        symbol: str,
        start_date: str,
        end_date: str,
        initial_capital: float = 100000.0,
        params: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        执行策略回测
        
        Args:
            strategy_id: 策略 ID
            symbol: 回测品种
            start_date: 开始日期
            end_date: 结束日期
            initial_capital: 初始资金
            params: 策略参数
        
        Returns:
            {
                "success": bool,
                "report": {
                    "total_return": float,
                    "annual_return": float,
                    "sharpe_ratio": float,
                    "max_drawdown": float,
                    "total_trades": int,
                    "win_rate": float,
                    # 期货特有:
                    "long_trades": int (optional),
                    "short_trades": int (optional),
                },
                "trades": list,
                "equity_curve": dict,
                "error": str (optional),
            }
        """
        pass
    
    # ========== 对话接口 ==========
    
    @abstractmethod
    def process_chat(self, message: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        处理对话请求
        
        Args:
            message: 用户消息
            context: 上下文信息（包含当前模式等）
        
        Returns:
            {
                "reply": str,
                "data": dict (optional),
                "suggestions": list,
            }
        """
        pass
    
    # ========== 工具方法 ==========
    
    def get_module_info(self) -> Dict[str, Any]:
        """获取模块信息"""
        return {
            "name": self.module_name,
            "display_name": self.display_name,
            "available": True,
        }

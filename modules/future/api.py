"""
Future Module API - 期货模块统一接口

封装期货数据、策略、回测功能
"""
import logging
from typing import Dict, List, Any, Optional
from pathlib import Path

from modules.base_module import MarketModule

logger = logging.getLogger(__name__)


class FutureModule(MarketModule):
    """
    期货模块实现
    
    封装期货功能，提供统一接口
    """
    
    @property
    def module_name(self) -> str:
        return "future"
    
    @property
    def display_name(self) -> str:
        return "📉 期货"
    
    def __init__(self):
        """初始化期货模块"""
        self._data_source = None
        self._database = None
        logger.info("期货模块初始化完成")
    
    @property
    def data_source(self):
        """数据源（懒加载）"""
        if self._data_source is None:
            from agents.data.future_source import FutureDataSource
            self._data_source = FutureDataSource()
        return self._data_source
    
    @property
    def database(self):
        """数据库（懒加载）"""
        if self._database is None:
            from agents.data.future_database import FutureDatabase
            self._database = FutureDatabase()
        return self._database
    
    def query_quote(self, symbol: str) -> Dict[str, Any]:
        """查询期货行情"""
        try:
            # 从数据库获取最新数据
            bars = self.database.load_bars(symbol, start_date=None, end_date=None, limit=1)
            
            if not bars:
                return {
                    "symbol": symbol,
                    "error": "未找到数据",
                }
            
            bar = bars[0]
            return {
                "symbol": symbol,
                "name": self._get_contract_name(symbol),
                "last_price": bar.close_price,
                "change_percent": 0.0,  # TODO: 计算涨跌幅
                "volume": bar.volume,
                "open_interest": bar.open_interest if bar.open_interest else 0.0,  # 期货特有：持仓量
                "timestamp": bar.datetime.isoformat(),
            }
            
        except Exception as e:
            logger.error(f"查询行情失败 | symbol={symbol} | error={e}")
            return {
                "symbol": symbol,
                "error": str(e),
            }
    
    def query_klines(
        self,
        symbol: str,
        period: str,
        start_date: str,
        end_date: str,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """查询期货 K 线"""
        try:
            # 如果是主力合约请求，获取主力合约连续数据
            if len(symbol) == 2:  # 如 "IF"
                df = self.data_source.get_main_contract_klines(
                    symbol=symbol,
                    period=period,
                    start_date=start_date.replace('-', ''),
                    end_date=end_date.replace('-', '')
                )
                
                return [
                    {
                        "timestamp": row.datetime.isoformat() if hasattr(row.datetime, 'isoformat') else str(row.datetime),
                        "open": float(row.open_price),
                        "high": float(row.high_price),
                        "low": float(row.low_price),
                        "close": float(row.close_price),
                        "volume": float(row.volume),
                        "open_interest": float(row.open_interest) if hasattr(row, 'open_interest') else 0.0,
                    }
                    for _, row in df.iterrows()
                ]
            else:
                # 具体合约
                bars = self.database.load_bars(
                    symbol=symbol,
                    start_date=start_date,
                    end_date=end_date
                )
                bars = bars[:limit]  # 限制数量
                
                return [
                    {
                        "timestamp": bar.datetime.isoformat(),
                        "open": bar.open_price,
                        "high": bar.high_price,
                        "low": bar.low_price,
                        "close": bar.close_price,
                        "volume": bar.volume,
                        "open_interest": bar.open_interest if bar.open_interest else 0.0,
                    }
                    for bar in bars
                ]
            
        except Exception as e:
            logger.error(f"查询 K 线失败 | symbol={symbol} | error={e}")
            return []
    
    def search_instruments(self, keyword: str, limit: int = 20) -> List[Dict[str, Any]]:
        """搜索期货合约"""
        try:
            # TODO: 实现期货合约搜索
            # 临时返回示例数据
            return [
                {
                    "symbol": "IF2403",
                    "name": "沪深 300 股指期货 2403",
                    "exchange": "CFFEX",
                    "type": "future",
                    "contract_month": "2403",
                },
                {
                    "symbol": "IC2403",
                    "name": "中证 500 股指期货 2403",
                    "exchange": "CFFEX",
                    "type": "future",
                    "contract_month": "2403",
                },
            ]
            
        except Exception as e:
            logger.error(f"搜索期货失败 | keyword={keyword} | error={e}")
            return []
    
    def list_strategies(self) -> List[Dict[str, Any]]:
        """获取期货策略列表"""
        try:
            return [
                {
                    "id": "future_dual_ma",
                    "name": "期货双均线策略",
                    "description": "支持做多和做空的双均线策略",
                    "params": {
                        "short_period": 10,
                        "long_period": 30,
                        "allow_short": True,
                    },
                },
                {
                    "id": "future_rsi",
                    "name": "期货 RSI 策略",
                    "description": "基于 RSI 超买超卖的震荡策略",
                    "params": {
                        "rsi_period": 14,
                        "oversold": 30,
                        "overbought": 70,
                    },
                },
            ]
            
        except Exception as e:
            logger.error(f"获取策略列表失败 | error={e}")
            return []
    
    def run_backtest(
        self,
        strategy_id: str,
        symbol: str,
        start_date: str,
        end_date: str,
        initial_capital: float = 100000.0,
        params: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """执行期货回测"""
        try:
            # TODO: 实现期货回测
            return {
                "success": True,
                "report": {
                    "total_return": 0.25,
                    "annual_return": 0.20,
                    "sharpe_ratio": 1.5,
                    "max_drawdown": 0.15,
                    "total_trades": 80,
                    "win_rate": 0.60,
                    "long_trades": 45,      # 期货特有：做多次数
                    "short_trades": 35,     # 期货特有：做空次数
                },
                "trades": [],
                "equity_curve": {},
            }
            
        except Exception as e:
            logger.error(f"回测失败 | error={e}")
            return {
                "success": False,
                "error": str(e),
            }
    
    def process_chat(self, message: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """处理期货对话请求"""
        try:
            # TODO: 集成 LLM + 工具调用
            return {
                "reply": f"期货模块收到：{message}",
                "data": None,
                "suggestions": [
                    "查询沪深 300 股指期货行情",
                    "螺纹钢主力合约走势",
                    "回测期货双均线策略",
                ],
            }
            
        except Exception as e:
            logger.error(f"处理对话失败 | error={e}")
            return {
                "reply": f"处理失败：{e}",
                "data": None,
                "suggestions": [],
            }
    
    def _get_contract_name(self, symbol: str) -> str:
        """获取合约名称（临时实现）"""
        # TODO: 从数据库获取
        name_map = {
            "IF2403": "沪深 300 股指期货 2403",
            "IC2403": "中证 500 股指期货 2403",
            "IH2403": "上证 50 股指期货 2403",
            "RB2405": "螺纹钢 2405",
            "CU2403": "沪铜 2403",
            "AU2406": "沪金 2406",
        }
        return name_map.get(symbol, symbol)

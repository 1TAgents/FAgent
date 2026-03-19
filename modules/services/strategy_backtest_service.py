"""
策略和回测服务层

提供：
1. 策略列表查询
2. 策略详情查询
3. 执行回测
4. 回测结果展示
"""
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class StrategyService:
    """策略服务"""
    
    def __init__(self):
        """初始化策略服务"""
        self._stock_strategies = None
        self._future_strategies = None
        logger.info("策略服务初始化完成")
    
    def list_strategies(self, market_type: str = 'stock') -> List[Dict[str, Any]]:
        """
        获取策略列表
        
        Args:
            market_type: 市场类型（stock/future）
        
        Returns:
            策略列表
        """
        if market_type == 'stock':
            return self._get_stock_strategies()
        elif market_type == 'future':
            return self._get_future_strategies()
        else:
            return []
    
    def _get_stock_strategies(self) -> List[Dict[str, Any]]:
        """获取股票策略列表"""
        try:
            from modules.stock.strategies import list_strategies
            return list_strategies()
        except Exception as e:
            logger.error(f"获取股票策略失败：{e}")
            return []
    
    def _get_future_strategies(self) -> List[Dict[str, Any]]:
        """获取期货策略列表"""
        try:
            from modules.future.strategies import list_strategies
            return list_strategies()
        except Exception as e:
            logger.error(f"获取期货策略失败：{e}")
            return []
    
    def get_strategy_detail(
        self,
        strategy_id: str,
        market_type: str = 'stock'
    ) -> Optional[Dict[str, Any]]:
        """
        获取策略详情
        
        Args:
            strategy_id: 策略 ID
            market_type: 市场类型
        
        Returns:
            策略详情
        """
        strategies = self.list_strategies(market_type)
        
        for strategy in strategies:
            if strategy['id'] == strategy_id:
                return strategy
        
        return None


class BacktestService:
    """回测服务"""
    
    def __init__(self):
        """初始化回测服务"""
        logger.info("回测服务初始化完成")
    
    def run_backtest(
        self,
        strategy_id: str,
        symbol: str,
        start_date: str,
        end_date: str,
        market_type: str = 'stock',
        initial_capital: float = 100000.0,
        params: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        执行回测
        
        Args:
            strategy_id: 策略 ID
            symbol: 标的代码
            start_date: 开始日期
            end_date: 结束日期
            market_type: 市场类型
            initial_capital: 初始资金
            params: 策略参数
        
        Returns:
            回测结果
        """
        logger.info(f"执行回测 | {strategy_id} {symbol} {start_date}至{end_date}")
        
        try:
            if market_type == 'stock':
                return self._run_stock_backtest(
                    strategy_id, symbol, start_date, end_date,
                    initial_capital, params
                )
            elif market_type == 'future':
                return self._run_future_backtest(
                    strategy_id, symbol, start_date, end_date,
                    initial_capital, params
                )
            else:
                return {'success': False, 'error': '不支持的市场类型'}
                
        except Exception as e:
            logger.error(f"回测失败：{e}")
            return {'success': False, 'error': str(e)}
    
    def _run_stock_backtest(
        self,
        strategy_id: str,
        symbol: str,
        start_date: str,
        end_date: str,
        initial_capital: float,
        params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """执行股票回测"""
        try:
            from modules.stock.api import StockModule
            
            module = StockModule()
            result = module.run_backtest(
                strategy_id=strategy_id,
                symbol=symbol,
                start_date=start_date,
                end_date=end_date,
                initial_capital=initial_capital,
                params=params
            )
            
            return result
            
        except Exception as e:
            logger.error(f"股票回测失败：{e}")
            return {'success': False, 'error': str(e)}
    
    def _run_future_backtest(
        self,
        strategy_id: str,
        symbol: str,
        start_date: str,
        end_date: str,
        initial_capital: float,
        params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """执行期货回测"""
        try:
            from modules.future.api import FutureModule
            
            module = FutureModule()
            result = module.run_backtest(
                strategy_id=strategy_id,
                symbol=symbol,
                start_date=start_date,
                end_date=end_date,
                initial_capital=initial_capital,
                params=params
            )
            
            return result
            
        except Exception as e:
            logger.error(f"期货回测失败：{e}")
            return {'success': False, 'error': str(e)}
    
    def format_backtest_result(self, result: Dict[str, Any]) -> str:
        """
        格式化回测结果为文本
        
        Args:
            result: 回测结果
        
        Returns:
            格式化的文本
        """
        if not result.get('success'):
            return f"❌ 回测失败：{result.get('error', '未知错误')}"
        
        report = result.get('report', {})
        
        text = []
        text.append("📊 回测结果")
        text.append("=" * 60)
        text.append(f"总收益率：{report.get('total_return', 0):.2%}")
        text.append(f"年化收益：{report.get('annual_return', 0):.2%}")
        text.append(f"夏普比率：{report.get('sharpe_ratio', 0):.2f}")
        text.append(f"最大回撤：{report.get('max_drawdown', 0):.2%}")
        text.append(f"交易次数：{report.get('total_trades', 0)}")
        text.append(f"胜率：{report.get('win_rate', 0):.1%}")
        
        # 期货特有
        if 'long_trades' in report:
            text.append(f"做多次数：{report.get('long_trades', 0)}")
        if 'short_trades' in report:
            text.append(f"做空次数：{report.get('short_trades', 0)}")
        
        text.append("=" * 60)
        
        return "\n".join(text)


# 全局实例
_strategy_service: Optional[StrategyService] = None
_backtest_service: Optional[BacktestService] = None


def get_strategy_service() -> StrategyService:
    """获取策略服务实例"""
    global _strategy_service
    if _strategy_service is None:
        _strategy_service = StrategyService()
    return _strategy_service


def get_backtest_service() -> BacktestService:
    """获取回测服务实例"""
    global _backtest_service
    if _backtest_service is None:
        _backtest_service = BacktestService()
    return _backtest_service

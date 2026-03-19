"""
统一查询接口

提供自然语言查询功能：
- 问行情：自动识别股票/期货，从本地或远程加载
- 问策略：返回可用策略列表
- 问回测：执行回测并返回结果
"""
import logging
import re
import time
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta

# 导入增强日志
from modules.utils.enhanced_logging import (
    log_query_start, log_query_end, log_data_loaded,
    log_tool_called, log_backtest_run, log_error,
    get_query_logger, get_event_logger
)

logger = logging.getLogger(__name__)


class UnifiedQueryInterface:
    """
    统一查询接口
    
    支持自然语言查询：
    - "茅台行情" → 获取股票行情
    - "螺纹钢 5 分钟数据" → 获取期货数据
    - "有什么策略" → 返回策略列表
    - "回测双均线" → 执行回测
    """
    
    def __init__(self):
        """初始化查询接口"""
        from modules.data.unified_data_service import get_data_service
        from modules.services.strategy_backtest_service import get_strategy_service, get_backtest_service
        
        self.data_service = get_data_service()
        self.strategy_service = get_strategy_service()
        self.backtest_service = get_backtest_service()
        
        logger.info("统一查询接口初始化完成")
    
    def query(self, message: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        处理用户查询
        
        Args:
            message: 用户消息
            context: 上下文信息
        
        Returns:
            查询结果
        """
        start_time = time.time()
        
        # 记录查询开始
        log_query_start(message)
        
        message_lower = message.lower()
        result = None
        
        try:
            # 1. 判断查询类型
            if self._is_market_query(message_lower):
                result = self._handle_market_query(message, context)
                result_type = 'market'
            
            elif self._is_strategy_query(message_lower):
                result = self._handle_strategy_query(message, context)
                result_type = 'strategy'
            
            elif self._is_backtest_query(message_lower):
                result = self._handle_backtest_query(message, context)
                result_type = 'backtest'
            
            else:
                result = {
                    'reply': "抱歉，我不理解您的问题。您可以问我：\n- 股票/期货行情\n- 可用策略\n- 执行回测",
                    'suggestions': [
                        "贵州茅台行情",
                        "螺纹钢 5 分钟数据",
                        "有什么策略",
                        "回测双均线策略"
                    ]
                }
                result_type = 'unknown'
            
            # 记录查询结束
            duration = time.time() - start_time
            log_query_end(message, result_type, duration)
            
            return result
            
        except Exception as e:
            duration = time.time() - start_time
            log_error('query_error', str(e), {'query': message})
            raise
    
    def _is_market_query(self, message: str) -> bool:
        """判断是否是行情查询"""
        keywords = ['行情', '价格', '股价', '走势', '数据', 'k 线', 'k 线']
        return any(kw in message for kw in keywords)
    
    def _is_strategy_query(self, message: str) -> bool:
        """判断是否是策略查询"""
        keywords = ['策略', '方法', '模型', '指标']
        return any(kw in message for kw in keywords)
    
    def _is_backtest_query(self, message: str) -> bool:
        """判断是否是回测查询"""
        keywords = ['回测', '测试', '收益率', '绩效', '表现']
        return any(kw in message for kw in keywords)
    
    def _handle_market_query(self, message: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """处理行情查询"""
        # 提取股票代码
        symbol = self._extract_symbol(message)
        
        if not symbol:
            return {
                'reply': "请告诉我您想查询哪个股票或期货的行情？",
                'suggestions': [
                    "贵州茅台行情",
                    "沪深 300 股指期货",
                    "螺纹钢主力合约"
                ]
            }
        
        # 判断股票还是期货
        if self._is_stock_symbol(symbol):
            return self._get_stock_market_data(symbol, message)
        else:
            return self._get_future_market_data(symbol, message)
    
    def _get_stock_market_data(self, symbol: str, message: str) -> Dict[str, Any]:
        """获取股票行情数据"""
        # 获取实时行情
        quote = self.data_service.get_stock_quote(symbol)
        
        # 获取 K 线数据（最近 30 天）
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        
        bars = self.data_service.get_stock_bars(symbol, start_date, end_date, '1d')
        
        # 构建回复
        if quote:
            reply = f"📈 {symbol} 实时行情\n"
            reply += "=" * 40 + "\n"
            reply += f"最新价：{quote.get('last_price', 0):.2f}\n"
            reply += f"涨跌：{quote.get('change_percent', 0):.2f}%\n"
            reply += f"成交量：{quote.get('volume', 0):,.0f}\n"
            reply += f"成交额：{quote.get('turnover', 0):,.0f}\n"
            reply += "=" * 40 + "\n"
        else:
            reply = f"❌ 未找到 {symbol} 的行情数据"
        
        # 添加 K 线数据摘要
        if bars:
            reply += f"\n📊 最近 30 天数据：{len(bars)} 条\n"
            if len(bars) > 0:
                latest = bars[-1]
                reply += f"最新收盘价：{latest['close']:.2f}\n"
        
        return {
            'reply': reply,
            'data': {
                'quote': quote,
                'bars': bars
            },
            'suggestions': [
                f"{symbol} 技术指标",
                f"回测{symbol}双均线策略",
                f"{symbol} 财务数据"
            ]
        }
    
    def _get_future_market_data(self, symbol: str, message: str) -> Dict[str, Any]:
        """获取期货行情数据"""
        # 判断周期
        if '5 分钟' in message or '5m' in message:
            frequency = '5m'
        elif '日线' in message or '1d' in message:
            frequency = '1d'
        else:
            frequency = '5m'  # 默认 5 分钟
        
        # 获取实时行情
        quote = self.data_service.get_future_quote(symbol)
        
        # 获取 K 线数据
        if frequency == '5m':
            # 最近 5 天
            end_date = datetime.now().strftime('%Y-%m-%d %H:%M')
            start_date = (datetime.now() - timedelta(days=5)).strftime('%Y-%m-%d %H:%M')
        else:
            # 最近 30 天
            end_date = datetime.now().strftime('%Y-%m-%d')
            start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        
        bars = self.data_service.get_future_bars(symbol, start_date, end_date, frequency)
        
        # 构建回复
        reply = f"📊 {symbol} 行情"
        if frequency == '5m':
            reply += " (5 分钟)\n"
        else:
            reply += " (日线)\n"
        reply += "=" * 40 + "\n"
        
        if quote:
            reply += f"最新价：{quote.get('last_price', 0):.1f}\n"
            reply += f"持仓量：{quote.get('open_interest', 0):,.0f}\n"
            reply += f"成交量：{quote.get('volume', 0):,.0f}\n"
        else:
            reply += "暂无实时行情\n"
        
        reply += "=" * 40 + "\n"
        
        if bars:
            reply += f"数据条数：{len(bars)} 条\n"
            if len(bars) > 0:
                latest = bars[-1]
                reply += f"最新收盘价：{latest['close']:.1f}\n"
        
        return {
            'reply': reply,
            'data': {
                'quote': quote,
                'bars': bars
            },
            'suggestions': [
                f"{symbol} 持仓量分析",
                f"回测{symbol}趋势策略",
                f"{symbol} 主力合约"
            ]
        }
    
    def _handle_strategy_query(self, message: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """处理策略查询"""
        # 判断股票还是期货
        if '期货' in message:
            market_type = 'future'
        elif '股票' in message:
            market_type = 'stock'
        else:
            market_type = 'stock'  # 默认股票
        
        strategies = self.strategy_service.list_strategies(market_type)
        
        if not strategies:
            return {
                'reply': f"暂无{market_type}策略",
                'suggestions': [
                    "股票有什么策略",
                    "期货策略列表",
                    "双均线策略详情"
                ]
            }
        
        # 构建回复
        reply = f"📚 可用策略 ({market_type})\n"
        reply += "=" * 60 + "\n"
        
        for i, strategy in enumerate(strategies, 1):
            reply += f"{i}. {strategy['name']} ({strategy['id']})\n"
            reply += f"   {strategy.get('description', '')}\n"
            
            # 显示参数
            params = strategy.get('params', {})
            if params:
                param_str = ", ".join([f"{k}: {v.get('default', '?')}" for k, v in params.items()])
                reply += f"   参数：{param_str}\n"
            
            reply += "\n"
        
        reply += "=" * 60 + "\n"
        reply += "💡 使用示例：\n"
        reply += "  - 回测双均线策略 600519\n"
        reply += "  - 回测期货 RSI 策略 IF\n"
        
        return {
            'reply': reply,
            'data': {
                'strategies': strategies,
                'market_type': market_type
            },
            'suggestions': [
                f"回测{strategies[0]['id']}策略",
                f"{strategies[0]['name']}详情",
                "期货有什么策略"
            ]
        }
    
    def _handle_backtest_query(self, message: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """处理回测查询"""
        # 提取策略 ID
        strategy_id = self._extract_strategy_id(message)
        
        # 提取股票代码
        symbol = self._extract_symbol(message)
        
        if not strategy_id:
            strategy_id = 'dual_ma'  # 默认双均线
        
        if not symbol:
            symbol = '600519'  # 默认贵州茅台
        
        # 判断股票还是期货
        if self._is_stock_symbol(symbol):
            market_type = 'stock'
        else:
            market_type = 'future'
        
        # 执行回测
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
        
        result = self.backtest_service.run_backtest(
            strategy_id=strategy_id,
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
            market_type=market_type,
            initial_capital=100000.0
        )
        
        # 格式化结果
        reply = self.backtest_service.format_backtest_result(result)
        
        return {
            'reply': reply,
            'data': {
                'backtest_result': result,
                'strategy_id': strategy_id,
                'symbol': symbol
            },
            'suggestions': [
                "查看回测详情",
                "查看交易记录",
                "调整策略参数"
            ]
        }
    
    def _extract_symbol(self, message: str) -> Optional[str]:
        """从消息中提取股票代码"""
        # 匹配 6 位数字代码
        match = re.search(r'\b(\d{6})\b', message)
        if match:
            return match.group(1)
        
        # 匹配常见股票名称
        stock_names = {
            '茅台': '600519',
            '贵州茅台': '600519',
            '平安银行': '000001',
            '宁德时代': '300750',
            '五粮液': '000858',
        }
        
        for name, symbol in stock_names.items():
            if name in message:
                return symbol
        
        # 匹配期货品种
        future_symbols = {
            '螺纹': 'RB',
            '螺纹钢': 'RB',
            '沪金': 'AU',
            '黄金': 'AU',
            '沪银': 'AG',
            '白银': 'AG',
            '原油': 'SC',
            '沪深 300': 'IF',
            '股指期货': 'IF',
            '中证 500': 'IC',
            '上证 50': 'IH',
        }
        
        for name, symbol in future_symbols.items():
            if name in message:
                return symbol
        
        return None
    
    def _extract_strategy_id(self, message: str) -> Optional[str]:
        """从消息中提取策略 ID"""
        if '双均线' in message or '双均线' in message:
            return 'dual_ma'
        elif 'rsi' in message.lower():
            return 'rsi'
        elif 'macd' in message.lower():
            return 'macd'
        elif '布林' in message:
            return 'bollinger'
        
        return None
    
    def _is_stock_symbol(self, symbol: str) -> bool:
        """判断是否是股票代码"""
        if symbol.isdigit() and len(symbol) == 6:
            return True
        return False


# 全局实例
_query_interface: Optional[UnifiedQueryInterface] = None


def get_query_interface() -> UnifiedQueryInterface:
    """获取查询接口实例"""
    global _query_interface
    if _query_interface is None:
        _query_interface = UnifiedQueryInterface()
    return _query_interface

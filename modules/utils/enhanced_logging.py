"""
增强的日志系统

特点：
1. 分级日志（DEBUG/INFO/WARNING/ERROR）
2. 结构化日志（JSON 格式）
3. 按模块分离
4. 关键操作审计日志
5. 性能日志（耗时统计）
"""
import logging
import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional
import traceback


class EnhancedLogger:
    """增强日志器"""
    
    def __init__(self, name: str, log_dir: str = 'logs'):
        """
        初始化日志器
        
        Args:
            name: 日志器名称
            log_dir: 日志目录
        """
        self.name = name
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # 创建 logger
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)
        
        # 清除已有 handler
        self.logger.handlers = []
        
        # 控制台 handler（彩色输出）
        console_handler = self._create_console_handler()
        self.logger.addHandler(console_handler)
        
        # 文件 handler（按日期分割）
        file_handler = self._create_file_handler()
        self.logger.addHandler(file_handler)
        
        # 错误文件 handler（单独记录错误）
        error_handler = self._create_error_handler()
        self.logger.addHandler(error_handler)
        
        # 审计日志 handler（关键操作）
        audit_handler = self._create_audit_handler()
        self.logger.addHandler(audit_handler)
    
    def _create_console_handler(self) -> logging.Handler:
        """创建控制台 handler"""
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(logging.INFO)
        
        # 彩色格式
        formatter = logging.Formatter(
            '\033[36m%(asctime)s\033[0m | '
            '\033[32m%(levelname)-8s\033[0m | '
            '\033[33m%(name)s\033[0m | '
            '%(message)s',
            datefmt='%H:%M:%S'
        )
        handler.setFormatter(formatter)
        return handler
    
    def _create_file_handler(self) -> logging.Handler:
        """创建文件 handler（按日期分割）"""
        date_str = datetime.now().strftime('%Y%m%d')
        log_file = self.log_dir / f'{self.name}_{date_str}.log'
        
        handler = logging.FileHandler(log_file, encoding='utf-8')
        handler.setLevel(logging.DEBUG)
        
        formatter = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(name)s | '
            '%(filename)s:%(lineno)d | %(funcName)s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        handler.setFormatter(formatter)
        return handler
    
    def _create_error_handler(self) -> logging.Handler:
        """创建错误日志 handler"""
        date_str = datetime.now().strftime('%Y%m%d')
        error_file = self.log_dir / f'error_{date_str}.log'
        
        handler = logging.FileHandler(error_file, encoding='utf-8')
        handler.setLevel(logging.ERROR)
        
        formatter = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(name)s | '
            '%(filename)s:%(lineno)d | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        handler.setFormatter(formatter)
        return handler
    
    def _create_audit_handler(self) -> logging.Handler:
        """创建审计日志 handler（JSON 格式）"""
        date_str = datetime.now().strftime('%Y%m%d')
        audit_file = self.log_dir / f'audit_{date_str}.jsonl'
        
        handler = logging.FileHandler(audit_file, encoding='utf-8')
        handler.setLevel(logging.INFO)
        handler.addFilter(self._audit_filter)
        
        # JSON 格式
        handler.setFormatter(logging.Formatter('%(message)s'))
        return handler
    
    def _audit_filter(self, record: logging.LogRecord) -> bool:
        """审计日志过滤器（只记录关键操作）"""
        return hasattr(record, 'audit') and record.audit
    
    def debug(self, msg: str, **kwargs):
        """DEBUG 级别日志"""
        self.logger.debug(msg, extra=kwargs)
    
    def info(self, msg: str, **kwargs):
        """INFO 级别日志"""
        self.logger.info(msg, extra=kwargs)
    
    def warning(self, msg: str, **kwargs):
        """WARNING 级别日志"""
        self.logger.warning(msg, extra=kwargs)
    
    def error(self, msg: str, exc_info: bool = False, **kwargs):
        """ERROR 级别日志"""
        if exc_info:
            msg += '\n' + traceback.format_exc()
        self.logger.error(msg, extra=kwargs)
    
    def audit(self, msg: str, **kwargs):
        """审计日志（关键操作）"""
        kwargs['audit'] = True
        kwargs['timestamp'] = datetime.now().isoformat()
        kwargs['level'] = 'AUDIT'
        
        # JSON 格式
        json_msg = json.dumps(kwargs, ensure_ascii=False, default=str)
        self.logger.info(json_msg, extra=kwargs)
    
    def performance(self, operation: str, duration: float, **kwargs):
        """性能日志"""
        kwargs['audit'] = True
        kwargs['timestamp'] = datetime.now().isoformat()
        kwargs['level'] = 'PERF'
        kwargs['operation'] = operation
        kwargs['duration_ms'] = duration * 1000
        
        json_msg = json.dumps(kwargs, ensure_ascii=False, default=str)
        self.logger.info(json_msg, extra=kwargs)


class EventLogger:
    """
    Event 事件日志器
    
    记录关键事件（工具调用、数据加载等）
    不记录：LLM 流式输出（太多无意义）
    """
    
    def __init__(self, log_dir: str = 'logs'):
        """初始化 Event 日志器"""
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Event 文件（JSONL 格式，便于解析）
        date_str = datetime.now().strftime('%Y%m%d')
        self.event_file = self.log_dir / f'events_{date_str}.jsonl'
        
        # 性能统计
        self.stats = {
            'total_events': 0,
            'by_type': {},
            'start_time': datetime.now()
        }
    
    def log_event(self, event_type: str, data: Dict[str, Any], 
                  save_to_file: bool = True):
        """
        记录事件
        
        Args:
            event_type: 事件类型
            data: 事件数据
            save_to_file: 是否保存到文件
        """
        event = {
            'timestamp': datetime.now().isoformat(),
            'event_type': event_type,
            'data': data
        }
        
        # 统计
        self.stats['total_events'] += 1
        self.stats['by_type'][event_type] = \
            self.stats['by_type'].get(event_type, 0) + 1
        
        # 保存到文件
        if save_to_file:
            self._save_event(event)
    
    def _save_event(self, event: Dict[str, Any]):
        """保存事件到文件（JSONL 格式）"""
        try:
            with open(self.event_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(event, ensure_ascii=False, default=str) + '\n')
        except Exception as e:
            print(f"保存事件失败：{e}")
    
    def log_tool_call(self, tool_name: str, params: Dict[str, Any], 
                     result: Any = None, duration: float = None):
        """记录工具调用"""
        data = {
            'tool_name': tool_name,
            'params': params,
            'result': result if result else None,
            'duration_ms': duration * 1000 if duration else None
        }
        self.log_event('tool_call', data)
    
    def log_data_load(self, data_type: str, symbol: str, 
                     source: str, count: int, duration: float):
        """记录数据加载"""
        data = {
            'data_type': data_type,
            'symbol': symbol,
            'source': source,  # local/remote
            'count': count,
            'duration_ms': duration * 1000
        }
        self.log_event('data_load', data)
    
    def log_query(self, query: str, intent: str, result_type: str, 
                 duration: float):
        """记录用户查询"""
        data = {
            'query': query,
            'intent': intent,
            'result_type': result_type,
            'duration_ms': duration * 1000
        }
        self.log_event('user_query', data)
    
    def log_backtest(self, strategy_id: str, symbol: str, 
                    params: Dict[str, Any], result: Dict[str, Any]):
        """记录回测"""
        data = {
            'strategy_id': strategy_id,
            'symbol': symbol,
            'params': params,
            'result_summary': {
                'total_return': result.get('report', {}).get('total_return'),
                'sharpe_ratio': result.get('report', {}).get('sharpe_ratio'),
                'total_trades': result.get('report', {}).get('total_trades')
            }
        }
        self.log_event('backtest', data)
    
    def log_error(self, error_type: str, error_msg: str, 
                 context: Dict[str, Any] = None):
        """记录错误"""
        data = {
            'error_type': error_type,
            'error_msg': error_msg,
            'context': context
        }
        self.log_event('error', data)
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        duration = (datetime.now() - self.stats['start_time']).total_seconds()
        return {
            **self.stats,
            'duration_seconds': duration,
            'events_per_second': self.stats['total_events'] / duration if duration > 0 else 0
        }


# 全局日志器实例
_query_logger = None
_event_logger = None


def get_query_logger() -> EnhancedLogger:
    """获取查询日志器"""
    global _query_logger
    if _query_logger is None:
        _query_logger = EnhancedLogger('query')
    return _query_logger


def get_event_logger() -> EventLogger:
    """获取 Event 日志器"""
    global _event_logger
    if _event_logger is None:
        _event_logger = EventLogger()
    return _event_logger


# 便捷函数
def log_query_start(query: str):
    """记录查询开始"""
    logger = get_query_logger()
    logger.info(f"📝 查询开始：{query[:100]}")
    logger.audit(f"用户查询：{query}", query=query)


def log_query_end(query: str, result_type: str, duration: float):
    """记录查询结束"""
    logger = get_query_logger()
    event_logger = get_event_logger()
    
    logger.info(f"✅ 查询完成：{result_type} ({duration:.2f}s)")
    logger.performance("query", duration, query=query, result_type=result_type)
    event_logger.log_query(query, result_type, result_type, duration)


def log_data_loaded(data_type: str, symbol: str, source: str, 
                   count: int, duration: float):
    """记录数据加载"""
    logger = get_query_logger()
    event_logger = get_event_logger()
    
    source_icon = "💾" if source == 'local' else "🌐"
    logger.info(f"{source_icon} 数据加载：{data_type} {symbol} "
               f"({source}) - {count}条 ({duration:.2f}s)")
    
    event_logger.log_data_load(data_type, symbol, source, count, duration)


def log_tool_called(tool_name: str, params: Dict[str, Any], 
                   result: Any, duration: float):
    """记录工具调用"""
    logger = get_query_logger()
    event_logger = get_event_logger()
    
    logger.info(f"🔧 工具调用：{tool_name} ({duration:.2f}s)")
    logger.debug(f"参数：{params}")
    
    event_logger.log_tool_call(tool_name, params, result, duration)


def log_backtest_run(strategy_id: str, symbol: str, 
                    result: Dict[str, Any], duration: float):
    """记录回测执行"""
    logger = get_query_logger()
    event_logger = get_event_logger()
    
    report = result.get('report', {})
    logger.info(f"📊 回测完成：{strategy_id} {symbol} "
               f"收益:{report.get('total_return', 0):.2%} "
               f"夏普:{report.get('sharpe_ratio', 0):.2f} "
               f"({duration:.2f}s)")
    
    event_logger.log_backtest(strategy_id, symbol, {}, result)


def log_error(error_type: str, error_msg: str, context: Dict[str, Any] = None):
    """记录错误"""
    logger = get_query_logger()
    event_logger = get_event_logger()
    
    logger.error(f"❌ 错误：{error_type} - {error_msg}", exc_info=True)
    
    event_logger.log_error(error_type, error_msg, context)

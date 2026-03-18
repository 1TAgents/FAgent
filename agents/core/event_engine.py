"""
事件引擎

事件驱动架构核心，参考 vnpy 的事件引擎设计

职责：
1. 事件推送（生产者 → 消费者）
2. 事件处理（多线程/单线程）
3. 事件过滤（按类型/订阅）
"""
import logging
from queue import Queue, Empty
from threading import Thread
from datetime import datetime
from typing import Callable, Dict, List, Any, Optional
from dataclasses import dataclass, field
from enum import Enum
import uuid

logger = logging.getLogger(__name__)


# ==================== 事件类型 ====================

class EventType(str, Enum):
    """事件类型枚举"""
    
    # 行情事件
    TICK = "tick"           # Tick 行情推送
    BAR = "bar"             # K 线更新
    
    # 交易事件
    ORDER = "order"         # 订单状态变化
    TRADE = "trade"         # 成交推送
    POSITION = "position"   # 持仓变化
    ACCOUNT = "account"     # 账户更新
    
    # 策略事件
    SIGNAL = "signal"       # 交易信号
    STRATEGY_INIT = "strategy_init"     # 策略初始化
    STRATEGY_START = "strategy_start"   # 策略启动
    STRATEGY_STOP = "strategy_stop"     # 策略停止
    
    # 系统事件
    LOG = "log"             # 日志
    TIMER = "timer"         # 定时器
    EXCEPTION = "exception" # 异常


# ==================== 事件对象 ====================

@dataclass
class Event:
    """
    事件对象
    
    所有事件都封装为 Event 对象，在系统中传递
    """
    type: EventType                     # 事件类型
    data: Any                           # 事件数据
    timestamp: datetime = field(default_factory=datetime.now)
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "event_id": self.event_id,
            "type": self.type.value,
            "timestamp": self.timestamp.isoformat(),
            "data": self.data,
        }


# ==================== 事件引擎 ====================

class EventEngine:
    """
    事件引擎
    
    核心设计：
    1. 事件队列：接收所有事件
    2. 事件处理器：注册到特定事件类型
    3. 事件循环：持续从队列取事件并分发
    
    线程模型：
    - 事件推送线程：生产者（数据源、交易接口）
    - 事件处理线程：消费者（策略、风控、日志）
    """
    
    def __init__(self, use_thread: bool = True):
        """
        初始化事件引擎
        
        Args:
            use_thread: 是否使用独立线程处理事件
                       - True: 异步处理（适合实盘）
                       - False: 同步处理（适合回测）
        """
        self._queue = Queue()
        self._active = False
        self._thread: Optional[Thread] = None
        self._use_thread = use_thread
        
        # 事件处理器注册表
        # type -> [handler1, handler2, ...]
        self._handlers: Dict[EventType, List[Callable]] = {}
        
        # 通用处理器（处理所有事件）
        self._general_handlers: List[Callable] = []
        
        logger.info("事件引擎初始化完成")
    
    def start(self):
        """启动事件引擎"""
        if self._active:
            return
        
        self._active = True
        
        if self._use_thread:
            # 启动事件处理线程
            self._thread = Thread(target=self._run, name="EventEngineThread")
            self._thread.daemon = True
            self._thread.start()
            logger.info("事件引擎线程已启动")
        else:
            logger.info("事件引擎已启动（同步模式）")
    
    def stop(self):
        """停止事件引擎"""
        if not self._active:
            return
        
        self._active = False
        
        if self._thread:
            self._thread.join(timeout=5)
            self._thread = None
        
        logger.info("事件引擎已停止")
    
    def put(self, event: Event):
        """
        推送事件
        
        生产者调用此方法将事件放入队列
        
        Args:
            event: 事件对象
        """
        self._queue.put(event)
    
    def register(self, event_type: EventType, handler: Callable):
        """
        注册事件处理器
        
        消费者调用此方法订阅特定类型的事件
        
        Args:
            event_type: 事件类型
            handler: 处理函数，签名：handler(event: Event)
        """
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        
        if handler not in self._handlers[event_type]:
            self._handlers[event_type].append(handler)
            logger.debug(f"注册事件处理器 | type={event_type.value}, handler={handler.__name__}")
    
    def unregister(self, event_type: EventType, handler: Callable):
        """
        注销事件处理器
        
        Args:
            event_type: 事件类型
            handler: 处理函数
        """
        if event_type in self._handlers and handler in self._handlers[event_type]:
            self._handlers[event_type].remove(handler)
            logger.debug(f"注销事件处理器 | type={event_type.value}")
    
    def register_general(self, handler: Callable):
        """
        注册通用处理器（接收所有事件）
        
        用于日志记录、监控等
        """
        if handler not in self._general_handlers:
            self._general_handlers.append(handler)
    
    def process_event(self, event: Event):
        """
        处理单个事件（同步模式使用）
        
        Args:
            event: 事件对象
        """
        # 1. 调用类型特定的处理器
        if event.type in self._handlers:
            for handler in self._handlers[event.type]:
                try:
                    handler(event)
                except Exception as e:
                    logger.error(f"事件处理失败 | type={event.type.value}, handler={handler.__name__}, error={e}")
        
        # 2. 调用通用处理器
        for handler in self._general_handlers:
            try:
                handler(event)
            except Exception as e:
                logger.error(f"通用处理器失败 | handler={handler.__name__}, error={e}")
    
    def _run(self):
        """事件处理线程主循环"""
        logger.info("事件处理线程开始运行")
        
        while self._active:
            try:
                # 从队列获取事件（超时 1 秒）
                event = self._queue.get(timeout=1)
                self.process_event(event)
            except Empty:
                # 队列为空，继续循环
                continue
            except Exception as e:
                logger.error(f"事件处理异常 | error={e}")
        
        logger.info("事件处理线程已退出")
    
    def create_event(
        self,
        event_type: EventType,
        data: Any,
        timestamp: datetime = None
    ) -> Event:
        """
        创建事件对象
        
        便捷方法，用于生成事件
        
        Args:
            event_type: 事件类型
            data: 事件数据
            timestamp: 时间戳（默认当前时间）
        
        Returns:
            Event 对象
        """
        return Event(
            type=event_type,
            data=data,
            timestamp=timestamp or datetime.now()
        )
    
    def is_active(self) -> bool:
        """检查引擎是否运行中"""
        return self._active
    
    def get_handler_count(self, event_type: EventType) -> int:
        """获取某类事件的处理器数量"""
        return len(self._handlers.get(event_type, []))
    
    def get_queue_size(self) -> int:
        """获取队列中待处理事件数量"""
        return self._queue.qsize()


# ==================== 事件引擎装饰器 ====================

def event_handler(event_type: EventType):
    """
    事件处理器装饰器
    
    用法:
        @event_handler(EventType.BAR)
        def on_bar(event: Event):
            bar = event.data
            ...
    """
    def decorator(func: Callable):
        func._event_type = event_type
        return func
    return decorator


def register_handlers(engine: EventEngine, obj: Any):
    """
    自动注册对象中的所有事件处理器
    
    查找带有 _event_type 属性的方法并注册
    
    Args:
        engine: 事件引擎
        obj: 包含处理器的对象
    """
    for name in dir(obj):
        method = getattr(obj, name)
        if hasattr(method, '_event_type'):
            event_type = getattr(method, '_event_type')
            engine.register(event_type, method)
            logger.debug(f"自动注册处理器 | obj={obj.__class__.__name__}, method={name}, type={event_type.value}")


# ==================== 全局事件引擎实例 ====================

# 全局事件引擎（单例）
_global_engine: Optional[EventEngine] = None


def get_event_engine(use_thread: bool = True) -> EventEngine:
    """
    获取全局事件引擎实例
    
    Args:
        use_thread: 是否使用线程模式
    
    Returns:
        EventEngine 实例
    """
    global _global_engine
    if _global_engine is None:
        _global_engine = EventEngine(use_thread=use_thread)
    return _global_engine


def init_event_engine(use_thread: bool = True) -> EventEngine:
    """
    初始化全局事件引擎
    
    Args:
        use_thread: 是否使用线程模式
    
    Returns:
        EventEngine 实例
    """
    global _global_engine
    _global_engine = EventEngine(use_thread=use_thread)
    return _global_engine

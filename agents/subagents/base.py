"""
SubAgent 基类

所有子智能体的抽象基类，定义统一接口
"""
from abc import ABC, abstractmethod
from typing import AsyncIterator, Iterator, Optional
import logging

from ..router.models import TaskContext

logger = logging.getLogger(__name__)


class BaseSubAgent(ABC):
    """
    SubAgent 抽象基类
    
    所有子智能体必须实现：
    - process_stream: 流式处理（主要接口）
    - process: 非流式处理
    
    设计原则：
    - SubAgent 只接收 TaskContext，不直接访问完整历史
    - 流式输出直接返回给用户（透传）
    - 专注于领域任务，不做路由决策
    """
    
    name: str = "base"  # SubAgent 名称，子类需覆盖
    
    def __init__(self):
        logger.info(f"{self.__class__.__name__} 初始化完成")
    
    @abstractmethod
    async def process_stream(self, context: TaskContext) -> AsyncIterator[str]:
        """
        流式处理任务（主要接口）
        
        Args:
            context: 任务上下文（由 Router 提供）
            
        Yields:
            str: 流式返回的文本片段
        """
        pass
    
    @abstractmethod
    async def process(self, context: TaskContext) -> str:
        """
        非流式处理任务
        
        Args:
            context: 任务上下文
            
        Returns:
            str: 完整回复内容
        """
        pass
    
    def can_handle(self, context: TaskContext) -> bool:
        """
        判断是否能处理该任务（可选覆盖）
        
        子类可以覆盖此方法，实现更精细的任务匹配
        """
        return True
    
    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(name={self.name})>"

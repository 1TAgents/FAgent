"""
Chat Agent - 对话 Agent 主逻辑

职责：
1. 通过 cid + message_id 获取历史消息
2. 处理历史数据和 metadata
3. 拼接 System Prompt
4. 调用 LLM
5. 返回流式/非流式结果
"""
import os
import sys
from typing import Optional, Iterator, List, Dict, Any

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from backend.core.context import ctx_logger as logger
from backend.services.storage import message_storage
from .llm import llm_service
from ..core.prompts import DEFAULT_SYSTEM_PROMPT
from ..core.context_builder import context_builder


class ChatAgent:
    """
    对话 Agent
    
    负责：
    - 获取历史消息
    - 构建 LLM 上下文
    - 调用 LLM
    - 返回结果
    """
    
    def __init__(self):
        self.llm = llm_service
        logger.info("ChatAgent 初始化完成")
    
    def _get_history_messages(
        self,
        cid: int,
        before_message_id: int,
        limit: Optional[int] = None
    ) -> List[Dict]:
        """
        获取历史消息
        
        Args:
            cid: 会话 ID
            before_message_id: 获取此消息之前的历史
            limit: 最多返回条数
            
        Returns:
            历史消息列表 [{"role": "...", "content": "..."}]
        """
        messages = message_storage.get_history_before_message(cid, before_message_id, limit)
        return [{"role": msg["role"], "content": msg["content"]} for msg in messages]
    
    def _build_context(
        self,
        history: List[Dict],
        user_message: str,
        system_prompt: Optional[str] = None
    ) -> List[Dict]:
        """
        构建 LLM 上下文
        
        Args:
            history: 历史消息
            user_message: 当前用户消息
            system_prompt: 自定义 System Prompt
            
        Returns:
            完整的 messages 列表
        """
        return context_builder.build_chat_messages(
            system_prompt=system_prompt or DEFAULT_SYSTEM_PROMPT,
            history=history,
            user_message=user_message,
        )
    
    def process_stream(
        self,
        cid: int,
        message_id: int,
        user_message: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        history_limit: Optional[int] = None,
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> Iterator[str]:
        """
        流式处理对话
        
        Args:
            cid: 会话 ID
            message_id: 当前用户消息 ID（用于获取之前的历史）
            user_message: 当前用户消息内容
            temperature: LLM 温度参数
            max_tokens: 最大 token 数
            history_limit: 历史消息条数限制
            system_prompt: 自定义 System Prompt
            **kwargs: 其他 LLM 参数
            
        Yields:
            str: 流式返回的文本片段
        """
        logger.debug(f"ChatAgent.process_stream | cid={cid} | message_id={message_id}")
        
        # 1. 获取历史消息
        history = self._get_history_messages(cid, message_id, history_limit)
        logger.debug(f"获取历史消息 | count={len(history)}")
        
        # 2. 构建上下文
        messages = self._build_context(history, user_message, system_prompt)
        logger.debug(f"构建上下文完成 | total_messages={len(messages)}")
        
        # 3. 调用 LLM（流式）
        for chunk in self.llm.chat_completion_stream(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs
        ):
            yield chunk
    
    def process(
        self,
        cid: int,
        message_id: int,
        user_message: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        history_limit: Optional[int] = None,
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> str:
        """
        非流式处理对话
        
        Args:
            cid: 会话 ID
            message_id: 当前用户消息 ID
            user_message: 当前用户消息内容
            temperature: LLM 温度参数
            max_tokens: 最大 token 数
            history_limit: 历史消息条数限制
            system_prompt: 自定义 System Prompt
            **kwargs: 其他 LLM 参数
            
        Returns:
            str: AI 回复内容
        """
        logger.debug(f"ChatAgent.process | cid={cid} | message_id={message_id}")
        
        # 1. 获取历史消息
        history = self._get_history_messages(cid, message_id, history_limit)
        logger.debug(f"获取历史消息 | count={len(history)}")
        
        # 2. 构建上下文
        messages = self._build_context(history, user_message, system_prompt)
        logger.debug(f"构建上下文完成 | total_messages={len(messages)}")
        
        # 3. 调用 LLM（非流式）
        response = self.llm.chat_completion(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs
        )
        
        return response.choices[0].message.content


# 全局实例
chat_agent = ChatAgent()

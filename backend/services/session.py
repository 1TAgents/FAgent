"""
会话管理服务 - 管理多轮对话的会话和历史
使用持久化存储（SQLite）

支持多种消息类型：
- text: 纯文本
- image_url: 图片 URL
- image_base64: 图片 Base64
- video_url: 视频 URL
- audio_url: 音频 URL
- file: 文件
- multimodal: 多模态（混合内容）
"""
from typing import Dict, List, Optional, Union
import uuid
from loguru import logger
from .storage import message_storage, ContentType


class SessionManager:
    """
    会话管理器
    使用 conversation_id 作为会话标识
    每个消息都有 message_id 和 conversation_id
    
    支持多种消息类型和消息 metadata
    """
    
    def create_session(
        self,
        conversation_id: Optional[str] = None,
        system_message: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> str:
        """
        创建新会话（conversation）
        
        Args:
            conversation_id: 可选的会话ID，如果不提供则自动生成
            system_message: 可选的系统消息
            metadata: 可选的元数据
            
        Returns:
            会话ID (conversation_id)
        """
        cid = message_storage.create_conversation(
            conversation_id=conversation_id,
            system_message=system_message,
            metadata=metadata
        )
        logger.info(f"SessionManager: 会话创建 | conversation_id={cid}")
        return cid
    
    def get_session(self, conversation_id: str) -> Optional[Dict]:
        """
        获取会话信息
        
        Args:
            conversation_id: 会话ID
            
        Returns:
            会话信息字典，如果不存在则返回 None
        """
        return message_storage.get_conversation(conversation_id)
    
    def add_message(
        self,
        conversation_id: str,
        role: str,
        content: Union[str, List, Dict],
        content_type: Optional[str] = None,
        metadata: Optional[Dict] = None,
        message_id: Optional[str] = None
    ) -> str:
        """
        添加消息到会话
        
        Args:
            conversation_id: 会话ID
            role: 消息角色 (user, assistant, system)
            content: 消息内容，支持以下格式：
                - 字符串: "Hello"（纯文本）
                - 多模态列表: [{"type": "text", "text": "..."}, {"type": "image_url", "image_url": {...}}]
                - 单个内容项: {"type": "image_url", "image_url": {"url": "..."}}
            content_type: 内容类型，如果不提供则自动检测
            metadata: 消息元数据
            message_id: 可选的消息ID，如果不提供则自动生成
            
        Returns:
            消息ID
        """
        return message_storage.add_message(
            conversation_id=conversation_id,
            role=role,
            content=content,
            content_type=content_type,
            metadata=metadata,
            message_id=message_id
        )
    
    def get_message(self, message_id: str) -> Optional[Dict]:
        """
        根据 message_id 获取单条消息
        
        Args:
            message_id: 消息ID
            
        Returns:
            消息字典，如果不存在则返回 None
        """
        return message_storage.get_message(message_id)
    
    def update_message_metadata(
        self,
        message_id: str,
        metadata: Dict
    ) -> bool:
        """
        更新消息的 metadata
        
        Args:
            message_id: 消息ID
            metadata: 新的元数据
            
        Returns:
            是否成功
        """
        return message_storage.update_message_metadata(message_id, metadata)
    
    def get_messages(
        self,
        conversation_id: str,
        limit: Optional[int] = None,
        offset: int = 0
    ) -> List[Dict]:
        """
        获取会话的所有消息
        
        Args:
            conversation_id: 会话ID
            limit: 可选的消息数量限制
            offset: 偏移量
            
        Returns:
            消息列表，每个消息包含 message_id, conversation_id, role, content, created_at
        """
        return message_storage.get_messages(
            conversation_id=conversation_id,
            limit=limit,
            offset=offset
        )
    
    def get_conversation_with_messages(self, conversation_id: str) -> Optional[Dict]:
        """
        获取会话及其所有消息（完整记录）
        
        Args:
            conversation_id: 会话ID
            
        Returns:
            包含会话信息和消息列表的字典
        """
        return message_storage.get_conversation_with_messages(conversation_id)
    
    def get_messages_for_llm(self, conversation_id: str) -> List[Dict]:
        """
        获取会话消息，格式化为 LLM API 调用格式
        
        Args:
            conversation_id: 会话ID
            
        Returns:
            LLM API 格式的消息列表，每条消息只包含 role 和 content
            
        示例返回:
            [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "Hi there!"},
                {"role": "user", "content": [
                    {"type": "text", "text": "What is in this image?"},
                    {"type": "image_url", "image_url": {"url": "https://..."}}
                ]}
            ]
        """
        return message_storage.get_messages_for_llm(conversation_id)
    
    def delete_message(self, message_id: str) -> bool:
        """
        删除单条消息
        
        Args:
            message_id: 消息ID
            
        Returns:
            是否成功删除
        """
        return message_storage.delete_message(message_id)
    
    def clear_session(self, conversation_id: str) -> bool:
        """
        清空会话消息（保留会话）
        
        Args:
            conversation_id: 会话ID
            
        Returns:
            是否成功
        """
        return message_storage.clear_conversation_messages(conversation_id)
    
    def delete_session(self, conversation_id: str) -> bool:
        """
        删除会话及其所有消息
        
        Args:
            conversation_id: 会话ID
            
        Returns:
            是否成功删除
        """
        return message_storage.delete_conversation(conversation_id)
    
    def list_sessions(self, limit: Optional[int] = None, offset: int = 0) -> List[Dict]:
        """
        列出所有会话
        
        Args:
            limit: 可选的数量限制
            offset: 偏移量
            
        Returns:
            会话列表，按更新时间倒序
        """
        return message_storage.list_conversations(limit=limit, offset=offset)
    
    # 向后兼容：session_id 映射到 conversation_id
    def create_session_by_session_id(
        self,
        session_id: Optional[str] = None,
        system_message: Optional[str] = None
    ) -> str:
        """
        向后兼容方法：使用 session_id 创建会话
        实际使用 conversation_id
        """
        return self.create_session(
            conversation_id=session_id,
            system_message=system_message
        )


# 全局会话管理器实例
session_manager = SessionManager()


"""
消息存储服务 - 使用 SQLite 持久化存储消息

支持多种消息类型（与 OpenAI/LLM API 格式一致）：
- text: 纯文本
- image_url: 图片 URL
- image_base64: 图片 Base64
- video_url: 视频 URL
- audio_url: 音频 URL
- file: 文件
- multimodal: 多模态（混合内容）

消息 content 格式（与 OpenAI API 一致）：
1. 纯文本: "content": "Hello"
2. 多模态: "content": [
     {"type": "text", "text": "What is in this image?"},
     {"type": "image_url", "image_url": {"url": "https://..."}}
   ]
"""
import sqlite3
import json
from typing import Dict, List, Optional, Union, Any
from datetime import datetime
from pathlib import Path
import uuid
from enum import Enum
from loguru import logger


class ContentType(str, Enum):
    """消息内容类型（与 OpenAI API 一致）"""
    TEXT = "text"
    IMAGE_URL = "image_url"
    IMAGE_BASE64 = "image_base64"  # 自定义扩展
    VIDEO_URL = "video_url"  # 自定义扩展
    AUDIO_URL = "audio_url"  # 自定义扩展
    FILE = "file"  # 自定义扩展
    MULTIMODAL = "multimodal"  # 混合内容


class MessageStorage:
    """消息存储服务"""
    
    # 数据库版本，用于迁移
    DB_VERSION = 2
    
    def __init__(self, db_path: str = "data/conversations.db"):
        """
        初始化存储服务
        
        Args:
            db_path: 数据库文件路径
        """
        # 确保目录存在
        db_file = Path(db_path)
        db_file.parent.mkdir(parents=True, exist_ok=True)
        
        self.db_path = db_path
        self._init_database()
        logger.info(f"消息存储服务初始化完成 | db_path={db_path}")
    
    def _init_database(self):
        """初始化数据库表"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 检查是否需要迁移
        cursor.execute("PRAGMA user_version")
        current_version = cursor.fetchone()[0]
        
        if current_version < self.DB_VERSION:
            # 新建或迁移数据库
            self._create_tables(cursor)
            cursor.execute(f"PRAGMA user_version = {self.DB_VERSION}")
        
        conn.commit()
        conn.close()
    
    def _create_tables(self, cursor):
        """创建数据库表"""
        # 创建会话表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                conversation_id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                metadata TEXT,
                system_message TEXT
            )
        """)
        
        # 创建消息表（支持多种类型和 metadata）
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                message_id TEXT PRIMARY KEY,
                conversation_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content_type TEXT NOT NULL DEFAULT 'text',
                content TEXT NOT NULL,
                metadata TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (conversation_id) REFERENCES conversations(conversation_id)
            )
        """)
        
        # 创建索引
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_messages_conversation_id 
            ON messages(conversation_id)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_messages_created_at 
            ON messages(created_at)
        """)
    
    @staticmethod
    def _detect_content_type(content: Union[str, List, Dict]) -> str:
        """
        自动检测内容类型
        
        Args:
            content: 消息内容
            
        Returns:
            内容类型字符串
        """
        if isinstance(content, str):
            return ContentType.TEXT.value
        elif isinstance(content, list):
            # 多模态内容
            return ContentType.MULTIMODAL.value
        elif isinstance(content, dict):
            # 单个内容项
            return content.get("type", ContentType.TEXT.value)
        else:
            return ContentType.TEXT.value
    
    @staticmethod
    def _serialize_content(content: Union[str, List, Dict]) -> str:
        """
        序列化消息内容
        
        Args:
            content: 消息内容（字符串、列表或字典）
            
        Returns:
            JSON 字符串
        """
        if isinstance(content, str):
            return content
        else:
            return json.dumps(content, ensure_ascii=False)
    
    @staticmethod
    def _deserialize_content(content_str: str, content_type: str) -> Union[str, List, Dict]:
        """
        反序列化消息内容
        
        Args:
            content_str: 内容字符串
            content_type: 内容类型
            
        Returns:
            原始内容
        """
        if content_type == ContentType.TEXT.value:
            # 尝试解析 JSON，如果失败则返回原始字符串
            try:
                return json.loads(content_str)
            except (json.JSONDecodeError, TypeError):
                return content_str
        else:
            try:
                return json.loads(content_str)
            except (json.JSONDecodeError, TypeError):
                return content_str
    
    def create_conversation(
        self,
        conversation_id: Optional[str] = None,
        system_message: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> str:
        """
        创建新会话
        
        Args:
            conversation_id: 可选的会话ID，如果不提供则自动生成
            system_message: 可选的系统消息
            metadata: 可选的元数据
            
        Returns:
            会话ID (conversation_id)
        """
        if conversation_id is None:
            conversation_id = str(uuid.uuid4())
        
        now = datetime.now().isoformat()
        metadata_json = json.dumps(metadata, ensure_ascii=False) if metadata else None
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT INTO conversations (conversation_id, created_at, updated_at, metadata, system_message)
                VALUES (?, ?, ?, ?, ?)
            """, (conversation_id, now, now, metadata_json, system_message))
            
            # 如果有系统消息，添加到消息表
            if system_message:
                message_id = str(uuid.uuid4())
                cursor.execute("""
                    INSERT INTO messages (message_id, conversation_id, role, content_type, content, metadata, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (message_id, conversation_id, "system", ContentType.TEXT.value, system_message, None, now))
            
            conn.commit()
            logger.info(f"会话创建成功 | conversation_id={conversation_id}")
            return conversation_id
        except Exception as e:
            logger.error(f"会话创建失败 | error={str(e)}")
            raise
        finally:
            conn.close()
    
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
                - 字符串: "Hello"
                - 多模态列表: [{"type": "text", "text": "..."}, {"type": "image_url", "image_url": {...}}]
                - 单个内容项: {"type": "image_url", "image_url": {"url": "..."}}
            content_type: 内容类型，如果不提供则自动检测
            metadata: 消息元数据
            message_id: 可选的消息ID，如果不提供则自动生成
            
        Returns:
            消息ID
        """
        if message_id is None:
            message_id = str(uuid.uuid4())
        
        if content_type is None:
            content_type = self._detect_content_type(content)
        
        content_str = self._serialize_content(content)
        metadata_json = json.dumps(metadata, ensure_ascii=False) if metadata else None
        now = datetime.now().isoformat()
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT INTO messages (message_id, conversation_id, role, content_type, content, metadata, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (message_id, conversation_id, role, content_type, content_str, metadata_json, now))
            
            # 更新会话的更新时间
            cursor.execute("""
                UPDATE conversations
                SET updated_at = ?
                WHERE conversation_id = ?
            """, (now, conversation_id))
            
            conn.commit()
            logger.debug(
                f"消息添加成功 | conversation_id={conversation_id} | "
                f"message_id={message_id} | role={role} | type={content_type}"
            )
            return message_id
        except Exception as e:
            logger.error(f"消息添加失败 | conversation_id={conversation_id} | error={str(e)}")
            raise
        finally:
            conn.close()
    
    def get_message(self, message_id: str) -> Optional[Dict]:
        """
        根据 message_id 获取单条消息
        
        Args:
            message_id: 消息ID
            
        Returns:
            消息字典，如果不存在则返回 None
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT message_id, conversation_id, role, content_type, content, metadata, created_at
                FROM messages
                WHERE message_id = ?
            """, (message_id,))
            
            row = cursor.fetchone()
            if row is None:
                return None
            
            return self._row_to_message(row)
        finally:
            conn.close()
    
    def _row_to_message(self, row) -> Dict:
        """将数据库行转换为消息字典"""
        content = self._deserialize_content(row["content"], row["content_type"])
        
        metadata = None
        if row["metadata"]:
            try:
                metadata = json.loads(row["metadata"])
            except (json.JSONDecodeError, TypeError):
                pass
        
        return {
            "message_id": row["message_id"],
            "conversation_id": row["conversation_id"],
            "role": row["role"],
            "content_type": row["content_type"],
            "content": content,
            "metadata": metadata,
            "created_at": row["created_at"]
        }
    
    def get_messages(
        self,
        conversation_id: str,
        limit: Optional[int] = None,
        offset: int = 0,
        content_type: Optional[str] = None
    ) -> List[Dict]:
        """
        获取会话的所有消息
        
        Args:
            conversation_id: 会话ID
            limit: 可选的消息数量限制
            offset: 偏移量
            content_type: 可选的内容类型过滤
            
        Returns:
            消息列表，按创建时间排序
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        try:
            query = """
                SELECT message_id, conversation_id, role, content_type, content, metadata, created_at
                FROM messages
                WHERE conversation_id = ?
            """
            params: List[Any] = [conversation_id]
            
            if content_type:
                query += " AND content_type = ?"
                params.append(content_type)
            
            query += " ORDER BY created_at ASC"
            
            if limit:
                query += " LIMIT ? OFFSET ?"
                params.extend([limit, offset])
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            return [self._row_to_message(row) for row in rows]
        finally:
            conn.close()
    
    def get_messages_for_llm(self, conversation_id: str) -> List[Dict]:
        """
        获取会话消息，格式化为 LLM API 调用格式
        
        Args:
            conversation_id: 会话ID
            
        Returns:
            LLM API 格式的消息列表
        """
        messages = self.get_messages(conversation_id)
        
        llm_messages = []
        for msg in messages:
            llm_msg = {
                "role": msg["role"],
                "content": msg["content"]
            }
            llm_messages.append(llm_msg)
        
        return llm_messages
    
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
        metadata_json = json.dumps(metadata, ensure_ascii=False)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                UPDATE messages
                SET metadata = ?
                WHERE message_id = ?
            """, (metadata_json, message_id))
            
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()
    
    def get_conversation(self, conversation_id: str) -> Optional[Dict]:
        """
        获取会话信息
        
        Args:
            conversation_id: 会话ID
            
        Returns:
            会话信息字典，如果不存在则返回 None
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT conversation_id, created_at, updated_at, metadata, system_message
                FROM conversations
                WHERE conversation_id = ?
            """, (conversation_id,))
            
            row = cursor.fetchone()
            if row is None:
                return None
            
            metadata = None
            if row["metadata"]:
                try:
                    metadata = json.loads(row["metadata"])
                except (json.JSONDecodeError, TypeError):
                    pass
            
            return {
                "conversation_id": row["conversation_id"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
                "metadata": metadata,
                "system_message": row["system_message"]
            }
        finally:
            conn.close()
    
    def get_conversation_with_messages(self, conversation_id: str) -> Optional[Dict]:
        """
        获取会话及其所有消息
        
        Args:
            conversation_id: 会话ID
            
        Returns:
            包含会话信息和消息列表的字典
        """
        conversation = self.get_conversation(conversation_id)
        if conversation is None:
            return None
        
        messages = self.get_messages(conversation_id)
        conversation["messages"] = messages
        conversation["message_count"] = len(messages)
        
        return conversation
    
    def delete_conversation(self, conversation_id: str) -> bool:
        """
        删除会话及其所有消息
        
        Args:
            conversation_id: 会话ID
            
        Returns:
            是否成功删除
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # 先删除消息
            cursor.execute("DELETE FROM messages WHERE conversation_id = ?", (conversation_id,))
            # 删除会话
            cursor.execute("DELETE FROM conversations WHERE conversation_id = ?", (conversation_id,))
            
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()
    
    def delete_message(self, message_id: str) -> bool:
        """
        删除单条消息
        
        Args:
            message_id: 消息ID
            
        Returns:
            是否成功删除
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("DELETE FROM messages WHERE message_id = ?", (message_id,))
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()
    
    def clear_conversation_messages(self, conversation_id: str) -> bool:
        """
        清空会话的所有消息（保留会话）
        
        Args:
            conversation_id: 会话ID
            
        Returns:
            是否成功
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("DELETE FROM messages WHERE conversation_id = ?", (conversation_id,))
            conn.commit()
            return True
        finally:
            conn.close()
    
    def list_conversations(
        self,
        limit: Optional[int] = None,
        offset: int = 0
    ) -> List[Dict]:
        """
        列出所有会话
        
        Args:
            limit: 可选的数量限制
            offset: 偏移量
            
        Returns:
            会话列表，按更新时间倒序
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        try:
            query = """
                SELECT 
                    c.conversation_id,
                    c.created_at,
                    c.updated_at,
                    c.metadata,
                    COUNT(m.message_id) as message_count
                FROM conversations c
                LEFT JOIN messages m ON c.conversation_id = m.conversation_id
                GROUP BY c.conversation_id
                ORDER BY c.updated_at DESC
            """
            
            params: List[Any] = []
            if limit:
                query += " LIMIT ? OFFSET ?"
                params.extend([limit, offset])
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            conversations = []
            for row in rows:
                metadata = None
                if row["metadata"]:
                    try:
                        metadata = json.loads(row["metadata"])
                    except (json.JSONDecodeError, TypeError):
                        pass
                
                conversations.append({
                    "conversation_id": row["conversation_id"],
                    "created_at": row["created_at"],
                    "updated_at": row["updated_at"],
                    "metadata": metadata,
                    "message_count": row["message_count"]
                })
            
            return conversations
        finally:
            conn.close()


# 全局存储实例
message_storage = MessageStorage()

"""
消息存储服务 - 使用 SQLite 持久化存储消息

ID 设计：
- cid (conversation_id): 整数，自增
- message_id: 整数，自增
- 通过 message_id 大小过滤历史消息

消息角色（role）:
- user: 用户消息
- assistant: AI 回复
- system: 系统消息

消息类型（content_type）:
- text: 纯文本
- image_url: 图片 URL
- image_base64: 图片 Base64
- video_url: 视频 URL
- audio_url: 音频 URL
- file: 文件
- multimodal: 多模态（混合内容）
"""
import sqlite3
import json
from typing import Dict, List, Optional, Union, Any
from datetime import datetime
from pathlib import Path
from enum import Enum
from ..core.context import ctx_logger as logger


class ContentType(str, Enum):
    """消息内容类型（与 OpenAI API 一致）"""
    TEXT = "text"
    IMAGE_URL = "image_url"
    IMAGE_BASE64 = "image_base64"
    VIDEO_URL = "video_url"
    AUDIO_URL = "audio_url"
    FILE = "file"
    MULTIMODAL = "multimodal"


class MessageStorage:
    """消息存储服务"""
    
    # 数据库版本，用于迁移
    DB_VERSION = 3  # 升级版本：自增 ID
    
    def __init__(self, db_path: str = "data/conversations.db"):
        """初始化存储服务"""
        db_file = Path(db_path)
        db_file.parent.mkdir(parents=True, exist_ok=True)
        
        self.db_path = db_path
        self._init_database()
        logger.info(f"消息存储服务初始化完成 | db_path={db_path}")
    
    def _init_database(self):
        """初始化数据库表"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("PRAGMA user_version")
        current_version = cursor.fetchone()[0]
        
        if current_version < self.DB_VERSION:
            # 如果是旧版本，需要迁移
            if current_version > 0:
                logger.warning(f"数据库版本升级: {current_version} -> {self.DB_VERSION}，将重建表")
                cursor.execute("DROP TABLE IF EXISTS messages")
                cursor.execute("DROP TABLE IF EXISTS conversations")
            
            self._create_tables(cursor)
            cursor.execute(f"PRAGMA user_version = {self.DB_VERSION}")
        
        conn.commit()
        conn.close()
    
    def _create_tables(self, cursor):
        """创建数据库表（使用自增 ID）"""
        # 会话表：cid 自增
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                cid INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                metadata TEXT,
                system_message TEXT
            )
        """)
        
        # 消息表：message_id 自增
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                message_id INTEGER PRIMARY KEY AUTOINCREMENT,
                cid INTEGER NOT NULL,
                role TEXT NOT NULL,
                content_type TEXT NOT NULL DEFAULT 'text',
                content TEXT NOT NULL,
                metadata TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (cid) REFERENCES conversations(cid)
            )
        """)
        
        # 索引
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_messages_cid ON messages(cid)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_messages_id_cid ON messages(message_id, cid)")
        
        logger.info("数据库表创建完成（自增 ID 模式）")
    
    @staticmethod
    def _detect_content_type(content: Union[str, List, Dict]) -> str:
        """自动检测内容类型"""
        if isinstance(content, str):
            return ContentType.TEXT.value
        elif isinstance(content, list):
            return ContentType.MULTIMODAL.value
        elif isinstance(content, dict):
            return content.get("type", ContentType.TEXT.value)
        return ContentType.TEXT.value
    
    @staticmethod
    def _serialize_content(content: Union[str, List, Dict]) -> str:
        """序列化消息内容"""
        if isinstance(content, str):
            return content
        return json.dumps(content, ensure_ascii=False)
    
    @staticmethod
    def _deserialize_content(content_str: str, content_type: str) -> Union[str, List, Dict]:
        """反序列化消息内容"""
        if content_type == ContentType.TEXT.value:
            try:
                return json.loads(content_str)
            except (json.JSONDecodeError, TypeError):
                return content_str
        try:
            return json.loads(content_str)
        except (json.JSONDecodeError, TypeError):
            return content_str
    
    # ==================== 会话操作 ====================
    
    def create_conversation(
        self,
        system_message: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> int:
        """
        创建新会话
        
        Returns:
            cid (整数)
        """
        now = datetime.now().isoformat()
        metadata_json = json.dumps(metadata, ensure_ascii=False) if metadata else None
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT INTO conversations (created_at, updated_at, metadata, system_message)
                VALUES (?, ?, ?, ?)
            """, (now, now, metadata_json, system_message))
            
            cid = cursor.lastrowid
            
            # 如果有系统消息，添加到消息表
            if system_message:
                cursor.execute("""
                    INSERT INTO messages (cid, role, content_type, content, metadata, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (cid, "system", ContentType.TEXT.value, system_message, None, now))
            
            conn.commit()
            logger.info(f"会话创建成功 | cid={cid}")
            return cid
        except Exception as e:
            logger.error(f"会话创建失败 | error={str(e)}")
            raise
        finally:
            conn.close()
    
    def get_conversation(self, cid: int) -> Optional[Dict]:
        """获取会话信息"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT cid, created_at, updated_at, metadata, system_message
                FROM conversations WHERE cid = ?
            """, (cid,))
            
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
                "cid": row["cid"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
                "metadata": metadata,
                "system_message": row["system_message"]
            }
        finally:
            conn.close()
    
    def get_conversation_with_messages(self, cid: int) -> Optional[Dict]:
        """获取会话及其所有消息"""
        conversation = self.get_conversation(cid)
        if conversation is None:
            return None
        
        messages = self.get_messages(cid)
        conversation["messages"] = messages
        conversation["message_count"] = len(messages)
        
        return conversation
    
    def delete_conversation(self, cid: int) -> bool:
        """删除会话及其所有消息"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("DELETE FROM messages WHERE cid = ?", (cid,))
            cursor.execute("DELETE FROM conversations WHERE cid = ?", (cid,))
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()
    
    def list_conversations(self, limit: Optional[int] = None, offset: int = 0) -> List[Dict]:
        """列出所有会话"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        try:
            query = """
                SELECT c.cid, c.created_at, c.updated_at, c.metadata,
                       COUNT(m.message_id) as message_count
                FROM conversations c
                LEFT JOIN messages m ON c.cid = m.cid
                GROUP BY c.cid
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
                    "cid": row["cid"],
                    "created_at": row["created_at"],
                    "updated_at": row["updated_at"],
                    "metadata": metadata,
                    "message_count": row["message_count"]
                })
            
            return conversations
        finally:
            conn.close()
    
    # ==================== 消息操作 ====================
    
    def add_message(
        self,
        cid: int,
        role: str,
        content: Union[str, List, Dict],
        content_type: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> int:
        """
        添加消息到会话
        
        Args:
            cid: 会话ID（整数）
            role: 消息角色 (user, assistant, system)
            content: 消息内容
            content_type: 内容类型，不提供则自动检测
            metadata: 消息元数据
            
        Returns:
            message_id（整数）
        """
        if content_type is None:
            content_type = self._detect_content_type(content)
        
        content_str = self._serialize_content(content)
        metadata_json = json.dumps(metadata, ensure_ascii=False) if metadata else None
        now = datetime.now().isoformat()
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT INTO messages (cid, role, content_type, content, metadata, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (cid, role, content_type, content_str, metadata_json, now))
            
            message_id = cursor.lastrowid
            
            # 更新会话的更新时间
            cursor.execute("UPDATE conversations SET updated_at = ? WHERE cid = ?", (now, cid))
            
            conn.commit()
            logger.debug(f"消息添加成功 | cid={cid} | message_id={message_id} | role={role}")
            return message_id
        except Exception as e:
            logger.error(f"消息添加失败 | cid={cid} | error={str(e)}")
            raise
        finally:
            conn.close()
    
    def get_message(self, message_id: int) -> Optional[Dict]:
        """获取单条消息"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT message_id, cid, role, content_type, content, metadata, created_at
                FROM messages WHERE message_id = ?
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
            "cid": row["cid"],
            "role": row["role"],
            "content_type": row["content_type"],
            "content": content,
            "metadata": metadata,
            "created_at": row["created_at"]
        }
    
    def get_messages(
        self,
        cid: int,
        limit: Optional[int] = None,
        offset: int = 0
    ) -> List[Dict]:
        """获取会话的所有消息（按 message_id 升序）"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        try:
            query = """
                SELECT message_id, cid, role, content_type, content, metadata, created_at
                FROM messages WHERE cid = ?
                ORDER BY message_id ASC
            """
            params: List[Any] = [cid]
            
            if limit:
                query += " LIMIT ? OFFSET ?"
                params.extend([limit, offset])
            
            cursor.execute(query, params)
            return [self._row_to_message(row) for row in cursor.fetchall()]
        finally:
            conn.close()
    
    def get_history_before_message(
        self,
        cid: int,
        before_message_id: int,
        limit: Optional[int] = None
    ) -> List[Dict]:
        """
        获取指定消息之前的历史消息
        
        Args:
            cid: 会话ID
            before_message_id: 在此消息之前（不包含此消息）
            limit: 最多返回条数（从最近的开始）
            
        Returns:
            消息列表（按 message_id 升序）
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        try:
            if limit:
                # 先取最近的 N 条，再按升序排列
                query = """
                    SELECT * FROM (
                        SELECT message_id, cid, role, content_type, content, metadata, created_at
                        FROM messages
                        WHERE cid = ? AND message_id < ?
                        ORDER BY message_id DESC
                        LIMIT ?
                    ) ORDER BY message_id ASC
                """
                cursor.execute(query, (cid, before_message_id, limit))
            else:
                query = """
                    SELECT message_id, cid, role, content_type, content, metadata, created_at
                    FROM messages
                    WHERE cid = ? AND message_id < ?
                    ORDER BY message_id ASC
                """
                cursor.execute(query, (cid, before_message_id))
            
            return [self._row_to_message(row) for row in cursor.fetchall()]
        finally:
            conn.close()
    
    def get_messages_for_llm(
        self,
        cid: int,
        before_message_id: Optional[int] = None,
        limit: Optional[int] = None
    ) -> List[Dict]:
        """
        获取 LLM API 格式的消息列表
        
        Args:
            cid: 会话ID
            before_message_id: 如果提供，获取此消息之前的历史
            limit: 最多返回条数
            
        Returns:
            LLM API 格式的消息列表 [{"role": "...", "content": "..."}]
        """
        if before_message_id:
            messages = self.get_history_before_message(cid, before_message_id, limit)
        else:
            messages = self.get_messages(cid, limit)
        
        return [{"role": msg["role"], "content": msg["content"]} for msg in messages]
    
    def update_message_content(
        self,
        message_id: int,
        content: Union[str, List, Dict],
        content_type: Optional[str] = None
    ) -> bool:
        """更新消息内容"""
        if content_type is None:
            content_type = self._detect_content_type(content)
        
        content_str = self._serialize_content(content)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                UPDATE messages SET content = ?, content_type = ?
                WHERE message_id = ?
            """, (content_str, content_type, message_id))
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()
    
    def update_message_metadata(self, message_id: int, metadata: Dict) -> bool:
        """更新消息 metadata"""
        metadata_json = json.dumps(metadata, ensure_ascii=False)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("UPDATE messages SET metadata = ? WHERE message_id = ?", 
                          (metadata_json, message_id))
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()
    
    def delete_message(self, message_id: int) -> bool:
        """删除单条消息"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("DELETE FROM messages WHERE message_id = ?", (message_id,))
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()
    
    def clear_conversation_messages(self, cid: int) -> bool:
        """清空会话的所有消息"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("DELETE FROM messages WHERE cid = ?", (cid,))
            conn.commit()
            return True
        finally:
            conn.close()


# 全局存储实例
message_storage = MessageStorage()

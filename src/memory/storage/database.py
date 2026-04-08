"""
Memory 数据库

SQLite 存储引擎，支持原始消息、摘要、工具响应等
"""

import sqlite3
import json
from pathlib import Path
from typing import Optional, List, Dict
from datetime import datetime


class MemoryDatabase:
    """
    Memory 数据库 - SQLite 存储引擎
    
    存储:
    - 原始消息 (raw_messages)
    - 摘要 (summaries)
    - 工具响应 (tool_responses)
    - 会话元数据 (conversations)
    - 记忆提取记录 (memory_extractions)
    """
    
    def __init__(self, data_dir: str = "fagent_memory"):
        """
        初始化数据库
        
        Args:
            data_dir: 数据目录
        """
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.db_path = self.data_dir / "memory.db"
        self._init_tables()
    
    def _init_tables(self):
        """初始化数据库表"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # === 原始消息表 ===
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS raw_messages (
                cid TEXT NOT NULL,
                mid TEXT NOT NULL,
                parent_mid TEXT,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                content_hash TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                sequence_num INTEGER NOT NULL,
                tool_name TEXT,
                tool_call_id TEXT,
                tool_response_size INTEGER,
                attachments TEXT,
                metadata TEXT,
                status TEXT NOT NULL DEFAULT 'raw',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                PRIMARY KEY (cid, mid)
            )
        ''')
        
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_messages_cid ON raw_messages(cid)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_messages_hash ON raw_messages(content_hash)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_messages_seq ON raw_messages(cid, sequence_num)')
        
        # === 摘要表 ===
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS summaries (
                sid TEXT PRIMARY KEY,
                cid TEXT NOT NULL,
                summary_type TEXT NOT NULL,
                covered_mids TEXT NOT NULL,
                start_mid TEXT NOT NULL,
                end_mid TEXT NOT NULL,
                message_count INTEGER NOT NULL,
                summary TEXT NOT NULL,
                key_points TEXT,
                entities TEXT,
                topics TEXT,
                parent_summary_id TEXT,
                child_summary_ids TEXT,
                can_expand INTEGER DEFAULT 1,
                expansion_hint TEXT,
                created_at TEXT NOT NULL,
                created_by TEXT NOT NULL DEFAULT 'auto'
            )
        ''')
        
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_summaries_cid ON summaries(cid)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_summaries_parent ON summaries(parent_summary_id)')
        
        # === 工具响应表 ===
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tool_responses (
                rid TEXT PRIMARY KEY,
                cid TEXT NOT NULL,
                mid TEXT NOT NULL,
                tool_call_id TEXT NOT NULL,
                tool_name TEXT NOT NULL,
                tool_input TEXT NOT NULL,
                response_size INTEGER NOT NULL,
                storage_type TEXT NOT NULL,
                inline_content TEXT,
                file_path TEXT,
                index_data TEXT,
                summary TEXT NOT NULL,
                key_data TEXT,
                can_load_full INTEGER DEFAULT 1,
                load_hint TEXT,
                created_at TEXT NOT NULL,
                execution_time_ms INTEGER
            )
        ''')
        
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_responses_cid ON tool_responses(cid)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_responses_tool ON tool_responses(tool_name)')
        
        # === 会话元数据表 ===
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS conversations (
                cid TEXT PRIMARY KEY,
                title TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                message_count INTEGER DEFAULT 0,
                last_message_mid TEXT,
                status TEXT NOT NULL DEFAULT 'active'
            )
        ''')
        
        # === 记忆提取记录表 ===
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS memory_extractions (
                extraction_id TEXT PRIMARY KEY,
                cid TEXT NOT NULL,
                mid TEXT NOT NULL,
                intent_type TEXT NOT NULL,
                confidence REAL NOT NULL,
                extracted_data TEXT,
                saved_to_immediate INTEGER DEFAULT 0,
                saved_to_working INTEGER DEFAULT 0,
                saved_to_longterm INTEGER DEFAULT 0,
                created_at TEXT NOT NULL
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def get_tables(self) -> List[str]:
        """获取所有表名"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        conn.close()
        return tables
    
    def table_exists(self, table_name: str) -> bool:
        """检查表是否存在"""
        return table_name in self.get_tables()
    
    def get_table_count(self, table_name: str) -> int:
        """获取表记录数"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        count = cursor.fetchone()[0]
        conn.close()
        return count
    
    # ==================== 原始消息操作 ====================
    
    def save_message(self, msg: "RawMessage"):
        """保存原始消息"""
        from memory.models.message import Role, MessageStatus
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO raw_messages VALUES 
            (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            msg.cid, msg.mid, msg.parent_mid,
            msg.role.value, msg.content, msg.content_hash,
            msg.timestamp, msg.sequence_num,
            msg.tool_name, msg.tool_call_id, msg.tool_response_size,
            json.dumps(msg.attachments), json.dumps(msg.metadata),
            msg.status.value, msg.created_at, msg.updated_at
        ))
        
        # 更新会话元数据
        self._update_conversation(msg.cid, msg.mid, conn)
        
        conn.commit()
        conn.close()
    
    def get_message(self, cid: str, mid: str) -> Optional["RawMessage"]:
        """获取单条消息"""
        from memory.models.message import RawMessage, Role, MessageStatus
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM raw_messages WHERE cid = ? AND mid = ?', (cid, mid))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return RawMessage(
                cid=row[0], mid=row[1], parent_mid=row[2],
                role=Role(row[3]), content=row[4], content_hash=row[5],
                timestamp=row[6], sequence_num=row[7],
                tool_name=row[8], tool_call_id=row[9], tool_response_size=row[10],
                attachments=json.loads(row[11]) if row[11] else [],
                metadata=json.loads(row[12]) if row[12] else {},
                status=MessageStatus(row[13]), created_at=row[14], updated_at=row[15]
            )
        return None
    
    def get_messages(self, cid: str, start: int = 0, limit: int = 100) -> List["RawMessage"]:
        """获取会话消息（分页）"""
        from memory.models.message import RawMessage, Role, MessageStatus
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM raw_messages 
            WHERE cid = ? 
            ORDER BY sequence_num ASC 
            LIMIT ? OFFSET ?
        ''', (cid, limit, start))
        
        messages = []
        for row in cursor.fetchall():
            msg = RawMessage(
                cid=row[0], mid=row[1], parent_mid=row[2],
                role=Role(row[3]), content=row[4], content_hash=row[5],
                timestamp=row[6], sequence_num=row[7],
                tool_name=row[8], tool_call_id=row[9], tool_response_size=row[10],
                attachments=json.loads(row[11]) if row[11] else [],
                metadata=json.loads(row[12]) if row[12] else {},
                status=MessageStatus(row[13]), created_at=row[14], updated_at=row[15]
            )
            messages.append(msg)
        
        conn.close()
        return messages
    
    def delete_message(self, cid: str, mid: str) -> bool:
        """删除消息"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('DELETE FROM raw_messages WHERE cid = ? AND mid = ?', (cid, mid))
        deleted = cursor.rowcount > 0
        
        conn.commit()
        conn.close()
        return deleted
    
    def _update_conversation(self, cid: str, last_mid: str, conn):
        """更新会话元数据"""
        cursor = conn.cursor()
        
        # 获取消息数
        cursor.execute('SELECT COUNT(*) FROM raw_messages WHERE cid = ?', (cid,))
        count = cursor.fetchone()[0]
        
        # 获取时间戳
        cursor.execute('SELECT timestamp FROM raw_messages WHERE cid = ? AND mid = ?', (cid, last_mid))
        timestamp = cursor.fetchone()[0]
        
        # 插入或更新
        cursor.execute('''
            INSERT OR REPLACE INTO conversations VALUES 
            (?, ?, ?, ?, ?, ?, ?)
        ''', (
            cid, None, timestamp, timestamp, count, last_mid, 'active'
        ))

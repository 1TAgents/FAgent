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

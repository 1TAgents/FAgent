"""
Memory Manager - Memory 系统统一入口

提供会话管理、消息存储等基础功能
"""

import sqlite3
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict
import uuid


class MemoryManager:
    """Memory Manager - 管理会话和基础数据"""
    
    _instance = None
    _current_cid: Optional[str] = None
    
    def __new__(cls, data_dir: str = "fagent_memory"):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, data_dir: str = "fagent_memory"):
        if self._initialized:
            return
        
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.db_path = self.data_dir / "memory.db"
        self._init_database()
        self._initialized = True
    
    @property
    def current_cid(self) -> Optional[str]:
        """获取当前会话 ID"""
        return self._current_cid
    
    @current_cid.setter
    def current_cid(self, cid: str):
        """设置当前会话 ID"""
        self._current_cid = cid
    
    def _init_database(self):
        """初始化数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 创建会话表
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
        
        conn.commit()
        conn.close()
    
    # ==================== 会话管理 ====================
    
    def start_session(self, title: str = None) -> str:
        """
        创建新会话
        
        Returns:
            str: 会话 ID (cid)
        """
        cid = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
        now = datetime.now().isoformat()
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO conversations (cid, title, created_at, updated_at, status)
            VALUES (?, ?, ?, ?, 'active')
        ''', (cid, title or f"会话 {cid[-6:]}", now, now))
        
        conn.commit()
        conn.close()
        
        # 自动切换到新会话
        self._current_cid = cid
        
        return cid
    
    def list_sessions(self, status: str = "active") -> List[Dict]:
        """
        列出所有会话
        
        Args:
            status: 会话状态过滤
        
        Returns:
            List[Dict]: 会话列表
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT cid, title, created_at, updated_at, message_count, status
            FROM conversations
            WHERE status = ?
            ORDER BY updated_at DESC
        ''', (status,))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [
            {
                "cid": row[0],
                "title": row[1],
                "created_at": row[2],
                "updated_at": row[3],
                "message_count": row[4],
                "status": row[5]
            }
            for row in rows
        ]
    
    def switch_session(self, cid: str) -> bool:
        """
        切换会话
        
        Args:
            cid: 会话 ID
        
        Returns:
            bool: 是否成功切换
        """
        # 检查会话是否存在
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT cid FROM conversations WHERE cid = ?', (cid,))
        exists = cursor.fetchone() is not None
        conn.close()
        
        if exists:
            self._current_cid = cid
            return True
        return False
    
    def get_session_info(self, cid: str = None) -> Optional[Dict]:
        """
        获取会话信息
        
        Args:
            cid: 会话 ID（默认当前会话）
        
        Returns:
            Optional[Dict]: 会话信息
        """
        cid = cid or self._current_cid
        if not cid:
            return None
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT cid, title, created_at, updated_at, message_count, status
            FROM conversations
            WHERE cid = ?
        ''', (cid,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {
                "cid": row[0],
                "title": row[1],
                "created_at": row[2],
                "updated_at": row[3],
                "message_count": row[4],
                "status": row[5]
            }
        return None
    
    def delete_session(self, cid: str) -> bool:
        """
        删除会话（软删除）
        
        Args:
            cid: 会话 ID
        
        Returns:
            bool: 是否成功删除
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 更新状态为 deleted
        cursor.execute('''
            UPDATE conversations
            SET status = 'deleted', updated_at = ?
            WHERE cid = ?
        ''', (datetime.now().isoformat(), cid))
        
        affected = cursor.rowcount
        conn.commit()
        conn.close()
        
        # 如果删除的是当前会话，清空当前会话
        if affected and self._current_cid == cid:
            self._current_cid = None
        
        return affected > 0

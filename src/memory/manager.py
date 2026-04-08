"""
Memory Manager - Memory 系统统一入口

整合 ID 体系、数据模型、存储层、API 层
"""

from pathlib import Path
from datetime import datetime
from typing import Optional, List
import sys

# 延迟导入，避免循环依赖
from .ids import MemoryID, generate_cid
from .storage.database import MemoryDatabase


class MemoryManager:
    """
    Memory Manager - Memory 系统统一入口
    
    提供:
    - 会话管理
    - 消息存储
    - 摘要管理
    - 工具响应管理
    - 逐渐披露 API
    """
    
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
        
        # 初始化存储层
        self.db = MemoryDatabase(str(self.data_dir))
        
        # ID 缓存
        self._id_counter = 0
        
        self._initialized = True
    
    @property
    def current_cid(self) -> Optional[str]:
        """获取当前会话 ID"""
        return self._current_cid
    
    @current_cid.setter
    def current_cid(self, cid: str):
        """设置当前会话 ID"""
        self._current_cid = cid
    
    # ==================== 会话管理 ====================
    
    def start_session(self, title: str = None) -> str:
        """
        创建新会话
        
        Returns:
            str: 会话 ID (cid)
        """
        cid = generate_cid()
        now = datetime.now().isoformat()
        
        conn = self.db.db_path
        import sqlite3
        conn_sqlite = sqlite3.connect(conn)
        cursor = conn_sqlite.cursor()
        
        cursor.execute('''
            INSERT INTO conversations (cid, title, created_at, updated_at, status)
            VALUES (?, ?, ?, ?, 'active')
        ''', (cid, title or f"会话 {cid[-6:]}", now, now))
        
        conn_sqlite.commit()
        conn_sqlite.close()
        
        # 自动切换到新会话
        self._current_cid = cid
        
        return cid
    
    def list_sessions(self, status: str = "active") -> List[dict]:
        """列出所有会话"""
        import sqlite3
        conn = sqlite3.connect(self.db.db_path)
        cursor = conn.cursor()
        
        if status == 'all':
            cursor.execute('''
                SELECT cid, title, created_at, updated_at, message_count, status
                FROM conversations
                ORDER BY updated_at DESC
            ''')
        else:
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
        """切换会话"""
        import sqlite3
        conn = sqlite3.connect(self.db.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT cid FROM conversations WHERE cid = ?', (cid,))
        exists = cursor.fetchone() is not None
        conn.close()
        
        if exists:
            self._current_cid = cid
            return True
        return False
    
    def get_session_info(self, cid: str = None) -> Optional[dict]:
        """获取会话信息"""
        cid = cid or self._current_cid
        if not cid:
            return None
        
        import sqlite3
        conn = sqlite3.connect(self.db.db_path)
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
        """删除会话（软删除）"""
        if cid == self._current_cid:
            return False
        
        import sqlite3
        conn = sqlite3.connect(self.db.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE conversations
            SET status = 'deleted', updated_at = ?
            WHERE cid = ?
        ''', (datetime.now().isoformat(), cid))
        
        affected = cursor.rowcount > 0
        
        conn.commit()
        conn.close()
        
        if affected and self._current_cid == cid:
            self._current_cid = None
        
        return affected
    
    # ==================== 消息操作 ====================
    
    def save_message(self, cid: str, role: str, content: str, 
                     sequence_num: int = None, **kwargs) -> str:
        """
        保存消息
        
        Args:
            cid: 会话 ID
            role: 消息角色 (user/assistant/system/tool)
            content: 消息内容
            sequence_num: 序号（自动分配）
        
        Returns:
            str: 消息 ID (mid)
        """
        from .models import RawMessage, Role
        
        # 自动分配序号
        if sequence_num is None:
            messages = self.db.get_messages(cid)
            sequence_num = len(messages)
        
        # 生成消息 ID
        msg_id = MemoryID.new_message(cid)
        
        # 创建消息对象
        msg = RawMessage(
            cid=cid,
            mid=msg_id.mid,
            role=Role(role),
            content=content,
            sequence_num=sequence_num,
            **kwargs
        )
        
        # 保存到数据库
        self.db.save_message(msg)
        
        return msg.mid
    
    def get_message(self, cid: str, mid: str):
        """获取单条消息"""
        return self.db.get_message(cid, mid)
    
    def get_messages(self, cid: str, start: int = 0, limit: int = 100):
        """获取消息列表（分页）"""
        return self.db.get_messages(cid, start, limit)
    
    # ==================== 摘要操作 ====================
    
    def save_summary(self, summary):
        """保存摘要"""
        self.db.save_summary(summary)
    
    def get_summary(self, sid: str):
        """获取摘要"""
        return self.db.get_summary(sid)
    
    def get_summaries(self, cid: str):
        """获取会话摘要列表"""
        return self.db.get_summaries_for_conversation(cid)
    
    # ==================== 工具响应操作 ====================
    
    def save_tool_response(self, response):
        """保存工具响应"""
        self.db.save_tool_response(response)
    
    def get_tool_response(self, rid: str):
        """获取工具响应"""
        return self.db.get_tool_response(rid)

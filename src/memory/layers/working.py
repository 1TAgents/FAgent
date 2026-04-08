"""
L2 工作记忆

任务级记忆，SQLite 存储，任务结束清理
"""

import sqlite3
import json
from pathlib import Path
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from typing import Optional, List, Dict


@dataclass
class Task:
    """任务"""
    task_id: str
    task_type: str  # analysis | trade | review | backtest
    title: str
    context: Dict
    status: str  # pending | active | completed | failed
    decision_chain: List[Dict]
    todo_queue: List[Dict]
    created_at: str
    expires_at: str
    result: Optional[Dict] = None


class WorkingMemory:
    """
    L2 工作记忆 - 任务级，SQLite 存储
    
    存储:
    - 当前任务上下文
    - 决策链记录
    - 持仓状态快照
    - 待办事项队列
    """
    
    def __init__(self, db_path: str):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
    
    def _init_db(self):
        """初始化数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tasks (
                task_id TEXT PRIMARY KEY,
                task_type TEXT NOT NULL,
                title TEXT NOT NULL,
                context TEXT,
                status TEXT NOT NULL,
                decision_chain TEXT,
                todo_queue TEXT,
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                result TEXT,
                updated_at TEXT NOT NULL
            )
        ''')
        
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_status ON tasks(status)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_type ON tasks(task_type)')
        
        conn.commit()
        conn.close()
    
    def create_task(self, task: Task) -> str:
        """创建新任务"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO tasks VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            task.task_id, task.task_type, task.title,
            json.dumps(task.context), task.status,
            json.dumps(task.decision_chain), json.dumps(task.todo_queue),
            task.created_at, task.expires_at,
            json.dumps(task.result) if task.result else None,
            task.created_at
        ))
        
        conn.commit()
        conn.close()
        return task.task_id
    
    def get_task(self, task_id: str) -> Optional[Task]:
        """获取任务"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM tasks WHERE task_id = ?', (task_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return self._row_to_task(row)
        return None
    
    def get_active_tasks(self) -> List[Task]:
        """获取所有活跃任务"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM tasks 
            WHERE status IN ('pending', 'active') 
            AND expires_at > ?
            ORDER BY created_at DESC
        ''', (datetime.now().isoformat(),))
        
        tasks = [self._row_to_task(row) for row in cursor.fetchall()]
        conn.close()
        return tasks
    
    def update_task_status(self, task_id: str, status: str, result: Dict = None):
        """更新任务状态"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE tasks 
            SET status = ?, result = ?, updated_at = ?
            WHERE task_id = ?
        ''', (
            status,
            json.dumps(result) if result else None,
            datetime.now().isoformat(),
            task_id
        ))
        
        conn.commit()
        conn.close()
    
    def append_decision(self, task_id: str, decision: Dict):
        """追加决策记录到决策链"""
        task = self.get_task(task_id)
        if task:
            task.decision_chain.append(decision)
            self.update_task(task)
    
    def add_todo(self, task_id: str, todo: Dict):
        """添加待办到队列"""
        task = self.get_task(task_id)
        if task:
            task.todo_queue.append(todo)
            self.update_task(task)
    
    def cleanup_expired(self) -> int:
        """清理过期任务"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            DELETE FROM tasks 
            WHERE expires_at < ? AND status = 'completed'
        ''', (datetime.now().isoformat(),))
        
        deleted = cursor.rowcount
        conn.commit()
        conn.close()
        return deleted
    
    def _row_to_task(self, row) -> Task:
        return Task(
            task_id=row[0], task_type=row[1], title=row[2],
            context=json.loads(row[3]), status=row[4],
            decision_chain=json.loads(row[5]),
            todo_queue=json.loads(row[6]),
            created_at=row[7], expires_at=row[8],
            result=json.loads(row[9]) if row[9] else None,
            updated_at=row[10]
        )

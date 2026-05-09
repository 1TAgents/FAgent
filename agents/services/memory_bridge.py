"""
Memory Bridge - 记忆系统与 Agent 工作流的桥梁

在现有 src/memory/ 系统之上，提供 Agent 友好的接口：
- recall(): 每次用户消息前召回相关记忆
- store(): 每次助手回复后提取并存储新记忆
- format_for_prompt(): 格式化为可注入 prompt 的文本

设计参考：hermes-agent 的 memory plugin lifecycle (prefetch/sync_turn/flush)
"""
from __future__ import annotations

import json
import logging
import sqlite3
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Dict

logger = logging.getLogger(__name__)

MEMORY_DIR = Path(__file__).parent.parent.parent / "fagent_memory"
MEMORY_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class MemoryEntry:
    """一条记忆记录。"""
    id: str
    category: str       # user_preference | project_context | trade_history | fact
    content: str
    source_cid: Optional[str] = None
    created_at: float = 0.0
    relevance_score: float = 1.0

    def to_prompt_line(self) -> str:
        return f"[{self.category}] {self.content}"


class MemoryBridge:
    """记忆桥接器。

    负责：
    1. 从消息历史中提取并持久化记忆条目
    2. 根据用户/会话召回相关记忆
    3. 格式化为 prompt 可注入的文本
    """

    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            db_path = str(MEMORY_DIR / "agent_memory.db")
        self._db_path = db_path
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(self._db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS agent_memories (
                    id TEXT PRIMARY KEY,
                    category TEXT NOT NULL,
                    content TEXT NOT NULL,
                    source_cid TEXT,
                    created_at REAL NOT NULL,
                    relevance_score REAL DEFAULT 1.0
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_memories_category
                ON agent_memories(category)
            """)

    # ========== Recall ==========

    def recall(
        self,
        category: Optional[str] = None,
        limit: int = 10,
    ) -> List[MemoryEntry]:
        """召回相关记忆。

        Args:
            category: 按类别过滤（user_preference/project_context/trade_history/fact）
            limit: 返回数量上限
        """
        query = "SELECT id, category, content, source_cid, created_at, relevance_score FROM agent_memories"
        params: tuple = ()

        if category:
            query += " WHERE category = ?"
            params = (category,)

        query += " ORDER BY relevance_score DESC, created_at DESC LIMIT ?"
        params = params + (limit,)

        with sqlite3.connect(self._db_path) as conn:
            rows = conn.execute(query, params).fetchall()

        return [
            MemoryEntry(
                id=r[0], category=r[1], content=r[2],
                source_cid=r[3], created_at=r[4], relevance_score=r[5],
            )
            for r in rows
        ]

    def recall_all(self, limit_per_category: int = 5) -> List[MemoryEntry]:
        """从所有类别召回记忆。"""
        all_memories = []
        for cat in ["user_preference", "project_context", "trade_history", "fact"]:
            all_memories.extend(self.recall(category=cat, limit=limit_per_category))
        return all_memories

    # ========== Store ==========

    def store(self, entry: MemoryEntry) -> str:
        """存储一条新记忆。"""
        if not entry.created_at:
            entry.created_at = time.time()
        if not entry.id:
            entry.id = f"mem_{int(entry.created_at * 1000)}"

        with sqlite3.connect(self._db_path) as conn:
            conn.execute(
                """INSERT OR REPLACE INTO agent_memories
                   (id, category, content, source_cid, created_at, relevance_score)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    entry.id, entry.category, entry.content,
                    entry.source_cid, entry.created_at, entry.relevance_score,
                ),
            )
        logger.debug(f"Memory stored: {entry.id} ({entry.category})")
        return entry.id

    def store_many(self, entries: List[MemoryEntry]) -> List[str]:
        """批量存储记忆。"""
        return [self.store(e) for e in entries]

    # ========== Delete ==========

    def delete(self, memory_id: str) -> bool:
        """删除指定记忆。"""
        with sqlite3.connect(self._db_path) as conn:
            cursor = conn.execute("DELETE FROM agent_memories WHERE id = ?", (memory_id,))
            return cursor.rowcount > 0

    def clear_category(self, category: str) -> int:
        """清空某类别的所有记忆。"""
        with sqlite3.connect(self._db_path) as conn:
            cursor = conn.execute("DELETE FROM agent_memories WHERE category = ?", (category,))
            return cursor.rowcount

    # ========== Format ==========

    def format_for_prompt(
        self,
        entries: Optional[List[MemoryEntry]] = None,
        max_entries: int = 10,
    ) -> Optional[str]:
        """格式化记忆为可注入 prompt 的文本。

        Returns:
            格式化的文本，或 None（无记忆时）
        """
        if entries is None:
            entries = self.recall_all(limit_per_category=max_entries)

        if not entries:
            return None

        lines = ["【记忆上下文】"]
        for e in entries:
            lines.append(f"- {e.to_prompt_line()}")
        return "\n".join(lines)

    # ========== Stats ==========

    def stats(self) -> Dict[str, int]:
        """返回记忆统计信息。"""
        with sqlite3.connect(self._db_path) as conn:
            row = conn.execute("SELECT COUNT(*) FROM agent_memories").fetchone()
            total = row[0] if row else 0

            rows = conn.execute(
                "SELECT category, COUNT(*) FROM agent_memories GROUP BY category"
            ).fetchall()
            by_category = {r[0]: r[1] for r in rows}

        return {"total": total, "by_category": by_category}


# 全局单例
memory_bridge = MemoryBridge()

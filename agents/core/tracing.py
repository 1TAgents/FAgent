"""
Tracing - 结构化执行追踪

在现有链式日志（JSONL）之上，提供完整的单次请求追踪、
会话指标聚合、和回放能力。

核心概念：
- ExecutionTrace: 一次完整请求-响应链路的追踪记录
- TurnTrace: Agent 主循环中单步（LLM call + tool calls）的追踪
- SessionMetrics: 会话级别的聚合指标
- TraceStore: 追踪记录的存储和查询

设计参考：OpenTelemetry span 模型 + Vibe-Trading 的 run persistence。
"""
from __future__ import annotations

import json
import sqlite3
import time
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..core.logging import logger


@dataclass
class TurnTrace:
    """主循环中单步执行的追踪记录。

    一次 turn = 一次 LLM 调用 + 零到多次工具调用。
    """
    turn_id: int
    model: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    latency_ms: float = 0.0
    tool_calls: List[dict] = field(default_factory=list)
    tool_results: List[dict] = field(default_factory=list)
    error: Optional[str] = None

    def to_dict(self) -> dict:
        d = {
            "turn_id": self.turn_id,
            "model": self.model,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "latency_ms": round(self.latency_ms, 2),
            "tool_calls": self.tool_calls,
            "tool_results": self.tool_results,
        }
        if self.error:
            d["error"] = self.error
        return d


@dataclass
class ExecutionTrace:
    """一次完整请求的追踪记录。

    对应一次 /send 或 /stream 调用。
    """
    trace_id: str           # 唯一标识，格式: rid_{timestamp}
    cid: int = 0            # 会话 ID
    mid: int = 0            # 消息 ID
    rid: int = 0            # 请求 ID
    user_message: str = ""
    route: str = ""         # 路由决策（market/chat/backtest/trade/strategy）
    task_type: str = ""
    turns: List[TurnTrace] = field(default_factory=list)
    final_response: str = ""
    total_tokens: int = 0
    total_latency_ms: float = 0.0
    error: Optional[str] = None
    started_at: float = 0.0
    finished_at: float = 0.0

    def start_turn(self, turn_id: int = 1) -> TurnTrace:
        """开始一个新的 turn。"""
        turn = TurnTrace(turn_id=turn_id)
        self.turns.append(turn)
        return turn

    def summarize(self) -> dict:
        """生成摘要信息。"""
        return {
            "trace_id": self.trace_id,
            "cid": self.cid,
            "route": self.route,
            "task_type": self.task_type,
            "turns": len(self.turns),
            "total_tokens": self.total_tokens,
            "total_latency_ms": round(self.total_latency_ms, 2),
            "error": self.error,
        }

    def to_dict(self) -> dict:
        d = {
            "trace_id": self.trace_id,
            "cid": self.cid,
            "mid": self.mid,
            "rid": self.rid,
            "user_message": self.user_message,
            "route": self.route,
            "task_type": self.task_type,
            "turns": [t.to_dict() for t in self.turns],
            "final_response": self.final_response,
            "total_tokens": self.total_tokens,
            "total_latency_ms": round(self.total_latency_ms, 2),
            "started_at": self.started_at,
            "finished_at": self.finished_at,
        }
        if self.error:
            d["error"] = self.error
        return d


@dataclass
class SessionMetrics:
    """会话级别的聚合指标。"""
    cid: int
    total_requests: int = 0
    total_turns: int = 0
    total_tokens: int = 0
    total_latency_ms: float = 0.0
    route_distribution: Dict[str, int] = field(default_factory=dict)
    error_count: int = 0
    last_active: float = 0.0

    def record_trace(self, trace: ExecutionTrace) -> None:
        """从 ExecutionTrace 更新指标。"""
        self.total_requests += 1
        self.total_turns += len(trace.turns)
        self.total_tokens += trace.total_tokens
        self.total_latency_ms += trace.total_latency_ms
        if trace.route:
            self.route_distribution[trace.route] = (
                self.route_distribution.get(trace.route, 0) + 1
            )
        if trace.error:
            self.error_count += 1
        self.last_active = max(self.last_active, trace.finished_at)

    @property
    def avg_tokens_per_request(self) -> float:
        return self.total_tokens / max(self.total_requests, 1)

    @property
    def avg_latency_per_request(self) -> float:
        return self.total_latency_ms / max(self.total_requests, 1)

    def to_dict(self) -> dict:
        return {
            "cid": self.cid,
            "total_requests": self.total_requests,
            "total_turns": self.total_turns,
            "total_tokens": self.total_tokens,
            "total_latency_ms": round(self.total_latency_ms, 2),
            "avg_tokens_per_request": round(self.avg_tokens_per_request, 1),
            "avg_latency_ms": round(self.avg_latency_per_request, 2),
            "route_distribution": self.route_distribution,
            "error_count": self.error_count,
            "last_active": self.last_active,
        }


class TraceStore:
    """追踪记录存储。

    使用 SQLite 存储 ExecutionTrace，支持按会话查询和聚合。
    """

    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            db_path = str(Path(__file__).parent.parent.parent / "data" / "traces.db")
        self._db_path = db_path
        self._lock = threading.Lock()
        self._init_db()

    def _init_db(self) -> None:
        """初始化数据库表。"""
        with self._lock:
            with sqlite3.connect(self._db_path) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS traces (
                        trace_id TEXT PRIMARY KEY,
                        cid INTEGER NOT NULL,
                        mid INTEGER,
                        rid INTEGER,
                        user_message TEXT,
                        route TEXT,
                        task_type TEXT,
                        turns INTEGER DEFAULT 0,
                        total_tokens INTEGER DEFAULT 0,
                        total_latency_ms REAL DEFAULT 0,
                        error TEXT,
                        final_response TEXT,
                        trace_json TEXT,
                        created_at REAL NOT NULL
                    )
                """)
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_traces_cid
                    ON traces(cid)
                """)
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_traces_route
                    ON traces(route)
                """)

    def save(self, trace: ExecutionTrace) -> None:
        """保存 ExecutionTrace 到数据库。"""
        with self._lock:
            with sqlite3.connect(self._db_path) as conn:
                conn.execute(
                    """INSERT OR REPLACE INTO traces
                       (trace_id, cid, mid, rid, user_message, route, task_type,
                        turns, total_tokens, total_latency_ms, error,
                        final_response, trace_json, created_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        trace.trace_id,
                        trace.cid,
                        trace.mid,
                        trace.rid,
                        trace.user_message,
                        trace.route,
                        trace.task_type,
                        len(trace.turns),
                        trace.total_tokens,
                        trace.total_latency_ms,
                        trace.error,
                        trace.final_response,
                        json.dumps(trace.to_dict(), ensure_ascii=False),
                        trace.started_at or time.time(),
                    ),
                )
        logger.debug(f"Trace saved: {trace.trace_id} (cid={trace.cid})")

    def get_by_trace_id(self, trace_id: str) -> Optional[dict]:
        """按 trace_id 查询。"""
        with self._lock:
            with sqlite3.connect(self._db_path) as conn:
                conn.row_factory = sqlite3.Row
                row = conn.execute(
                    "SELECT * FROM traces WHERE trace_id = ?", (trace_id,)
                ).fetchone()
                if row:
                    return dict(row)
                return None

    def get_by_session(self, cid: int, limit: int = 20) -> List[dict]:
        """按会话 ID 查询最近的追踪记录。"""
        with self._lock:
            with sqlite3.connect(self._db_path) as conn:
                conn.row_factory = sqlite3.Row
                rows = conn.execute(
                    "SELECT * FROM traces WHERE cid = ? ORDER BY created_at DESC LIMIT ?",
                    (cid, limit),
                ).fetchall()
                return [dict(r) for r in rows]

    def get_session_metrics(self, cid: int) -> SessionMetrics:
        """计算会话级别的聚合指标。"""
        with self._lock:
            with sqlite3.connect(self._db_path) as conn:
                conn.row_factory = sqlite3.Row
                row = conn.execute(
                    """SELECT
                         COUNT(*) as total_requests,
                         SUM(turns) as total_turns,
                         SUM(total_tokens) as total_tokens,
                         SUM(total_latency_ms) as total_latency_ms,
                         COUNT(CASE WHEN error IS NOT NULL THEN 1 END) as error_count,
                         MAX(created_at) as last_active
                       FROM traces WHERE cid = ?""",
                    (cid,),
                ).fetchone()

                # 路由分布
                rows = conn.execute(
                    "SELECT route, COUNT(*) as cnt FROM traces WHERE cid = ? AND route IS NOT NULL GROUP BY route",
                    (cid,),
                ).fetchall()
                route_dist = {r["route"]: r["cnt"] for r in rows}

            metrics = SessionMetrics(cid=cid)
            if row and row["total_requests"]:
                metrics.total_requests = row["total_requests"]
                metrics.total_turns = row["total_turns"] or 0
                metrics.total_tokens = row["total_tokens"] or 0
                metrics.total_latency_ms = row["total_latency_ms"] or 0.0
                metrics.error_count = row["error_count"] or 0
                metrics.last_active = row["last_active"] or 0.0
                metrics.route_distribution = route_dist
            return metrics

    def get_recent_traces(self, limit: int = 50) -> List[dict]:
        """获取最近的追踪记录。"""
        with self._lock:
            with sqlite3.connect(self._db_path) as conn:
                conn.row_factory = sqlite3.Row
                rows = conn.execute(
                    "SELECT * FROM traces ORDER BY created_at DESC LIMIT ?",
                    (limit,),
                ).fetchall()
                return [dict(r) for r in rows]

    def get_traces_filtered(
        self,
        *,
        route: Optional[str] = None,
        cid: Optional[int] = None,
        start_ts: Optional[float] = None,
        end_ts: Optional[float] = None,
        limit: int = 50,
    ) -> List[dict]:
        """按条件过滤追踪记录。"""
        clauses = []
        params: list = []
        if route:
            clauses.append("route = ?")
            params.append(route)
        if cid is not None:
            clauses.append("cid = ?")
            params.append(cid)
        if start_ts is not None:
            clauses.append("created_at >= ?")
            params.append(start_ts)
        if end_ts is not None:
            clauses.append("created_at <= ?")
            params.append(end_ts)

        where = ""
        if clauses:
            where = "WHERE " + " AND ".join(clauses)

        with self._lock:
            with sqlite3.connect(self._db_path) as conn:
                conn.row_factory = sqlite3.Row
                rows = conn.execute(
                    f"SELECT * FROM traces {where} ORDER BY created_at DESC LIMIT ?",
                    params + [limit],
                ).fetchall()
                return [dict(r) for r in rows]

    def get_global_metrics(self) -> Dict[str, Any]:
        """获取全局聚合指标。"""
        with self._lock:
            with sqlite3.connect(self._db_path) as conn:
                conn.row_factory = sqlite3.Row
                row = conn.execute(
                    """SELECT
                         COUNT(*) as total_requests,
                         COUNT(DISTINCT cid) as unique_sessions,
                         SUM(turns) as total_turns,
                         SUM(total_tokens) as total_tokens,
                         SUM(total_latency_ms) as total_latency_ms,
                         COUNT(CASE WHEN error IS NOT NULL THEN 1 END) as error_count,
                         MIN(created_at) as first_active,
                         MAX(created_at) as last_active
                       FROM traces""",
                ).fetchone()

                # 路由分布
                route_rows = conn.execute(
                    "SELECT route, COUNT(*) as cnt, SUM(total_tokens) as tk FROM traces "
                    "WHERE route IS NOT NULL GROUP BY route ORDER BY cnt DESC",
                ).fetchall()
                route_dist = {
                    r["route"]: {"count": r["cnt"], "tokens": r["tk"] or 0}
                    for r in route_rows
                }

                # 按小时聚合（最近 24 小时）
                hour_rows = conn.execute(
                    """SELECT
                         strftime('%Y-%m-%d %H:00', datetime(created_at, 'unixepoch', 'localtime')) as hour,
                         COUNT(*) as cnt,
                         SUM(total_tokens) as tk
                       FROM traces
                       WHERE created_at >= ?
                       GROUP BY hour
                       ORDER BY hour""",
                    (time.time() - 86400,),
                ).fetchall()
                hourly = [
                    {"hour": r["hour"], "requests": r["cnt"], "tokens": r["tk"] or 0}
                    for r in hour_rows
                ]

        metrics = dict(row) if row else {}
        return {
            **metrics,
            "route_distribution": route_dist,
            "hourly_activity": hourly,
        }


# 全局单例
trace_store = TraceStore()

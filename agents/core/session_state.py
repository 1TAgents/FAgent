"""
Session State Machine - 会话生命周期管理

管理会话状态流转，支持取消、暂停、恢复。

状态流转：
    IDLE -> RUNNING -> FINISHED
    IDLE -> RUNNING -> ERROR
    RUNNING -> CANCELLED
    RUNNING -> WAITING -> RUNNING

设计参考：
- Vibe-Trading: session lifecycle with explicit state tracking
- OpenManus: task state machine for long-running operations
"""
from __future__ import annotations

import time
import threading
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class SessionState(str, Enum):
    """会话状态。"""
    IDLE = "idle"              # 等待用户输入
    RUNNING = "running"        # 正在处理
    WAITING = "waiting"        # 等待用户确认/审批
    FINISHED = "finished"      # 处理完成
    ERROR = "error"            # 处理出错
    CANCELLED = "cancelled"    # 被用户取消


@dataclass
class SessionInfo:
    """单个会话的状态信息。"""
    cid: int
    state: SessionState = SessionState.IDLE
    last_transition: float = field(default_factory=time.time)
    last_message: str = ""
    current_run_id: int = 0  # 当前第几次请求

    @property
    def is_active(self) -> bool:
        return self.state == SessionState.RUNNING

    @property
    def is_terminal(self) -> bool:
        return self.state in (
            SessionState.FINISHED,
            SessionState.ERROR,
            SessionState.CANCELLED,
        )

    def transition(self, new_state: SessionState) -> None:
        self.state = new_state
        self.last_transition = time.time()


class SessionStateManager:
    """会话状态管理器。

    管理 cid -> SessionInfo 的映射，提供状态查询和流转接口。
    """

    def __init__(self):
        self._sessions: Dict[int, SessionInfo] = {}
        self._lock = threading.Lock()

    def get_or_create(self, cid: int) -> SessionInfo:
        with self._lock:
            if cid not in self._sessions:
                self._sessions[cid] = SessionInfo(cid=cid)
            return self._sessions[cid]

    def get_state(self, cid: int) -> SessionState:
        info = self._sessions.get(cid)
        return info.state if info else SessionState.IDLE

    def is_running(self, cid: int) -> bool:
        return self.get_state(cid) == SessionState.RUNNING

    def start(self, cid: int, message_id: int = 0) -> None:
        info = self.get_or_create(cid)
        info.current_run_id = message_id
        info.transition(SessionState.RUNNING)
        logger.info(f"Session cid={cid} -> RUNNING")

    def cancel(self, cid: int) -> bool:
        info = self._sessions.get(cid)
        if info and info.is_active:
            info.transition(SessionState.CANCELLED)
            logger.info(f"Session cid={cid} -> CANCELLED")
            return True
        return False

    def finish(self, cid: int) -> None:
        info = self.get_or_create(cid)
        info.transition(SessionState.FINISHED)

    def set_error(self, cid: int) -> None:
        info = self.get_or_create(cid)
        info.transition(SessionState.ERROR)

    def wait(self, cid: int) -> None:
        info = self.get_or_create(cid)
        info.transition(SessionState.WAITING)

    def is_cancelled(self, cid: int) -> bool:
        return self.get_state(cid) == SessionState.CANCELLED

    def reset(self, cid: int) -> None:
        info = self.get_or_create(cid)
        info.transition(SessionState.IDLE)

    def get_info(self, cid: int) -> Optional[dict]:
        info = self._sessions.get(cid)
        if not info:
            return None
        return {
            "cid": info.cid,
            "state": info.state.value,
            "last_transition": info.last_transition,
            "current_run_id": info.current_run_id,
            "is_active": info.is_active,
            "is_terminal": info.is_terminal,
        }

    def list_active(self) -> list:
        return [
            self.get_info(cid)
            for cid, info in self._sessions.items()
            if info.is_active
        ]


# 全局单例
session_state = SessionStateManager()

"""
Memory ID 体系

提供统一的 ID 生成和解析功能
"""

import uuid
from datetime import datetime
from dataclasses import dataclass
from typing import Optional


@dataclass
class MemoryID:
    """
    Memory 统一 ID 体系
    
    格式：cid:mid:sid:rid
    
    示例:
        session_20260408_001:msg_abc123:sum_def456:resp_xyz789
    """
    cid: str  # Conversation ID - 会话 ID
    mid: str  # Message ID - 消息 ID
    sid: Optional[str] = None  # Summary ID - 摘要 ID
    rid: Optional[str] = None  # Response ID - 工具响应 ID
    
    @classmethod
    def new_message(cls, cid: str) -> "MemoryID":
        """生成新消息 ID"""
        return cls(
            cid=cid,
            mid=f"msg_{uuid.uuid4().hex[:12]}",
            sid=None,
            rid=None
        )
    
    @classmethod
    def new_summary(cls, cid: str, mid: str) -> "MemoryID":
        """生成新摘要 ID"""
        return cls(
            cid=cid,
            mid=mid,
            sid=f"sum_{uuid.uuid4().hex[:12]}",
            rid=None
        )
    
    @classmethod
    def new_response(cls, cid: str, tool_name: str) -> "MemoryID":
        """生成新工具响应 ID"""
        return cls(
            cid=cid,
            mid=f"tool_{tool_name}_{uuid.uuid4().hex[:8]}",
            sid=None,
            rid=f"resp_{uuid.uuid4().hex[:12]}"
        )
    
    def __str__(self) -> str:
        """格式化为字符串"""
        parts = [self.cid, self.mid]
        if self.sid:
            parts.append(self.sid)
        if self.rid:
            parts.append(self.rid)
        return ":".join(parts)
    
    @classmethod
    def parse(cls, id_str: str) -> "MemoryID":
        """解析 ID 字符串"""
        parts = id_str.split(":")
        if len(parts) < 2:
            raise ValueError(f"Invalid ID format: {id_str}")
        
        return cls(
            cid=parts[0],
            mid=parts[1],
            sid=parts[2] if len(parts) > 2 else None,
            rid=parts[3] if len(parts) > 3 else None
        )
    
    def is_message(self) -> bool:
        """是否是消息 ID"""
        return self.mid is not None and self.sid is None and self.rid is None
    
    def is_summary(self) -> bool:
        """是否是摘要 ID"""
        return self.sid is not None
    
    def is_response(self) -> bool:
        """是否是工具响应 ID"""
        return self.rid is not None


def generate_cid() -> str:
    """生成会话 ID"""
    return f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"


def generate_mid() -> str:
    """生成消息 ID"""
    return f"msg_{uuid.uuid4().hex[:12]}"


def generate_sid() -> str:
    """生成摘要 ID"""
    return f"sum_{uuid.uuid4().hex[:12]}"


def generate_rid() -> str:
    """生成工具响应 ID"""
    return f"resp_{uuid.uuid4().hex[:12]}"

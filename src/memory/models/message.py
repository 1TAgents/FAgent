"""
原始消息模型

完整存储所有消息，永不修改
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict
from enum import Enum
import hashlib


class Role(str, Enum):
    """消息角色"""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"


class MessageStatus(str, Enum):
    """消息状态"""
    RAW = "raw"  # 原始未处理
    EXTRACTED = "extracted"  # 已提取记忆
    SUMMARIZED = "summarized"  # 已生成摘要
    ARCHIVED = "archived"  # 已归档


@dataclass
class RawMessage:
    """
    原始消息 - 完整存储，永不修改
    
    所有用户消息、助手回复、工具响应都必须完整保存
    """
    
    # === 标识 ===
    cid: str  # 会话 ID
    mid: str  # 消息 ID

    # === 内容 ===
    role: Role  # 消息角色
    content: str  # 原始内容（完整，不截断）

    # === 可选字段 ===
    parent_mid: Optional[str] = None  # 父消息 ID（回复链）
    content_hash: str = ""  # 内容哈希（用于去重）
    
    # === 元数据 ===
    timestamp: str = ""  # ISO 时间戳
    sequence_num: int = 0  # 会话内序号
    
    # === 工具相关 ===
    tool_name: Optional[str] = None  # 工具名称（如果是工具调用/响应）
    tool_call_id: Optional[str] = None  # 工具调用 ID
    tool_response_size: Optional[int] = None  # 工具响应大小（字节）
    
    # === 附件 ===
    attachments: List[Dict] = field(default_factory=list)  # 文件、图片等
    metadata: Dict = field(default_factory=dict)  # 额外元数据
    
    # === 状态 ===
    status: MessageStatus = MessageStatus.RAW
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def __post_init__(self):
        """初始化后处理"""
        if not self.content_hash:
            self.content_hash = self._compute_hash()
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()
    
    def _compute_hash(self) -> str:
        """计算内容哈希"""
        return hashlib.sha256(self.content.encode()).hexdigest()[:16]
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "cid": self.cid,
            "mid": self.mid,
            "parent_mid": self.parent_mid,
            "role": self.role.value,
            "content": self.content,
            "content_hash": self.content_hash,
            "timestamp": self.timestamp,
            "sequence_num": self.sequence_num,
            "tool_name": self.tool_name,
            "tool_call_id": self.tool_call_id,
            "tool_response_size": self.tool_response_size,
            "attachments": self.attachments,
            "metadata": self.metadata,
            "status": self.status.value,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "RawMessage":
        """从字典创建"""
        return cls(
            cid=data["cid"],
            mid=data["mid"],
            parent_mid=data.get("parent_mid"),
            role=Role(data["role"]),
            content=data["content"],
            content_hash=data.get("content_hash", ""),
            timestamp=data.get("timestamp", ""),
            sequence_num=data.get("sequence_num", 0),
            tool_name=data.get("tool_name"),
            tool_call_id=data.get("tool_call_id"),
            tool_response_size=data.get("tool_response_size"),
            attachments=data.get("attachments", []),
            metadata=data.get("metadata", {}),
            status=MessageStatus(data.get("status", "raw")),
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
        )

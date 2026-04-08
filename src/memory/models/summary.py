"""
消息摘要模型

摘要是索引，不是替代 - 必须能追溯到原始数据
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict


@dataclass
class MessageSummary:
    """
    消息摘要 - 指向原始数据
    
    摘要用于快速浏览和上下文构建，但必须能追溯到原始消息
    """
    
    # === 标识 ===
    sid: str  # 摘要 ID
    cid: str  # 所属会话
    summary_type: str  # single | window | hierarchical
    
    # === 覆盖范围（关键：链接原始消息）===
    covered_mids: List[str] = field(default_factory=list)  # 覆盖的原始消息 ID 列表
    start_mid: str = ""  # 起始消息 ID
    end_mid: str = ""  # 结束消息 ID
    message_count: int = 0  # 覆盖的消息数量
    
    # === 摘要内容 ===
    summary: str = ""  # 摘要文本
    key_points: List[str] = field(default_factory=list)  # 关键点列表
    entities: Dict = field(default_factory=dict)  # 提取的实体（股票、数字等）
    topics: List[str] = field(default_factory=list)  # 话题标签
    
    # === 链接 ===
    parent_summary_id: Optional[str] = None  # 父摘要（层级摘要）
    child_summary_ids: List[str] = field(default_factory=list)  # 子摘要
    
    # === 导航 ===
    can_expand: bool = True  # 是否可以展开查看原始消息
    expansion_hint: str = ""  # 如何展开（查询提示）
    
    # === 元数据 ===
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    created_by: str = "auto"  # auto | user | manual
    
    def __post_init__(self):
        """初始化后处理"""
        if not self.expansion_hint:
            self.expansion_hint = f"查询 cid={self.cid}, mids={self.covered_mids[:3]}..."
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "sid": self.sid,
            "cid": self.cid,
            "summary_type": self.summary_type,
            "covered_mids": self.covered_mids,
            "start_mid": self.start_mid,
            "end_mid": self.end_mid,
            "message_count": self.message_count,
            "summary": self.summary,
            "key_points": self.key_points,
            "entities": self.entities,
            "topics": self.topics,
            "parent_summary_id": self.parent_summary_id,
            "child_summary_ids": self.child_summary_ids,
            "can_expand": self.can_expand,
            "expansion_hint": self.expansion_hint,
            "created_at": self.created_at,
            "created_by": self.created_by,
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "MessageSummary":
        """从字典创建"""
        return cls(
            sid=data["sid"],
            cid=data["cid"],
            summary_type=data["summary_type"],
            covered_mids=data.get("covered_mids", []),
            start_mid=data.get("start_mid", ""),
            end_mid=data.get("end_mid", ""),
            message_count=data.get("message_count", 0),
            summary=data.get("summary", ""),
            key_points=data.get("key_points", []),
            entities=data.get("entities", {}),
            topics=data.get("topics", []),
            parent_summary_id=data.get("parent_summary_id"),
            child_summary_ids=data.get("child_summary_ids", []),
            can_expand=data.get("can_expand", True),
            expansion_hint=data.get("expansion_hint", ""),
            created_at=data.get("created_at", ""),
            created_by=data.get("created_by", "auto"),
        )
    
    def to_navigation_info(self) -> Dict:
        """返回导航信息（用于 UI 展示）"""
        return {
            "sid": self.sid,
            "cid": self.cid,
            "type": self.summary_type,
            "message_count": self.message_count,
            "start_mid": self.start_mid,
            "end_mid": self.end_mid,
            "can_expand": self.can_expand,
            "expansion_hint": self.expansion_hint,
        }

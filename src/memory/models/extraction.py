"""
记忆提取记录模型

记录从消息中提取的记忆信息
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict


@dataclass
class MemoryExtraction:
    """
    从消息中提取的记忆
    
    记录意图、实体、偏好等提取信息
    """
    
    extraction_id: str  # 提取记录 ID
    cid: str  # 会话 ID
    mid: str  # 消息 ID
    
    # === 提取内容 ===
    intent_type: str  # query | analysis | trade | review | preference | knowledge
    confidence: float  # 置信度 0-1
    extracted_data: Dict = field(default_factory=dict)  # 提取的结构化数据
    
    # === 保存位置标记 ===
    saved_to_immediate: bool = False  # 是否保存到 L1
    saved_to_working: bool = False  # 是否保存到 L2
    saved_to_longterm: bool = False  # 是否保存到 L3
    
    # === 元数据 ===
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "extraction_id": self.extraction_id,
            "cid": self.cid,
            "mid": self.mid,
            "intent_type": self.intent_type,
            "confidence": self.confidence,
            "extracted_data": self.extracted_data,
            "saved_to_immediate": self.saved_to_immediate,
            "saved_to_working": self.saved_to_working,
            "saved_to_longterm": self.saved_to_longterm,
            "created_at": self.created_at,
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "MemoryExtraction":
        """从字典创建"""
        return cls(
            extraction_id=data["extraction_id"],
            cid=data["cid"],
            mid=data["mid"],
            intent_type=data["intent_type"],
            confidence=data["confidence"],
            extracted_data=data.get("extracted_data", {}),
            saved_to_immediate=data.get("saved_to_immediate", False),
            saved_to_working=data.get("saved_to_working", False),
            saved_to_longterm=data.get("saved_to_longterm", False),
            created_at=data.get("created_at", ""),
        )

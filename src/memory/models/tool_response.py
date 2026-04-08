"""
工具响应模型

分级存储：小响应内联，中/大响应存文件
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict
from enum import Enum
from pathlib import Path


class ResponseStorage(str, Enum):
    """响应存储类型"""
    INLINE = "inline"  # 内联存储（<500 字）
    FILE = "file"  # 文件存储（500-2000 字）
    INDEXED = "indexed"  # 索引存储（>2000 字）


@dataclass
class ToolResponse:
    """
    工具响应 - 分级存储
    
    根据响应大小选择不同存储策略
    """
    
    # === 标识 ===
    rid: str  # 响应 ID
    cid: str  # 会话 ID
    mid: str  # 关联的消息 ID
    tool_call_id: str  # 工具调用 ID
    
    # === 工具信息 ===
    tool_name: str  # 工具名称
    tool_input: str  # 工具输入参数
    
    # === 响应内容 ===
    response_size: int  # 原始响应大小（字节）
    storage_type: ResponseStorage  # 存储类型
    
    # === 存储位置 ===
    inline_content: Optional[str] = None  # 内联内容（小响应）
    file_path: Optional[str] = None  # 文件路径（中/大响应）
    index_data: Optional[Dict] = None  # 索引数据（大响应）
    
    # === 摘要（必有）===
    summary: str = ""  # 响应摘要（用于快速浏览）
    key_data: Dict = field(default_factory=dict)  # 关键数据（结构化提取）
    
    # === 导航 ===
    can_load_full: bool = True  # 是否可以加载完整内容
    load_hint: str = ""  # 如何加载
    
    # === 元数据 ===
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    execution_time_ms: Optional[int] = None  # 工具执行时间
    
    def __post_init__(self):
        """初始化后处理"""
        if not self.load_hint:
            if self.storage_type == ResponseStorage.INLINE:
                self.load_hint = "完整内容已存储在数据库"
            elif self.storage_type == ResponseStorage.FILE:
                self.load_hint = f"完整内容已保存到 {self.file_path}"
            else:
                self.load_hint = f"使用索引查询完整内容：{self.index_data}"
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "rid": self.rid,
            "cid": self.cid,
            "mid": self.mid,
            "tool_call_id": self.tool_call_id,
            "tool_name": self.tool_name,
            "tool_input": self.tool_input,
            "response_size": self.response_size,
            "storage_type": self.storage_type.value,
            "inline_content": self.inline_content,
            "file_path": self.file_path,
            "index_data": self.index_data,
            "summary": self.summary,
            "key_data": self.key_data,
            "can_load_full": self.can_load_full,
            "load_hint": self.load_hint,
            "created_at": self.created_at,
            "execution_time_ms": self.execution_time_ms,
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "ToolResponse":
        """从字典创建"""
        return cls(
            rid=data["rid"],
            cid=data["cid"],
            mid=data["mid"],
            tool_call_id=data["tool_call_id"],
            tool_name=data["tool_name"],
            tool_input=data["tool_input"],
            response_size=data["response_size"],
            storage_type=ResponseStorage(data["storage_type"]),
            inline_content=data.get("inline_content"),
            file_path=data.get("file_path"),
            index_data=data.get("index_data"),
            summary=data.get("summary", ""),
            key_data=data.get("key_data", {}),
            can_load_full=data.get("can_load_full", True),
            load_hint=data.get("load_hint", ""),
            created_at=data.get("created_at", ""),
            execution_time_ms=data.get("execution_time_ms"),
        )
    
    def get_full_content(self) -> Optional[str]:
        """获取完整内容（懒加载）"""
        if self.storage_type == ResponseStorage.INLINE:
            return self.inline_content
        elif self.storage_type in [ResponseStorage.FILE, ResponseStorage.INDEXED]:
            if self.file_path and Path(self.file_path).exists():
                with open(self.file_path, 'r', encoding='utf-8') as f:
                    return f.read()
        return None
    
    def to_navigation_info(self) -> Dict:
        """返回导航信息"""
        return {
            "rid": self.rid,
            "cid": self.cid,
            "mid": self.mid,
            "tool_name": self.tool_name,
            "response_size": self.response_size,
            "storage_type": self.storage_type.value,
            "summary": self.summary[:100] + "..." if len(self.summary) > 100 else self.summary,
            "can_load_full": self.can_load_full,
            "load_hint": self.load_hint,
        }

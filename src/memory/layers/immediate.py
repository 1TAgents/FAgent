"""
L1 瞬时记忆

会话级记忆，内存存储，会话结束清空
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Any


@dataclass
class ImmediateMemory:
    """
    L1 瞬时记忆 - 会话级，内存存储
    
    存储:
    - 当前对话轮次
    - 实时行情数据快照
    - 工具调用响应
    - 临时计算结果
    """
    
    # 当前对话上下文
    current_turn: str = ""
    conversation_history: List[Dict] = field(default_factory=list)
    
    # 实时数据快照
    market_snapshot: Dict[str, Any] = field(default_factory=dict)
    portfolio_snapshot: Dict[str, Any] = field(default_factory=dict)
    
    # 工具调用上下文
    tool_calls: List[Dict] = field(default_factory=list)
    tool_responses: List[Dict] = field(default_factory=list)
    
    # 临时计算缓存
    temp_cache: Dict[str, Any] = field(default_factory=dict)
    
    # 生命周期管理
    session_id: str = field(default_factory=lambda: datetime.now().isoformat())
    created_at: datetime = field(default_factory=datetime.now)
    
    def clear(self):
        """清空瞬时记忆"""
        self.__init__()
    
    def add_turn(self, role: str, content: str):
        """添加对话轮次"""
        self.conversation_history.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        })
        self.current_turn = content
    
    def set_market_snapshot(self, symbols: List[str], data: Dict):
        """设置行情快照"""
        self.market_snapshot = {
            "symbols": symbols,
            "data": data,
            "fetched_at": datetime.now().isoformat()
        }
    
    def add_tool_call(self, tool_name: str, input_data: Dict):
        """添加工具调用"""
        self.tool_calls.append({
            "tool_name": tool_name,
            "input": input_data,
            "timestamp": datetime.now().isoformat()
        })
    
    def add_tool_response(self, tool_name: str, response: Dict):
        """添加工具响应"""
        self.tool_responses.append({
            "tool_name": tool_name,
            "response": response,
            "timestamp": datetime.now().isoformat()
        })
    
    def get_recent_turns(self, limit: int = 10) -> List[Dict]:
        """获取最近对话轮次"""
        return self.conversation_history[-limit:]
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "session_id": self.session_id,
            "current_turn": self.current_turn,
            "conversation_length": len(self.conversation_history),
            "market_symbols": list(self.market_snapshot.get("symbols", [])),
            "tool_calls_count": len(self.tool_calls),
            "tool_responses_count": len(self.tool_responses),
            "cache_keys": list(self.temp_cache.keys()),
            "created_at": self.created_at.isoformat()
        }

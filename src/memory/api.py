"""
Memory API - 逐渐披露 API

提供 L1-L5 级别的记忆查询接口
"""

from typing import Optional, List, Dict
from .manager import MemoryManager


class MemoryAPI:
    """
    Memory API - 逐渐披露接口
    
    Level 1: 会话概览
    Level 2: 消息列表
    Level 3: 消息详情
    Level 4: 工具响应
    Level 5: 摘要展开
    """
    
    def __init__(self, memory_manager: MemoryManager):
        self.memory = memory_manager
    
    # ==================== Level 1: 会话概览 ====================
    
    def get_conversation_overview(self, cid: str) -> Dict:
        """
        Level 1: 获取会话概览（只看摘要列表）
        
        Returns:
            {
                "cid": str,
                "type": "overview",
                "summaries": [summary_info, ...],
                "has_raw_messages": bool,
                "expand_hint": str
            }
        """
        summaries = self.memory.get_summaries(cid)
        
        return {
            "cid": cid,
            "type": "overview",
            "summaries": [s.to_navigation_info() for s in summaries],
            "has_raw_messages": True,
            "expand_hint": f"使用 memory.messages 查看消息列表"
        }
    
    # ==================== Level 2: 消息列表 ====================
    
    def get_conversation_messages(
        self,
        cid: str,
        start: int = 0,
        limit: int = 50
    ) -> Dict:
        """
        Level 2: 获取消息列表（分页，带摘要标记）
        
        Returns:
            {
                "cid": str,
                "type": "messages",
                "messages": [message_info, ...],
                "pagination": {"start": int, "limit": int, "has_more": bool}
            }
        """
        messages = self.memory.get_messages(cid, start, limit)
        
        # 获取所有摘要，标记哪些消息有摘要
        summaries = self.memory.get_summaries(cid)
        summarized_mids = set()
        for s in summaries:
            summarized_mids.update(s.covered_mids)
        
        return {
            "cid": cid,
            "type": "messages",
            "messages": [{
                "mid": m.mid,
                "role": m.role.value,
                "content_preview": m.content[:200] + "..." if len(m.content) > 200 else m.content,
                "timestamp": m.timestamp,
                "has_summary": m.mid in summarized_mids,
                "is_tool_response": m.tool_name is not None,
                "expand_hint": f"使用 memory.detail {m.mid} 查看详情"
            } for m in messages],
            "pagination": {
                "start": start,
                "limit": limit,
                "has_more": len(messages) == limit
            }
        }
    
    # ==================== Level 3: 消息详情 ====================
    
    def get_message_detail(self, cid: str, mid: str) -> Dict:
        """
        Level 3: 获取单条消息完整详情
        
        Returns:
            {
                "cid": str,
                "mid": str,
                "type": "message_detail",
                "message": {full_message},
                "related_summaries": [summary_info, ...],
                "can_expand": bool,
                "navigate_up_hint": str
            }
        """
        message = self.memory.get_message(cid, mid)
        if not message:
            return {"error": f"Message not found: {cid}:{mid}"}
        
        # 查找关联的摘要
        summaries = self.memory.get_summaries(cid)
        related_summaries = [
            s.to_navigation_info() for s in summaries
            if mid in s.covered_mids
        ]
        
        return {
            "cid": cid,
            "mid": mid,
            "type": "message_detail",
            "message": {
                "role": message.role.value,
                "content": message.content,  # 完整内容
                "timestamp": message.timestamp,
                "sequence_num": message.sequence_num,
                "attachments": message.attachments,
                "metadata": message.metadata
            },
            "related_summaries": related_summaries,
            "can_expand": False,
            "navigate_up_hint": "使用 memory.messages 返回列表"
        }
    
    # ==================== Level 4: 工具响应 ====================
    
    def get_tool_response_detail(self, rid: str) -> Dict:
        """
        Level 4: 获取工具响应详情（支持懒加载完整内容）
        
        Returns:
            {
                "rid": str,
                "cid": str,
                "mid": str,
                "type": "tool_response_detail",
                "tool_name": str,
                "tool_input": str,
                "summary": str,
                "key_data": dict,
                "response_size": int,
                "storage_type": str,
                "full_content": str (懒加载),
                "navigate_up_hint": str
            }
        """
        response = self.memory.get_tool_response(rid)
        if not response:
            return {"error": f"Response not found: {rid}"}
        
        # 懒加载完整内容
        full_content = response.get_full_content()
        
        return {
            "rid": rid,
            "cid": response.cid,
            "mid": response.mid,
            "type": "tool_response_detail",
            "tool_name": response.tool_name,
            "tool_input": response.tool_input,
            "summary": response.summary,
            "key_data": response.key_data,
            "response_size": response.response_size,
            "storage_type": response.storage_type.value,
            "full_content": full_content,
            "navigate_up_hint": f"使用 message.detail {response.mid} 查看关联消息"
        }
    
    # ==================== Level 5: 摘要展开 ====================
    
    def expand_summary(self, sid: str) -> Dict:
        """
        Level 5: 展开摘要，查看覆盖的原始消息
        
        Returns:
            {
                "sid": str,
                "cid": str,
                "type": "summary_expanded",
                "summary": {summary_info},
                "covered_messages": [full_message, ...],
                "message_count": int,
                "navigate_up_hint": str
            }
        """
        summary = self.memory.get_summary(sid)
        if not summary:
            return {"error": f"Summary not found: {sid}"}
        
        # 获取覆盖的所有原始消息
        messages = []
        for mid in summary.covered_mids:
            msg = self.memory.get_message(summary.cid, mid)
            if msg:
                messages.append({
                    "mid": msg.mid,
                    "role": msg.role.value,
                    "content": msg.content,
                    "timestamp": msg.timestamp
                })
        
        return {
            "sid": sid,
            "cid": summary.cid,
            "type": "summary_expanded",
            "summary": {
                "summary": summary.summary,
                "key_points": summary.key_points,
                "topics": summary.topics
            },
            "covered_messages": messages,
            "message_count": len(messages),
            "navigate_up_hint": "使用 memory.overview 返回概览"
        }
    
    # ==================== 搜索 ====================
    
    def search_messages(
        self,
        cid: str,
        query: str,
        limit: int = 20
    ) -> Dict:
        """
        搜索消息（在完整内容中搜索）
        
        Returns:
            {
                "cid": str,
                "query": str,
                "results": [match_info, ...],
                "total_found": int
            }
        """
        # 获取消息（简单实现：获取所有后关键词匹配）
        messages = self.memory.get_messages(cid, 0, 1000)
        
        results = []
        for msg in messages:
            if query.lower() in msg.content.lower():
                # 高亮匹配
                idx = msg.content.lower().find(query.lower())
                start = max(0, idx - 50)
                end = min(len(msg.content), idx + len(query) + 50)
                content_snippet = "..." + msg.content[start:end] + "..."
                
                results.append({
                    "mid": msg.mid,
                    "role": msg.role.value,
                    "content": content_snippet,
                    "timestamp": msg.timestamp,
                    "expand_hint": f"使用 memory.detail {msg.mid}"
                })
                
                if len(results) >= limit:
                    break
        
        return {
            "cid": cid,
            "query": query,
            "results": results,
            "total_found": len(results)
        }

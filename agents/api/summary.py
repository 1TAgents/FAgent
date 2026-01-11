"""
Agents Summary API - 会话总结接口

提供会话标题自动生成服务
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any

from ..services.summary import summary_service

router = APIRouter(prefix="/agent/summary", tags=["agent-summary"])


# ==================== 请求/响应模型 ====================

class Message(BaseModel):
    """消息模型"""
    role: str  # user, assistant
    content: str


class GenerateSummaryRequest(BaseModel):
    """生成总结请求"""
    messages: List[Message]
    max_messages: int = 6  # 最多使用的消息数量


class GenerateSummaryResponse(BaseModel):
    """生成总结响应"""
    title: str


# ==================== 接口 ====================

@router.post("/generate", response_model=GenerateSummaryResponse)
async def generate_summary(request: GenerateSummaryRequest):
    """
    根据对话内容生成简短标题
    
    用于：
    - 新会话完成首轮对话后，自动生成标题
    - 替换默认的 "Conversation ID"
    
    Args:
        messages: 对话消息列表
        max_messages: 最多使用的消息数量（默认 6 条）
        
    Returns:
        title: 生成的标题（5-15 字）
    """
    try:
        messages = [{"role": msg.role, "content": msg.content} for msg in request.messages]
        
        title = summary_service.generate_summary(
            messages=messages,
            max_messages=request.max_messages
        )
        
        return GenerateSummaryResponse(title=title)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

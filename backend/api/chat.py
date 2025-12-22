"""
Chat API - 对话接口（流式和非流式）
支持多轮对话和会话管理

支持多种消息类型（与 OpenAI API 一致）：
- text: 纯文本
- image_url: 图片 URL
- video_url: 视频 URL
- multimodal: 多模态（混合内容）
"""
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Union, Any
import json
from loguru import logger

from ..services.llm import llm_service
from ..services.session import session_manager
from ..services.storage import ContentType

router = APIRouter(prefix="/api/chat", tags=["chat"])


class Message(BaseModel):
    """
    消息模型（与 OpenAI API 格式兼容）
    
    content 支持以下格式：
    1. 纯文本: "Hello"
    2. 多模态列表: [{"type": "text", "text": "..."}, {"type": "image_url", "image_url": {"url": "..."}}]
    """
    role: str  # "user", "assistant", "system"
    content: Union[str, List[Dict[str, Any]]]  # 支持字符串或多模态列表
    content_type: Optional[str] = None  # 可选：内容类型，不提供则自动检测
    metadata: Optional[Dict[str, Any]] = None  # 可选：消息元数据


class ChatRequest(BaseModel):
    """聊天请求模型"""
    messages: Optional[List[Message]] = None  # 可选：直接提供消息列表
    session_id: Optional[str] = None  # 可选：会话ID（用于多轮对话）
    user_message: Optional[Union[str, List[Dict[str, Any]]]] = None  # 可选：用户消息（配合 session_id 使用）
    user_message_metadata: Optional[Dict[str, Any]] = None  # 可选：用户消息的元数据
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = None
    reasoning: Optional[bool] = False


class ChatRequestWithSession(BaseModel):
    """带会话的聊天请求模型（简化版）"""
    session_id: str
    user_message: Union[str, List[Dict[str, Any]]]
    user_message_metadata: Optional[Dict[str, Any]] = None
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = None
    reasoning: Optional[bool] = False


class ChatResponse(BaseModel):
    """聊天响应模型"""
    content: str
    model: str
    message_id: Optional[str] = None  # 返回消息ID
    usage: Optional[dict] = None


def _prepare_messages(request: ChatRequest) -> List[Dict]:
    """
    准备消息列表
    支持两种方式：
    1. 直接提供 messages 列表
    2. 使用 session_id + user_message（自动附加历史）
    """
    if request.messages:
        # 方式1: 直接提供消息列表
        return [{"role": msg.role, "content": msg.content} for msg in request.messages]
    elif request.session_id and request.user_message:
        # 方式2: 使用会话ID，自动附加历史
        session = session_manager.get_session(request.session_id)
        if session is None:
            raise HTTPException(status_code=404, detail=f"Session {request.session_id} not found")
        
        # 获取历史消息（格式化为 LLM 调用格式）
        messages = session_manager.get_messages_for_llm(request.session_id)
        # 添加当前用户消息
        messages.append({"role": "user", "content": request.user_message})
        return messages
    else:
        raise HTTPException(
            status_code=400,
            detail="Either 'messages' or both 'session_id' and 'user_message' must be provided"
        )


@router.post("/completion", response_model=ChatResponse)
async def chat_completion(request: ChatRequest):
    """
    非流式聊天接口
    
    支持两种调用方式：
    1. 直接提供消息列表（messages）
    2. 使用会话ID + 用户消息（session_id + user_message），自动附加对话历史
    
    返回完整的聊天回复
    """
    logger.info(f"API: /completion 请求 | session_id={request.session_id}")
    try:
        # 准备消息列表
        messages = _prepare_messages(request)
        logger.debug(f"API: 准备消息完成 | messages_count={len(messages)}")
        
        # 调用 LLM 服务
        kwargs = {}
        if request.reasoning:
            kwargs["reasoning"] = {"enabled": True}
        
        response = llm_service.chat_completion(
            messages=messages,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            **kwargs
        )
        
        # 提取回复内容
        content = response.choices[0].message.content
        
        # 如果使用会话，保存消息到会话历史
        assistant_message_id = None
        if request.session_id:
            # 保存用户消息（带 metadata）
            session_manager.add_message(
                request.session_id, 
                "user", 
                request.user_message,
                metadata=request.user_message_metadata
            )
            # 保存助手回复
            assistant_message_id = session_manager.add_message(
                request.session_id, 
                "assistant", 
                content
            )
        
        usage = None
        if response.usage:
            usage = {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
            }
        
        return ChatResponse(
            content=content,
            model=response.model,
            message_id=assistant_message_id,
            usage=usage
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"API: /completion 错误 | error={str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stream")
async def chat_stream(request: ChatRequest):
    """
    流式聊天接口（SSE）
    
    使用 Server-Sent Events 实时推送 AI 回复
    
    支持两种调用方式：
    1. 直接提供消息列表（messages）
    2. 使用会话ID + 用户消息（session_id + user_message），自动附加对话历史
    """
    logger.info(f"API: /stream 请求 | session_id={request.session_id}")
    try:
        # 准备消息列表
        messages = _prepare_messages(request)
        
        # 准备流式生成器
        kwargs = {}
        if request.reasoning:
            kwargs["reasoning"] = {"enabled": True}
        
        # 记录完整回复（用于保存到会话）
        full_content = ""
        
        def generate():
            """SSE 事件生成器"""
            nonlocal full_content
            try:
                for chunk in llm_service.chat_completion_stream(
                    messages=messages,
                    temperature=request.temperature,
                    max_tokens=request.max_tokens,
                    **kwargs
                ):
                    # 累积完整内容
                    full_content += chunk
                    # SSE 格式：data: {content}\n\n
                    data = json.dumps({"content": chunk}, ensure_ascii=False)
                    yield f"data: {data}\n\n"
                
                # 如果使用会话，保存消息到会话历史
                if request.session_id:
                    # 保存用户消息（带 metadata）
                    session_manager.add_message(
                        request.session_id, 
                        "user", 
                        request.user_message,
                        metadata=request.user_message_metadata
                    )
                    # 保存助手回复
                    assistant_message_id = session_manager.add_message(
                        request.session_id, 
                        "assistant", 
                        full_content
                    )
                    # 发送包含 message_id 的结束标记
                    done_data = json.dumps({"done": True, "message_id": assistant_message_id}, ensure_ascii=False)
                    yield f"data: {done_data}\n\n"
                
                # 发送结束标记
                yield "data: [DONE]\n\n"
            except Exception as e:
                # 发送错误信息
                error_data = json.dumps({"error": str(e)}, ensure_ascii=False)
                yield f"data: {error_data}\n\n"
        
        return StreamingResponse(
            generate(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",  # 禁用 Nginx 缓冲
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ========== 会话管理接口 ==========

@router.post("/session/create")
async def create_session(system_message: Optional[str] = None, metadata: Optional[Dict] = None):
    """
    创建新会话
    
    返回 conversation_id（会话ID）
    """
    conversation_id = session_manager.create_session(
        system_message=system_message,
        metadata=metadata
    )
    return {
        "conversation_id": conversation_id,
        "session_id": conversation_id,  # 向后兼容
        "message": "Session created successfully"
    }


@router.get("/conversation/{conversation_id}")
async def get_conversation(conversation_id: str):
    """
    根据 conversation_id 获取完整会话记录（包含所有消息）
    
    这是主要的查询接口，返回：
    - conversation_id: 会话ID
    - messages: 消息列表（每个消息包含 message_id）
    - message_count: 消息数量
    - created_at, updated_at: 时间戳
    """
    conversation = session_manager.get_conversation_with_messages(conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail=f"Conversation {conversation_id} not found")
    return conversation


@router.get("/session/{session_id}/messages")
async def get_session_messages(session_id: str):
    """
    获取会话的所有消息（向后兼容接口）
    
    使用 session_id（实际映射到 conversation_id）
    """
    messages = session_manager.get_messages(session_id)
    if not messages:
        # 检查会话是否存在
        session = session_manager.get_session(session_id)
        if session is None:
            raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
    
    return {
        "conversation_id": session_id,
        "session_id": session_id,  # 向后兼容
        "messages": messages,
        "count": len(messages)
    }


@router.delete("/session/{session_id}")
async def delete_session(session_id: str):
    """
    删除会话及其所有消息
    
    使用 session_id（实际映射到 conversation_id）
    """
    success = session_manager.delete_session(session_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
    return {"message": "Session deleted successfully"}


@router.delete("/conversation/{conversation_id}")
async def delete_conversation(conversation_id: str):
    """
    删除会话及其所有消息（使用 conversation_id）
    """
    success = session_manager.delete_session(conversation_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"Conversation {conversation_id} not found")
    return {"message": "Conversation deleted successfully"}


@router.post("/session/{session_id}/clear")
async def clear_session(session_id: str):
    """
    清空会话消息（保留会话）
    
    使用 session_id（实际映射到 conversation_id）
    """
    success = session_manager.clear_session(session_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
    return {"message": "Session cleared successfully"}


@router.get("/sessions")
async def list_sessions(limit: Optional[int] = None, offset: int = 0):
    """
    列出所有会话
    
    Query Parameters:
        limit: 可选的数量限制
        offset: 偏移量
    """
    sessions = session_manager.list_sessions(limit=limit, offset=offset)
    return {
        "sessions": sessions,
        "count": len(sessions)
    }


@router.get("/conversations")
async def list_conversations(limit: Optional[int] = None, offset: int = 0):
    """
    列出所有会话（使用 conversation_id）
    
    Query Parameters:
        limit: 可选的数量限制
        offset: 偏移量
    """
    conversations = session_manager.list_sessions(limit=limit, offset=offset)
    return {
        "conversations": conversations,
        "count": len(conversations)
    }


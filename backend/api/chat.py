"""
Chat API - 后端业务接口

后端职责：
1. 接收前端请求
2. 存储用户消息
3. 调用 Agents 服务（HTTP）
4. 存储 AI 回复
5. 返回给前端

ID 设计：
- cid: 整数，会话ID
- message_id: 整数，消息ID
"""
import os
import httpx
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import json

from ..core.context import set_context, ctx_logger as logger
from ..services.session import session_manager
from ..services.storage import message_storage

router = APIRouter(prefix="/api/chat", tags=["chat"])

# Agents 服务地址
AGENTS_BASE_URL = os.getenv("AGENTS_BASE_URL", "http://localhost:8001")


# ==================== 请求/响应模型 ====================

class ChatSendRequest(BaseModel):
    """聊天请求模型"""
    cid: int  # 会话ID
    user_message: str  # 用户消息
    user_message_metadata: Optional[Dict[str, Any]] = None
    
    # LLM 参数
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = None
    history_limit: Optional[int] = None


class ChatSendResponse(BaseModel):
    """聊天响应模型"""
    content: str
    cid: int
    user_message_id: int
    assistant_message_id: int


class CreateSessionRequest(BaseModel):
    """创建会话请求"""
    metadata: Optional[Dict[str, Any]] = None


class CreateSessionResponse(BaseModel):
    """创建会话响应"""
    cid: int
    message: str = "Session created successfully"


# ==================== 核心业务接口 ====================

@router.post("/send", response_model=ChatSendResponse)
async def chat_send(request: ChatSendRequest):
    """
    发送消息接口（非流式）
    
    流程：
    1. 后端：存储用户消息
    2. 后端：构建 messages，调用 Agents 服务
    3. 后端：存储 AI 回复
    4. 返回给前端
    """
    set_context(cid=str(request.cid))
    logger.info("/send 请求")
    
    try:
        # 1. 存储用户消息
        user_message_id = session_manager.add_message(
            cid=request.cid,
            role="user",
            content=request.user_message,
            metadata=request.user_message_metadata
        )
        logger.debug(f"用户消息已落库 | user_message_id={user_message_id}")
        
        # 2. 构建 messages 列表
        history = message_storage.get_history_before_message(
            cid=request.cid,
            before_message_id=user_message_id,
            limit=request.history_limit
        )
        messages = [{"role": msg["role"], "content": msg["content"]} for msg in history]
        messages.append({"role": "user", "content": request.user_message})
        
        # 3. 调用 Agents 服务
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{AGENTS_BASE_URL}/agent/chat/completion",
                json={
                    "messages": messages,
                    "temperature": request.temperature,
                    "max_tokens": request.max_tokens
                },
                timeout=60.0
            )
            response.raise_for_status()
            result = response.json()
        
        content = result["content"]
        
        # 4. 存储 AI 回复
        assistant_message_id = session_manager.add_message(
            cid=request.cid,
            role="assistant",
            content=content
        )
        logger.debug(f"AI 回复已落库 | assistant_message_id={assistant_message_id}")
        
        return ChatSendResponse(
            content=content,
            cid=request.cid,
            user_message_id=user_message_id,
            assistant_message_id=assistant_message_id
        )
    except httpx.HTTPError as e:
        logger.error(f"调用 Agents 服务失败 | error={str(e)}")
        raise HTTPException(status_code=502, detail=f"Agents service error: {str(e)}")
    except Exception as e:
        logger.error(f"/send 错误 | error={str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/send/stream")
async def chat_send_stream(request: ChatSendRequest):
    """
    发送消息接口（流式）
    
    流程：
    1. 后端：存储用户消息
    2. 后端：构建 messages，调用 Agents 服务（流式）
    3. 后端：接收流式结果，转发给前端
    4. 后端：存储 AI 回复
    """
    set_context(cid=str(request.cid))
    logger.info("/send/stream 请求")
    
    try:
        # 1. 存储用户消息
        user_message_id = session_manager.add_message(
            cid=request.cid,
            role="user",
            content=request.user_message,
            metadata=request.user_message_metadata
        )
        logger.debug(f"用户消息已落库 | user_message_id={user_message_id}")
        
        # 2. 构建 messages 列表
        history = message_storage.get_history_before_message(
            cid=request.cid,
            before_message_id=user_message_id,
            limit=request.history_limit
        )
        messages = [{"role": msg["role"], "content": msg["content"]} for msg in history]
        messages.append({"role": "user", "content": request.user_message})
        
        # 捕获参数
        cid = request.cid
        temperature = request.temperature
        max_tokens = request.max_tokens
        
        async def generate():
            """SSE 事件生成器"""
            full_content = ""
            assistant_message_id = None
            
            try:
                # 3. 调用 Agents 服务（流式）
                async with httpx.AsyncClient() as client:
                    async with client.stream(
                        "POST",
                        f"{AGENTS_BASE_URL}/agent/chat/stream",
                        json={
                            "messages": messages,
                            "temperature": temperature,
                            "max_tokens": max_tokens
                        },
                        timeout=60.0
                    ) as response:
                        async for line in response.aiter_lines():
                            if line.startswith("data: "):
                                data_str = line[6:]
                                if data_str == "[DONE]":
                                    break
                                try:
                                    data = json.loads(data_str)
                                    if "content" in data:
                                        full_content += data["content"]
                                        yield f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
                                    if "error" in data:
                                        yield f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
                                        return
                                except json.JSONDecodeError:
                                    pass
                
                # 4. 存储 AI 回复
                assistant_message_id = session_manager.add_message(
                    cid=cid,
                    role="assistant",
                    content=full_content
                )
                logger.debug(f"AI 回复已落库 | assistant_message_id={assistant_message_id}")
                
                # 发送完成信息
                done_data = json.dumps({
                    "done": True,
                    "cid": cid,
                    "user_message_id": user_message_id,
                    "assistant_message_id": assistant_message_id
                }, ensure_ascii=False)
                yield f"data: {done_data}\n\n"
                yield "data: [DONE]\n\n"
                
            except Exception as e:
                logger.error(f"/send/stream 生成错误 | error={str(e)}")
                error_data = json.dumps({"error": str(e)}, ensure_ascii=False)
                yield f"data: {error_data}\n\n"
        
        return StreamingResponse(
            generate(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            }
        )
    except Exception as e:
        logger.error(f"/send/stream 请求错误 | error={str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 会话管理接口 ====================

@router.post("/session/create", response_model=CreateSessionResponse)
async def create_session(request: CreateSessionRequest = None):
    """创建新会话"""
    if request is None:
        request = CreateSessionRequest()
    
    cid = session_manager.create_session(
        metadata=request.metadata
    )
    return CreateSessionResponse(cid=cid)


@router.get("/conversation/{cid}")
async def get_conversation(cid: int):
    """获取完整会话记录（包含所有消息）"""
    conversation = session_manager.get_conversation_with_messages(cid)
    if conversation is None:
        raise HTTPException(status_code=404, detail=f"Conversation {cid} not found")
    return conversation


@router.get("/conversation/{cid}/messages")
async def get_conversation_messages(cid: int, limit: Optional[int] = None):
    """获取会话的消息列表"""
    session = session_manager.get_session(cid)
    if session is None:
        raise HTTPException(status_code=404, detail=f"Conversation {cid} not found")
    
    messages = session_manager.get_messages(cid, limit=limit)
    return {
        "cid": cid,
        "messages": messages,
        "count": len(messages)
    }


@router.get("/conversation/{cid}/history")
async def get_conversation_history(
    cid: int,
    before_message_id: int,
    limit: Optional[int] = None
):
    """获取指定消息之前的历史消息"""
    messages = session_manager.get_history_before_message(cid, before_message_id, limit)
    return {
        "cid": cid,
        "before_message_id": before_message_id,
        "messages": messages,
        "count": len(messages)
    }


@router.delete("/conversation/{cid}")
async def delete_conversation(cid: int):
    """删除会话及其所有消息"""
    success = session_manager.delete_session(cid)
    if not success:
        raise HTTPException(status_code=404, detail=f"Conversation {cid} not found")
    return {"message": "Conversation deleted successfully", "cid": cid}


@router.post("/conversation/{cid}/clear")
async def clear_conversation(cid: int):
    """清空会话消息（保留会话）"""
    session = session_manager.get_session(cid)
    if session is None:
        raise HTTPException(status_code=404, detail=f"Conversation {cid} not found")
    
    session_manager.clear_session(cid)
    return {"message": "Conversation cleared successfully", "cid": cid}


@router.get("/conversations")
async def list_conversations(limit: Optional[int] = None, offset: int = 0):
    """列出所有会话"""
    conversations = session_manager.list_sessions(limit=limit, offset=offset)
    return {
        "conversations": conversations,
        "count": len(conversations)
    }

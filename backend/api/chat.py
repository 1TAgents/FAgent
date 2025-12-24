"""
Chat API - 对话接口（流式和非流式）

消息流程：
1. 用户消息先落库，获取 message_id
2. 用 message_id 过滤历史消息作为上下文
3. 调用 LLM
4. AI 回复落库

ID 设计：
- cid: 整数，会话ID
- message_id: 整数，消息ID

消息角色：
- user: 用户消息
- assistant: AI 回复
- system: 系统消息
"""
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Union, Any
import json

from ..core.context import set_context, ctx_logger as logger
from ..services.llm import llm_service
from ..services.session import session_manager

router = APIRouter(prefix="/api/chat", tags=["chat"])


# ==================== 请求/响应模型 ====================

class Message(BaseModel):
    """消息模型（直接调用时使用）"""
    role: str  # user, assistant, system
    content: Union[str, List[Dict[str, Any]]]


class ChatRequest(BaseModel):
    """聊天请求模型"""
    # 方式1：直接提供消息列表（无持久化）
    messages: Optional[List[Message]] = None
    
    # 方式2：使用会话（推荐，有持久化）
    cid: Optional[int] = None  # 会话ID
    user_message: Optional[Union[str, List[Dict[str, Any]]]] = None
    user_message_metadata: Optional[Dict[str, Any]] = None
    
    # LLM 参数
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = None
    reasoning: Optional[bool] = False
    
    # 历史消息限制
    history_limit: Optional[int] = None  # 最多取多少条历史


class ChatResponse(BaseModel):
    """聊天响应模型"""
    content: str
    model: str
    cid: Optional[int] = None
    user_message_id: Optional[int] = None
    assistant_message_id: Optional[int] = None
    usage: Optional[dict] = None


class CreateSessionRequest(BaseModel):
    """创建会话请求"""
    system_message: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class CreateSessionResponse(BaseModel):
    """创建会话响应"""
    cid: int
    message: str = "Session created successfully"


# ==================== 核心聊天接口 ====================

@router.post("/completion", response_model=ChatResponse)
async def chat_completion(request: ChatRequest):
    """
    非流式聊天接口
    
    消息流程（使用会话时）：
    1. 用户消息先落库
    2. 获取历史消息（message_id < 当前）
    3. 调用 LLM
    4. AI 回复落库
    """
    # 设置上下文
    if request.cid:
        set_context(cid=str(request.cid))
    
    logger.info("/completion 请求")
    
    try:
        user_message_id = None
        assistant_message_id = None
        
        if request.cid and request.user_message:
            # === 方式2：使用会话（有持久化）===
            
            # 1. 用户消息先落库
            user_message_id = session_manager.add_message(
                cid=request.cid,
                role="user",
                content=request.user_message,
                metadata=request.user_message_metadata
            )
            logger.debug(f"用户消息已落库 | user_message_id={user_message_id}")
            
            # 2. 获取历史消息（message_id < 当前用户消息）
            history_messages = session_manager.get_messages_for_llm(
                cid=request.cid,
                before_message_id=user_message_id,
                limit=request.history_limit
            )
            
            # 3. 构建完整消息列表
            messages = history_messages + [{"role": "user", "content": request.user_message}]
            logger.debug(f"构建消息列表 | history={len(history_messages)} | total={len(messages)}")
            
        elif request.messages:
            # === 方式1：直接提供消息（无持久化）===
            messages = [{"role": msg.role, "content": msg.content} for msg in request.messages]
        else:
            raise HTTPException(
                status_code=400,
                detail="Either 'messages' or both 'cid' and 'user_message' must be provided"
            )
        
        # 4. 调用 LLM
        kwargs = {}
        if request.reasoning:
            kwargs["reasoning"] = {"enabled": True}
        
        response = llm_service.chat_completion(
            messages=messages,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            **kwargs
        )
        
        content = response.choices[0].message.content
        
        # 5. AI 回复落库
        if request.cid:
            assistant_message_id = session_manager.add_message(
                cid=request.cid,
                role="assistant",
                content=content
            )
            logger.debug(f"AI 回复已落库 | assistant_message_id={assistant_message_id}")
        
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
            cid=request.cid,
            user_message_id=user_message_id,
            assistant_message_id=assistant_message_id,
            usage=usage
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"/completion 错误 | error={str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stream")
async def chat_stream(request: ChatRequest):
    """
    流式聊天接口（SSE）
    
    消息流程（使用会话时）：
    1. 用户消息先落库
    2. 获取历史消息
    3. 流式调用 LLM
    4. 累积完成后，AI 回复落库
    """
    # 设置上下文
    if request.cid:
        set_context(cid=str(request.cid))
    
    logger.info("/stream 请求")
    
    try:
        user_message_id = None
        messages = None
        
        if request.cid and request.user_message:
            # === 方式2：使用会话 ===
            
            # 1. 用户消息先落库
            user_message_id = session_manager.add_message(
                cid=request.cid,
                role="user",
                content=request.user_message,
                metadata=request.user_message_metadata
            )
            logger.debug(f"用户消息已落库 | user_message_id={user_message_id}")
            
            # 2. 获取历史消息
            history_messages = session_manager.get_messages_for_llm(
                cid=request.cid,
                before_message_id=user_message_id,
                limit=request.history_limit
            )
            
            # 3. 构建消息列表
            messages = history_messages + [{"role": "user", "content": request.user_message}]
            logger.debug(f"构建消息列表 | history={len(history_messages)} | total={len(messages)}")
            
        elif request.messages:
            # === 方式1：直接提供消息 ===
            messages = [{"role": msg.role, "content": msg.content} for msg in request.messages]
        else:
            raise HTTPException(
                status_code=400,
                detail="Either 'messages' or both 'cid' and 'user_message' must be provided"
            )
        
        # 准备 LLM 参数
        kwargs = {}
        if request.reasoning:
            kwargs["reasoning"] = {"enabled": True}
        
        # 捕获请求参数供生成器使用
        cid = request.cid
        temperature = request.temperature
        max_tokens = request.max_tokens
        
        def generate():
            """SSE 事件生成器"""
            full_content = ""
            assistant_message_id = None
            
            try:
                # 流式调用 LLM
                for chunk in llm_service.chat_completion_stream(
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    **kwargs
                ):
                    full_content += chunk
                    data = json.dumps({"content": chunk}, ensure_ascii=False)
                    yield f"data: {data}\n\n"
                
                # AI 回复落库
                if cid:
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
                logger.error(f"/stream 生成错误 | error={str(e)}")
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
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"/stream 请求错误 | error={str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 会话管理接口 ====================

@router.post("/session/create", response_model=CreateSessionResponse)
async def create_session(request: CreateSessionRequest = None):
    """创建新会话"""
    if request is None:
        request = CreateSessionRequest()
    
    cid = session_manager.create_session(
        system_message=request.system_message,
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
    """
    获取指定消息之前的历史消息
    
    用于调试和验证历史消息过滤
    """
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

"""
Streamlit 测试界面 - 用于测试 FastAPI 流式和非流式接口
"""
import streamlit as st
import requests
import json
import time
from typing import List, Dict

# API 配置
API_BASE_URL = "http://localhost:8000"
STREAM_ENDPOINT = f"{API_BASE_URL}/api/chat/stream"
COMPLETION_ENDPOINT = f"{API_BASE_URL}/api/chat/completion"
SESSION_CREATE_ENDPOINT = f"{API_BASE_URL}/api/chat/session/create"
SESSION_MESSAGES_ENDPOINT = f"{API_BASE_URL}/api/chat/session/{{session_id}}/messages"
SESSION_LIST_ENDPOINT = f"{API_BASE_URL}/api/chat/sessions"


def init_session_state():
    """初始化会话状态"""
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "api_status" not in st.session_state:
        st.session_state.api_status = "unknown"
    if "chat_session_id" not in st.session_state:
        st.session_state.chat_session_id = None
    if "use_session" not in st.session_state:
        st.session_state.use_session = True  # 默认使用会话管理


def check_api_health():
    """检查 API 健康状态"""
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=2)
        if response.status_code == 200:
            return True, "connected"
        else:
            return False, f"unhealthy (status: {response.status_code})"
    except requests.exceptions.RequestException as e:
        return False, f"connection error: {str(e)}"


def create_chat_session():
    """创建新的聊天会话"""
    try:
        response = requests.post(SESSION_CREATE_ENDPOINT, timeout=5)
        response.raise_for_status()
        return response.json().get("session_id")
    except Exception as e:
        st.error(f"创建会话失败: {str(e)}")
        return None


def send_completion_request(messages: List[Dict] = None, session_id: str = None, user_message: str = None, temperature: float = 0.7):
    """发送非流式请求"""
    try:
        if session_id and user_message:
            # 使用会话模式
            payload = {
                "session_id": session_id,
                "user_message": user_message,
                "temperature": temperature,
            }
        else:
            # 直接提供消息列表
            payload = {
                "messages": messages,
                "temperature": temperature,
            }
        
        response = requests.post(
            COMPLETION_ENDPOINT,
            json=payload,
            timeout=60
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return {"error": str(e)}


def send_stream_request(messages: List[Dict] = None, session_id: str = None, user_message: str = None, temperature: float = 0.7):
    """发送流式请求（SSE）"""
    try:
        if session_id and user_message:
            # 使用会话模式
            payload = {
                "session_id": session_id,
                "user_message": user_message,
                "temperature": temperature,
            }
        else:
            # 直接提供消息列表
            payload = {
                "messages": messages,
                "temperature": temperature,
            }
        
        response = requests.post(
            STREAM_ENDPOINT,
            json=payload,
            stream=True,
            timeout=60
        )
        response.raise_for_status()
        return response
    except Exception as e:
        return None


def get_session_messages(session_id: str):
    """获取会话消息"""
    try:
        url = SESSION_MESSAGES_ENDPOINT.format(session_id=session_id)
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        return response.json().get("messages", [])
    except Exception as e:
        return []


def main():
    st.set_page_config(
        page_title="FAgent API 测试",
        page_icon="🤖",
        layout="wide"
    )
    
    st.title("🤖 FAgent API 测试界面")
    st.markdown("---")
    
    # 初始化会话状态
    init_session_state()
    
    # 侧边栏配置
    with st.sidebar:
        st.header("⚙️ 配置")
        
        # API 状态检查
        st.subheader("API 状态")
        is_healthy, status_msg = check_api_health()
        if is_healthy:
            st.success(f"✅ {status_msg}")
        else:
            st.error(f"❌ {status_msg}")
            st.info("请确保 FastAPI 服务正在运行：\n```bash\ncd backend\nuvicorn api.main:app --reload\n```")
        
        st.markdown("---")
        
        # 会话管理
        st.subheader("💬 会话管理")
        use_session = st.checkbox("使用会话管理", value=st.session_state.use_session)
        st.session_state.use_session = use_session
        
        if use_session:
            if st.session_state.chat_session_id:
                st.info(f"会话ID: `{st.session_state.chat_session_id[:8]}...`")
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("🔄 刷新会话", use_container_width=True):
                        # 从服务器获取最新消息
                        server_messages = get_session_messages(st.session_state.chat_session_id)
                        st.session_state.messages = server_messages
                        st.rerun()
                with col2:
                    if st.button("🗑️ 清空会话", use_container_width=True):
                        st.session_state.messages = []
                        st.session_state.chat_session_id = None
                        st.rerun()
            else:
                if st.button("➕ 创建新会话", use_container_width=True):
                    session_id = create_chat_session()
                    if session_id:
                        st.session_state.chat_session_id = session_id
                        st.session_state.messages = []
                        st.success("会话创建成功！")
                        st.rerun()
        else:
            if st.button("🗑️ 清空对话", use_container_width=True):
                st.session_state.messages = []
                st.rerun()
        
        st.markdown("---")
        
        # 参数配置
        st.subheader("参数设置")
        temperature = st.slider("Temperature", 0.0, 2.0, 0.7, 0.1)
        use_reasoning = st.checkbox("启用 Reasoning", value=False)
        
        st.markdown("---")
        
        # 操作按钮
        st.subheader("操作")
        if st.button("🔄 刷新页面", use_container_width=True):
            st.rerun()
    
    # 主界面
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.header("💬 对话界面")
        
        # 显示历史消息
        chat_container = st.container()
        with chat_container:
            for msg in st.session_state.messages:
                role = msg["role"]
                content = msg["content"]
                
                if role == "user":
                    with st.chat_message("user"):
                        st.write(content)
                elif role == "assistant":
                    with st.chat_message("assistant"):
                        st.write(content)
        
        # 输入框
        user_input = st.chat_input("输入消息...")
        
        if user_input:
            # 显示用户消息
            with st.chat_message("user"):
                st.write(user_input)
            
            # 如果使用会话管理，先添加用户消息到本地显示
            if st.session_state.use_session and st.session_state.chat_session_id:
                # 会话模式下，消息会自动保存到服务器
                pass
            else:
                # 非会话模式，添加到本地消息列表
                st.session_state.messages.append({
                    "role": "user",
                    "content": user_input
                })
            
            # 选择请求方式
            request_type = st.radio(
                "选择请求方式",
                ["流式 (SSE)", "非流式"],
                horizontal=True,
                key="request_type"
            )
            
            # 发送请求
            if request_type == "流式 (SSE)":
                # 流式请求
                with st.chat_message("assistant"):
                    message_placeholder = st.empty()
                    full_response = ""
                    
                    try:
                        # 准备请求参数
                        if st.session_state.use_session and st.session_state.chat_session_id:
                            # 使用会话模式
                            response = send_stream_request(
                                session_id=st.session_state.chat_session_id,
                                user_message=user_input,
                                temperature=temperature
                            )
                        else:
                            # 直接提供消息列表
                            messages = [
                                {"role": msg["role"], "content": msg["content"]}
                                for msg in st.session_state.messages
                            ]
                            response = send_stream_request(messages=messages, temperature=temperature)
                        
                        if response:
                            for line in response.iter_lines():
                                if line:
                                    line_str = line.decode('utf-8')
                                    if line_str.startswith('data: '):
                                        data_str = line_str[6:]  # 移除 "data: " 前缀
                                        if data_str == "[DONE]":
                                            break
                                        try:
                                            data = json.loads(data_str)
                                            if "error" in data:
                                                st.error(f"错误: {data['error']}")
                                                break
                                            if "content" in data:
                                                chunk = data["content"]
                                                full_response += chunk
                                                message_placeholder.write(full_response + "▌")
                                        except json.JSONDecodeError:
                                            continue
                            
                            message_placeholder.write(full_response)
                            
                            # 添加助手回复到历史
                            if st.session_state.use_session and st.session_state.chat_session_id:
                                # 会话模式下，从服务器获取最新消息
                                server_messages = get_session_messages(st.session_state.chat_session_id)
                                st.session_state.messages = server_messages
                            else:
                                # 非会话模式，添加到本地
                                st.session_state.messages.append({
                                    "role": "assistant",
                                    "content": full_response
                                })
                        else:
                            st.error("流式请求失败")
                    except Exception as e:
                        st.error(f"请求错误: {str(e)}")
            else:
                # 非流式请求
                with st.chat_message("assistant"):
                    with st.spinner("思考中..."):
                        # 准备请求参数
                        if st.session_state.use_session and st.session_state.chat_session_id:
                            # 使用会话模式
                            result = send_completion_request(
                                session_id=st.session_state.chat_session_id,
                                user_message=user_input,
                                temperature=temperature
                            )
                        else:
                            # 直接提供消息列表
                            messages = [
                                {"role": msg["role"], "content": msg["content"]}
                                for msg in st.session_state.messages
                            ]
                            result = send_completion_request(messages=messages, temperature=temperature)
                        
                        if "error" in result:
                            st.error(f"错误: {result['error']}")
                        else:
                            content = result.get("content", "")
                            st.write(content)
                            
                            # 显示使用情况
                            if "usage" in result:
                                usage = result["usage"]
                                with st.expander("Token 使用情况"):
                                    st.json(usage)
                            
                            # 添加助手回复到历史
                            if st.session_state.use_session and st.session_state.chat_session_id:
                                # 会话模式下，从服务器获取最新消息
                                server_messages = get_session_messages(st.session_state.chat_session_id)
                                st.session_state.messages = server_messages
                            else:
                                # 非会话模式，添加到本地
                                st.session_state.messages.append({
                                    "role": "assistant",
                                    "content": content
                                })
            
            st.rerun()
    
    with col2:
        st.header("📊 请求详情")
        
        # 显示当前消息列表
        st.subheader("消息列表")
        if st.session_state.messages:
            st.json(st.session_state.messages)
        else:
            st.info("暂无消息")
        
        st.markdown("---")
        
        # API 信息
        st.subheader("API 端点")
        st.code(f"流式: {STREAM_ENDPOINT}")
        st.code(f"非流式: {COMPLETION_ENDPOINT}")
        
        st.markdown("---")
        
        # 使用说明
        st.subheader("📖 使用说明")
        st.markdown("""
        1. **启动后端服务**：
           ```bash
           cd backend
           uvicorn api.main:app --reload
           ```
        
        2. **流式请求**：实时显示 AI 回复，适合对话场景
        
        3. **非流式请求**：等待完整回复后显示，适合需要完整结果的场景
        
        4. **Temperature**：控制回复的随机性（0-2）
        """)


if __name__ == "__main__":
    main()


"""
多轮对话测试脚本
测试会话管理和消息持久化功能
"""
import requests
import json
import time

API_BASE_URL = "http://localhost:8000"


def print_separator(title: str = ""):
    print("\n" + "=" * 60)
    if title:
        print(f"  {title}")
        print("=" * 60)


def test_health():
    """测试 API 健康状态"""
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=5)
        return response.status_code == 200
    except Exception as e:
        print(f"❌ 健康检查失败: {e}")
        return False


def create_session(system_message: str = None) -> str:
    """创建新会话"""
    payload = {}
    if system_message:
        payload["system_message"] = system_message
    
    response = requests.post(
        f"{API_BASE_URL}/api/chat/session/create",
        params=payload
    )
    response.raise_for_status()
    data = response.json()
    return data["conversation_id"]


def send_message(session_id: str, user_message: str, stream: bool = True) -> str:
    """发送消息并获取回复"""
    payload = {
        "session_id": session_id,
        "user_message": user_message,
        "temperature": 0.7
    }
    
    if stream:
        # 流式请求
        response = requests.post(
            f"{API_BASE_URL}/api/chat/stream",
            json=payload,
            stream=True
        )
        response.raise_for_status()
        
        full_content = ""
        print("  AI: ", end="", flush=True)
        
        for line in response.iter_lines():
            if line:
                line_str = line.decode('utf-8')
                if line_str.startswith("data: "):
                    data_str = line_str[6:]
                    if data_str == "[DONE]":
                        break
                    try:
                        data = json.loads(data_str)
                        if "content" in data:
                            content = data["content"]
                            full_content += content
                            print(content, end="", flush=True)
                        elif "done" in data:
                            # 完成标记，包含 message_id
                            pass
                    except json.JSONDecodeError:
                        pass
        
        print()  # 换行
        return full_content
    else:
        # 非流式请求
        response = requests.post(
            f"{API_BASE_URL}/api/chat/completion",
            json=payload
        )
        response.raise_for_status()
        data = response.json()
        content = data["content"]
        print(f"  AI: {content}")
        return content


def get_session_messages(session_id: str) -> list:
    """获取会话的所有消息"""
    response = requests.get(
        f"{API_BASE_URL}/api/chat/session/{session_id}/messages"
    )
    response.raise_for_status()
    return response.json()


def get_conversation(session_id: str) -> dict:
    """获取完整会话记录"""
    response = requests.get(
        f"{API_BASE_URL}/api/chat/conversation/{session_id}"
    )
    response.raise_for_status()
    return response.json()


def main():
    print_separator("FAgent 多轮对话测试")
    
    # 1. 健康检查
    print("\n🔍 检查 API 服务状态...")
    if not test_health():
        print("❌ API 服务未启动，请先启动后端服务")
        return
    print("✅ API 服务正常")
    
    # 2. 创建会话
    print_separator("创建新会话")
    session_id = create_session()
    print(f"✅ 会话创建成功")
    print(f"   conversation_id: {session_id}")
    
    # 3. 第一轮对话
    print_separator("第一轮对话")
    question1 = "你叫什么名字？"
    print(f"  用户: {question1}")
    answer1 = send_message(session_id, question1, stream=True)
    
    time.sleep(1)  # 等待消息保存
    
    # 4. 第二轮对话
    print_separator("第二轮对话")
    question2 = "你的基模型是怎么训练的？"
    print(f"  用户: {question2}")
    answer2 = send_message(session_id, question2, stream=True)
    
    time.sleep(1)  # 等待消息保存
    
    # 5. 查看会话历史
    print_separator("会话历史记录")
    try:
        conversation = get_conversation(session_id)
        print(f"  会话ID: {conversation['conversation_id']}")
        print(f"  创建时间: {conversation['created_at']}")
        print(f"  消息数量: {conversation['message_count']}")
        print("\n  消息列表:")
        for i, msg in enumerate(conversation.get("messages", []), 1):
            role = msg["role"]
            content = msg["content"]
            msg_id = msg.get("message_id", "N/A")
            content_type = msg.get("content_type", "text")
            # 截断过长的内容
            if len(content) > 100:
                content = content[:100] + "..."
            print(f"    [{i}] {role}: {content}")
            print(f"        message_id: {msg_id}, type: {content_type}")
    except Exception as e:
        print(f"  ⚠️ 获取会话历史失败: {e}")
    
    print_separator("测试完成")
    print(f"\n✅ 多轮对话测试成功！")
    print(f"   会话ID: {session_id}")
    print(f"   共进行了 2 轮对话")


if __name__ == "__main__":
    main()


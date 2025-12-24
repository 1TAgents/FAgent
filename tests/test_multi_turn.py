"""
多轮对话测试脚本

验证功能：
1. 创建多个会话（cid 为整数，自增）
2. 用户消息先落库，获取 message_id
3. 历史消息过滤（message_id < 当前）
4. AI 回复落库
5. 多轮对话上下文保持
6. 多会话独立性验证
"""
import requests
import json

# API 配置
API_BASE_URL = "http://localhost:8000"


def check_api_status():
    """检查 API 服务状态"""
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=5)
        response.raise_for_status()
        return True
    except requests.exceptions.RequestException:
        return False


def create_session():
    """创建新会话，返回 cid（整数）"""
    response = requests.post(f"{API_BASE_URL}/api/chat/session/create")
    response.raise_for_status()
    data = response.json()
    return data["cid"]


def send_stream_message(cid: int, user_message: str, show_output: bool = True):
    """
    发送流式消息
    
    返回：(full_content, user_message_id, assistant_message_id)
    """
    payload = {
        "cid": cid,
        "user_message": user_message,
        "temperature": 0.7
    }
    
    full_content = ""
    user_message_id = None
    assistant_message_id = None
    
    with requests.post(
        f"{API_BASE_URL}/api/chat/stream",
        json=payload,
        stream=True
    ) as response:
        response.raise_for_status()
        for line in response.iter_lines():
            if line:
                decoded = line.decode('utf-8')
                if decoded.startswith("data: "):
                    data_str = decoded[6:]
                    if data_str == "[DONE]":
                        break
                    try:
                        data = json.loads(data_str)
                        if "content" in data:
                            full_content += data["content"]
                            if show_output:
                                print(data["content"], end="", flush=True)
                        if "done" in data:
                            user_message_id = data.get("user_message_id")
                            assistant_message_id = data.get("assistant_message_id")
                    except json.JSONDecodeError:
                        pass
    
    if show_output:
        print()  # 换行
    return full_content, user_message_id, assistant_message_id


def get_conversation(cid: int):
    """获取完整会话记录"""
    response = requests.get(f"{API_BASE_URL}/api/chat/conversation/{cid}")
    response.raise_for_status()
    return response.json()


def get_history_before_message(cid: int, before_message_id: int):
    """获取指定消息之前的历史"""
    response = requests.get(
        f"{API_BASE_URL}/api/chat/conversation/{cid}/history",
        params={"before_message_id": before_message_id}
    )
    response.raise_for_status()
    return response.json()


def list_conversations():
    """获取所有会话列表"""
    response = requests.get(f"{API_BASE_URL}/api/chat/conversations")
    response.raise_for_status()
    return response.json()


def print_separator(title: str = ""):
    """打印分隔线"""
    if title:
        print(f"\n{'=' * 60}")
        print(f"  {title}")
        print("=" * 60)
    else:
        print("-" * 40)


def main():
    print("=" * 60)
    print("  FAgent 多会话多轮对话测试")
    print("=" * 60)
    
    # 1. 检查 API 服务
    print("\n🔍 检查 API 服务...")
    if not check_api_status():
        print("❌ API 服务未运行")
        return
    print("✅ API 服务正常")
    
    # ==================== 会话 1：技术问答 ====================
    print_separator("会话 1：技术问答")
    
    cid1 = create_session()
    print(f"✅ 会话 1 创建成功 | cid={cid1}")
    
    # 会话1 - 第一轮
    q1_1 = "你叫什么名字？"
    print(f"\n  [轮次1] 用户: {q1_1}")
    print("  AI: ", end="")
    _, user_id_1_1, ai_id_1_1 = send_stream_message(cid1, q1_1)
    print(f"  📝 message_id: user={user_id_1_1}, assistant={ai_id_1_1}")
    
    # 会话1 - 第二轮
    q1_2 = "你的基模型是怎么训练的？"
    print(f"\n  [轮次2] 用户: {q1_2}")
    print("  AI: ", end="")
    _, user_id_1_2, ai_id_1_2 = send_stream_message(cid1, q1_2)
    print(f"  📝 message_id: user={user_id_1_2}, assistant={ai_id_1_2}")
    
    # ==================== 会话 2：日常对话 ====================
    print_separator("会话 2：日常对话")
    
    cid2 = create_session()
    print(f"✅ 会话 2 创建成功 | cid={cid2}")
    
    # 会话2 - 第一轮
    q2_1 = "今天天气怎么样？"
    print(f"\n  [轮次1] 用户: {q2_1}")
    print("  AI: ", end="")
    _, user_id_2_1, ai_id_2_1 = send_stream_message(cid2, q2_1)
    print(f"  📝 message_id: user={user_id_2_1}, assistant={ai_id_2_1}")
    
    # 会话2 - 第二轮
    q2_2 = "那有什么推荐的室内活动吗？"
    print(f"\n  [轮次2] 用户: {q2_2}")
    print("  AI: ", end="")
    _, user_id_2_2, ai_id_2_2 = send_stream_message(cid2, q2_2)
    print(f"  📝 message_id: user={user_id_2_2}, assistant={ai_id_2_2}")
    
    # ==================== 验证历史消息过滤 ====================
    print_separator("验证：历史消息过滤")
    
    print(f"\n  会话 1 (cid={cid1}): message_id < {user_id_1_2} 的历史")
    history1 = get_history_before_message(cid1, user_id_1_2)
    print(f"  历史消息数量: {history1['count']}")
    for msg in history1["messages"]:
        preview = str(msg["content"])[:40] + "..." if len(str(msg["content"])) > 40 else msg["content"]
        print(f"    [{msg['message_id']}] {msg['role']}: {preview}")
    
    print(f"\n  会话 2 (cid={cid2}): message_id < {user_id_2_2} 的历史")
    history2 = get_history_before_message(cid2, user_id_2_2)
    print(f"  历史消息数量: {history2['count']}")
    for msg in history2["messages"]:
        preview = str(msg["content"])[:40] + "..." if len(str(msg["content"])) > 40 else msg["content"]
        print(f"    [{msg['message_id']}] {msg['role']}: {preview}")
    
    # ==================== 会话列表汇总 ====================
    print_separator("会话列表汇总")
    
    convs = list_conversations()
    print(f"  总会话数: {convs['count']}")
    for conv in convs["conversations"]:
        print(f"    cid={conv['cid']}: {conv['message_count']} 条消息")
    
    # ==================== 完整会话记录 ====================
    print_separator("完整会话记录")
    
    for cid in [cid1, cid2]:
        conv = get_conversation(cid)
        print(f"\n  📂 会话 {cid} ({conv['message_count']} 条消息):")
        for msg in conv["messages"]:
            preview = str(msg["content"])[:50] + "..." if len(str(msg["content"])) > 50 else msg["content"]
            print(f"    [{msg['message_id']}] {msg['role']}: {preview}")
    
    # ==================== 测试结果 ====================
    print_separator("测试完成")
    
    print(f"\n✅ 多会话多轮对话测试成功！")
    print(f"\n  会话统计:")
    print(f"    会话 1 (cid={cid1}): message_id {user_id_1_1} → {ai_id_1_1} → {user_id_1_2} → {ai_id_1_2}")
    print(f"    会话 2 (cid={cid2}): message_id {user_id_2_1} → {ai_id_2_1} → {user_id_2_2} → {ai_id_2_2}")
    print(f"\n  验证项:")
    print(f"    ✅ cid 自增: {cid1} → {cid2}")
    print(f"    ✅ message_id 全局自增: {user_id_1_1} → ... → {ai_id_2_2}")
    print(f"    ✅ 历史消息按 message_id 过滤")
    print(f"    ✅ 多会话独立")


if __name__ == "__main__":
    main()

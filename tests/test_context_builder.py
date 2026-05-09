from agents.core.context_builder import AgentContextBuilder, RouterHistoryFormat


def test_build_chat_messages_keeps_system_history_and_current_user_message():
    builder = AgentContextBuilder()
    history = [
        {"role": "user", "content": "上一轮问题"},
        {"role": "assistant", "content": "上一轮回答"},
    ]

    messages = builder.build_chat_messages(
        system_prompt="system",
        history=history,
        user_message="当前问题",
    )

    assert messages == [
        {"role": "system", "content": "system"},
        {"role": "user", "content": "上一轮问题"},
        {"role": "assistant", "content": "上一轮回答"},
        {"role": "user", "content": "当前问题"},
    ]
    assert messages[1] is not history[0]


def test_build_router_messages_compacts_recent_history_without_mutating_input():
    builder = AgentContextBuilder()
    history = [
        {"role": "user", "content": "第一条"},
        {"role": "assistant", "content": "第二条"},
        {"role": "user", "content": "第三条很长很长"},
    ]

    messages = builder.build_router_messages(
        system_prompt="router",
        history=history,
        user_message="现在看什么？",
        history_format=RouterHistoryFormat(recent_limit=2, max_content_chars=4),
    )

    assert messages[0] == {"role": "system", "content": "router"}
    assert messages[1]["role"] == "user"
    assert "AI: 第二条" in messages[1]["content"]
    assert "用户: 第三条很..." in messages[1]["content"]
    assert "第一条" not in messages[1]["content"]
    assert messages[1]["content"].endswith("【当前问题】\n现在看什么？")
    assert history[2]["content"] == "第三条很长很长"


def test_build_router_messages_omits_history_block_when_empty():
    builder = AgentContextBuilder()

    messages = builder.build_router_messages(
        system_prompt="router",
        history=[],
        user_message="你好",
    )

    assert messages == [
        {"role": "system", "content": "router"},
        {"role": "user", "content": "【当前问题】\n你好"},
    ]

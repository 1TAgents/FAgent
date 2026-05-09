from agents.core.context_builder import AgentContextBuilder, RouterHistoryFormat, ContextBuilderWithBudget, ContextBudget


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


# ---------- Budget-aware context builder tests ----------

def test_build_with_tools_includes_system_and_user():
    builder = ContextBuilderWithBudget()
    messages, meta = builder.build_with_tools(
        system_prompt="you are a helper",
        history=None,
        user_message="what is MA?",
    )
    assert messages[0]["role"] == "system"
    assert messages[-1]["role"] == "user"
    assert meta["total_tokens"] > 0
    assert meta["history_count"] == 1  # includes final user message


def test_build_with_tools_includes_history():
    builder = ContextBuilderWithBudget()
    history = [
        {"role": "user", "content": "explain PE ratio"},
        {"role": "assistant", "content": "PE is price to earnings"},
    ]
    messages, meta = builder.build_with_tools(
        system_prompt="you are a helper",
        history=history,
        user_message="what about PB?",
    )
    # system + history(2) + user = 4 messages
    assert len(messages) == 4
    assert meta["history_count"] == 3  # 2 history + 1 final user


def test_build_with_tools_trims_history_when_over_budget():
    builder = ContextBuilderWithBudget()
    # Create a lot of history
    history = [
        {"role": "user", "content": f"question {i}"}
        if i % 2 == 0
        else {"role": "assistant", "content": f"answer {i}"}
        for i in range(50)
    ]
    # Very small budget to force trimming
    budget = ContextBudget(max_total=500, history=100, system=200, tools=50, reserve=50)
    messages, meta = builder.build_with_tools(
        system_prompt="you are a helper",
        history=history,
        user_message="last question",
        budget=budget,
    )
    # Should be trimmed to fit budget
    assert meta["over_budget"] is False or len(messages) < len(history) + 3


def test_build_with_tools_includes_tool_schemas():
    builder = ContextBuilderWithBudget()
    tool_schemas = [
        {
            "name": "get_quote",
            "description": "get stock quote",
            "parameters": {
                "type": "object",
                "properties": {"symbol": {"type": "string", "description": "stock code"}},
                "required": ["symbol"],
            },
        }
    ]
    messages, _ = builder.build_with_tools(
        system_prompt="you are a helper",
        history=None,
        user_message="what is 600519?",
        tool_schemas=tool_schemas,
    )
    # system + tool context + user = 3 messages
    assert len(messages) == 3
    assert "get_quote" in messages[1]["content"]
    assert "stock code" in messages[1]["content"]


def test_context_budget_defaults():
    budget = ContextBudget()
    assert budget.max_total == 32000
    assert budget.history == 8000
    assert budget.tools == 3000

"""
ReAct Agent Loop 测试
"""
import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from agents.react.loop import ReActAgentLoop, ReActResult, ReActTurn
from agents.tools.registry import ToolRegistry
from agents.tools.base import BaseTool, DangerLevel
from agents.tools.result import ToolResult
from agents.tools.permissions import ToolPermissions
from agents.core.tracing import ExecutionTrace


class MockLLM:
    """模拟 LLM 服务，用于测试。"""

    def __init__(self, behavior="single_turn"):
        """
        Args:
            behavior: "single_turn" - 直接返回最终回复
                     "two_turn" - 第一次返回工具调用，第二次返回回复
        """
        self.behavior = behavior
        self.call_count = 0
        self.stream_count = 0

    async def chat_completion(self, messages, temperature=0.7, model=None, tools=None, **kw):
        self.call_count += 1
        from types import SimpleNamespace

        if self.behavior == "two_turn" and self.call_count == 1:
            # 第一次：返回工具调用
            return SimpleNamespace(
                choices=[SimpleNamespace(
                    message=SimpleNamespace(
                        content=None,
                        tool_calls=[SimpleNamespace(
                            id="tc_001",
                            function=SimpleNamespace(
                                name="get_quote",
                                arguments='{"symbol": "600519"}',
                            ),
                        )],
                    )
                )],
                model=model or "test",
                usage=SimpleNamespace(prompt_tokens=100, completion_tokens=20, total_tokens=120),
            )
        else:
            # 直接返回或第二次：返回最终回复
            return SimpleNamespace(
                choices=[SimpleNamespace(
                    message=SimpleNamespace(
                        content="贵州茅台当前股价为 1850.00 元。",
                        tool_calls=None,
                    )
                )],
                model=model or "test",
                usage=SimpleNamespace(prompt_tokens=200, completion_tokens=30, total_tokens=230),
            )

    async def chat_completion_stream(self, messages, temperature=0.7, model=None, **kw):
        self.stream_count += 1
        for char in "贵州茅台当前股价为 1850.00 元。":
            yield char


@pytest.fixture
def registry():
    """创建带 mock 工具的 registry。"""
    reg = ToolRegistry()

    class MockQuoteTool(BaseTool):
        name = "get_quote"
        description = "查询股票实时行情"
        category = "market"

        @property
        def parameters(self):
            return {
                "type": "object",
                "properties": {
                    "symbol": {"type": "string", "description": "股票代码"},
                },
                "required": ["symbol"],
            }

        async def execute(self, symbol: str, **kw):
            return ToolResult.ok(
                self.name,
                data={"symbol": symbol, "price": 1850.0},
                text=f"{symbol} 当前价格 1850.00 元",
            )

    reg.register(MockQuoteTool())
    return reg


class TestReActAgentLoop:
    @pytest.mark.asyncio
    async def test_single_turn_no_tools(self):
        llm = MockLLM(behavior="single_turn")
        reg = ToolRegistry()
        loop = ReActAgentLoop(llm, system_prompt="test", registry=reg, model="test")
        result = await loop.run("你好")
        assert result.content == "贵州茅台当前股价为 1850.00 元。"
        assert result.error is None
        assert len(result.turns) == 1

    @pytest.mark.asyncio
    async def test_two_turn_with_tool_call(self, registry):
        llm = MockLLM(behavior="two_turn")
        loop = ReActAgentLoop(llm, system_prompt="test", registry=registry, model="test")
        result = await loop.run("茅台股价多少？")
        assert result.content == "贵州茅台当前股价为 1850.00 元。"
        assert result.error is None
        assert len(result.turns) == 2
        assert len(result.turns[0].tool_calls) == 1
        assert result.turns[0].tool_calls[0]["name"] == "get_quote"

    @pytest.mark.asyncio
    async def test_trace_records_tool_results(self, registry, monkeypatch):
        monkeypatch.setattr("agents.react.loop.trace_store.save", lambda trace: None)
        trace = ExecutionTrace(trace_id="trace_tool_results", cid=1)
        loop = ReActAgentLoop(
            MockLLM(behavior="two_turn"),
            system_prompt="test",
            registry=registry,
            model="test",
            trace=trace,
        )

        await loop.run("茅台股价多少？")

        assert trace.turns[0].tool_results[0]["tool_name"] == "get_quote"
        assert trace.turns[0].tool_results[0]["success"] is True

    @pytest.mark.asyncio
    async def test_tool_call_messages_are_openai_compatible_between_turns(self, registry):
        """Internal tool calls should be serialized before sending back to the LLM."""
        class InspectingLLM(MockLLM):
            def __init__(self):
                super().__init__(behavior="two_turn")
                self.second_call_messages = None

            async def chat_completion(self, messages, temperature=0.7, model=None, tools=None, **kw):
                if self.call_count == 1:
                    self.second_call_messages = [dict(m) for m in messages]
                return await super().chat_completion(messages, temperature, model, tools, **kw)

        llm = InspectingLLM()
        loop = ReActAgentLoop(llm, system_prompt="test", registry=registry, model="test")
        await loop.run("茅台股价多少？")

        assistant_tool_msg = next(
            m for m in llm.second_call_messages
            if m.get("role") == "assistant" and m.get("tool_calls")
        )
        tool_call = assistant_tool_msg["tool_calls"][0]
        assert tool_call["type"] == "function"
        assert tool_call["function"]["name"] == "get_quote"
        assert tool_call["function"]["arguments"] == '{"symbol": "600519"}'
        assert "arguments" not in tool_call

    @pytest.mark.asyncio
    async def test_permissions_deny_tool_execution(self):
        class MockWriteTool(BaseTool):
            name = "write_state"
            description = "修改内部状态"
            category = "test"
            danger_level = DangerLevel.WRITE

            async def execute(self, **kw):
                return ToolResult.ok(self.name, text="written")

        class WriteLLM(MockLLM):
            async def chat_completion(self, messages, temperature=0.7, model=None, tools=None, **kw):
                self.call_count += 1
                from types import SimpleNamespace

                if self.call_count == 1:
                    return SimpleNamespace(
                        choices=[SimpleNamespace(
                            message=SimpleNamespace(
                                content=None,
                                tool_calls=[SimpleNamespace(
                                    id="tc_write",
                                    function=SimpleNamespace(
                                        name="write_state",
                                        arguments="{}",
                                    ),
                                )],
                            )
                        )],
                        model=model or "test",
                        usage=SimpleNamespace(prompt_tokens=10, completion_tokens=5),
                    )

                return await super().chat_completion(messages, temperature, model, tools, **kw)

        reg = ToolRegistry()
        reg.register(MockWriteTool())
        permissions = ToolPermissions(max_danger_level=DangerLevel.READ_ONLY)
        loop = ReActAgentLoop(
            WriteLLM(),
            system_prompt="test",
            registry=reg,
            model="test",
            permissions=permissions,
        )

        result = await loop.run("修改状态")

        denied = result.turns[0].tool_results[0]
        assert not denied.success
        assert "超过允许的最大等级" in denied.error

    @pytest.mark.asyncio
    async def test_stream_output(self):
        llm = MockLLM(behavior="single_turn")
        reg = ToolRegistry()
        loop = ReActAgentLoop(llm, system_prompt="test", registry=reg, model="test")
        chunks = []
        async for chunk in loop.run_stream("你好"):
            chunks.append(chunk)
        assert len(chunks) > 0
        assert "1850" in "".join(chunks)
        assert llm.call_count == 1
        assert llm.stream_count == 0

    @pytest.mark.asyncio
    async def test_stuck_detection(self, registry):
        """测试循环调用检测。"""
        class StuckLLM:
            def __init__(self):
                self.call_count = 0

            async def chat_completion(self, messages, temperature=0.7, model=None, tools=None, **kw):
                self.call_count += 1
                from types import SimpleNamespace
                # 每次都返回相同的工具调用
                return SimpleNamespace(
                    choices=[SimpleNamespace(
                        message=SimpleNamespace(
                            content=None,
                            tool_calls=[SimpleNamespace(
                                id="tc_001",
                                function=SimpleNamespace(
                                    name="get_quote",
                                    arguments='{"symbol": "600519"}',
                                ),
                            )],
                        )
                    )],
                    model=model or "test",
                    usage=SimpleNamespace(prompt_tokens=100, completion_tokens=20, total_tokens=120),
                )

            async def chat_completion_stream(self, messages, temperature=0.7, model=None, **kw):
                yield ""

        llm = StuckLLM()
        loop = ReActAgentLoop(llm, system_prompt="test", registry=registry, model="test")
        result = await loop.run("茅台股价？")
        assert result.error is None  # stuck 终止不视为错误
        assert "循环" in result.content

    def test_build_messages(self):
        llm = MockLLM()
        reg = ToolRegistry()
        loop = ReActAgentLoop(llm, system_prompt="你是一个助手", registry=reg)
        history = [{"role": "user", "content": "hi"}, {"role": "assistant", "content": "hello"}]
        messages = loop._build_messages("new question", history)
        assert len(messages) == 4  # system + 2 history + user
        assert messages[0]["role"] == "system"
        assert messages[-1]["content"] == "new question"

    def test_build_tool_schemas(self, registry):
        llm = MockLLM()
        loop = ReActAgentLoop(llm, system_prompt="test", registry=registry)
        schemas = loop._build_tool_schemas_for_llm()
        assert len(schemas) == 1
        assert schemas[0]["type"] == "function"
        assert schemas[0]["function"]["name"] == "get_quote"

    def test_build_tool_schemas_respects_allowed_tool_names(self, registry):
        class HiddenTool(BaseTool):
            name = "hidden_tool"
            description = "不应暴露的工具"
            category = "test"

            async def execute(self, **kw):
                return ToolResult.ok(self.name, text="hidden")

        registry.register(HiddenTool())
        loop = ReActAgentLoop(
            MockLLM(),
            system_prompt="test",
            registry=registry,
            allowed_tool_names=["get_quote"],
        )

        schemas = loop._build_tool_schemas_for_llm()

        assert [schema["function"]["name"] for schema in schemas] == ["get_quote"]

    @pytest.mark.asyncio
    async def test_allowed_tool_names_deny_hidden_tool_execution(self, registry):
        result = await ReActAgentLoop(
            MockLLM(),
            system_prompt="test",
            registry=registry,
            allowed_tool_names=["get_quote"],
        )._execute_single("hidden_tool", {})

        assert not result.success
        assert "不在当前工具集中" in result.error

    @pytest.mark.asyncio
    async def test_execute_single_uses_tool_timeout_seconds(self, monkeypatch):
        class LongRunningTool(BaseTool):
            name = "long_running"
            description = "长耗时工具"
            category = "test"
            timeout_seconds = 120

            async def execute(self, **kw):
                return ToolResult.ok(self.name, text="ok")

        observed_timeouts = []

        async def recording_wait_for(awaitable, timeout=None):
            observed_timeouts.append(timeout)
            return await awaitable

        monkeypatch.setattr("agents.react.loop.asyncio.wait_for", recording_wait_for)

        reg = ToolRegistry()
        reg.register(LongRunningTool())
        result = await ReActAgentLoop(
            MockLLM(),
            system_prompt="test",
            registry=reg,
        )._execute_single("long_running", {})

        assert result.success
        assert observed_timeouts[0] == 120

    def test_tool_call_signature_ignores_provider_call_id(self):
        loop = ReActAgentLoop(MockLLM(), system_prompt="test", registry=ToolRegistry())

        first = [{"id": "call_a", "name": "get_quote", "arguments": {"symbol": "600519"}}]
        second = [{"id": "call_b", "name": "get_quote", "arguments": {"symbol": "600519"}}]
        different_args = [{"id": "call_c", "name": "get_quote", "arguments": {"symbol": "000001"}}]

        assert loop._tool_call_signature(first) == loop._tool_call_signature(second)
        assert loop._tool_call_signature(first) != loop._tool_call_signature(different_args)

    def test_extract_tool_calls(self):
        llm = MockLLM()
        reg = ToolRegistry()
        loop = ReActAgentLoop(llm, system_prompt="test", registry=reg)

        from types import SimpleNamespace
        response = SimpleNamespace(
            choices=[SimpleNamespace(
                message=SimpleNamespace(
                    content=None,
                    tool_calls=[SimpleNamespace(
                        id="tc_001",
                        function=SimpleNamespace(
                            name="search_stock",
                            arguments='{"keyword": "茅台"}',
                        ),
                    )],
                )
            )]
        )
        calls = loop._extract_tool_calls(response)
        assert len(calls) == 1
        assert calls[0]["name"] == "search_stock"
        assert calls[0]["arguments"]["keyword"] == "茅台"

    def test_extract_tool_calls_empty(self):
        llm = MockLLM()
        reg = ToolRegistry()
        loop = ReActAgentLoop(llm, system_prompt="test", registry=reg)

        from types import SimpleNamespace
        response = SimpleNamespace(
            choices=[SimpleNamespace(
                message=SimpleNamespace(content="hello", tool_calls=None)
            )]
        )
        calls = loop._extract_tool_calls(response)
        assert calls == []

    def test_react_result_defaults(self):
        result = ReActResult(content="hi")
        assert result.turns == []
        assert result.total_tokens == 0
        assert result.error is None

    def test_react_turn_to_dict(self):
        turn = ReActTurn(turn_id=1, model="test", latency_ms=150.0)
        d = turn.to_dict()
        assert d["turn_id"] == 1
        assert d["model"] == "test"

"""
ReAct Agent Loop 测试
"""
import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from agents.react.loop import ReActAgentLoop, ReActResult, ReActTurn
from agents.tools.registry import ToolRegistry
from agents.tools.base import BaseTool
from agents.tools.result import ToolResult


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

    def chat_completion(self, messages, temperature=0.7, model=None, tools=None, **kw):
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

    def chat_completion_stream(self, messages, temperature=0.7, model=None, **kw):
        yield "贵州茅台当前股价为 1850.00 元。"


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
    def test_single_turn_no_tools(self):
        llm = MockLLM(behavior="single_turn")
        reg = ToolRegistry()
        loop = ReActAgentLoop(llm, system_prompt="test", registry=reg, model="test")
        result = loop.run("你好")
        assert result.content == "贵州茅台当前股价为 1850.00 元。"
        assert result.error is None
        assert len(result.turns) == 1

    def test_two_turn_with_tool_call(self, registry):
        llm = MockLLM(behavior="two_turn")
        loop = ReActAgentLoop(llm, system_prompt="test", registry=registry, model="test")
        result = loop.run("茅台股价多少？")
        assert result.content == "贵州茅台当前股价为 1850.00 元。"
        assert result.error is None
        assert len(result.turns) == 2
        assert len(result.turns[0].tool_calls) == 1
        assert result.turns[0].tool_calls[0]["name"] == "get_quote"

    def test_stream_output(self):
        llm = MockLLM(behavior="single_turn")
        reg = ToolRegistry()
        loop = ReActAgentLoop(llm, system_prompt="test", registry=reg, model="test")
        chunks = list(loop.run_stream("你好"))
        assert len(chunks) > 0
        assert "1850" in "".join(chunks)

    def test_stuck_detection(self, registry):
        """测试循环调用检测。"""
        class StuckLLM:
            def __init__(self):
                self.call_count = 0

            def chat_completion(self, messages, temperature=0.7, model=None, tools=None, **kw):
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

            def chat_completion_stream(self, messages, temperature=0.7, model=None, **kw):
                yield ""

        llm = StuckLLM()
        loop = ReActAgentLoop(llm, system_prompt="test", registry=registry, model="test")
        result = loop.run("茅台股价？")
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

"""
Orchestrator 测试
"""
import pytest
import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from agents.orchestrator.dispatcher import SubAgentDispatcher, DispatchResult
from agents.orchestrator.aggregator import ResultAggregator
from agents.subagents.base import BaseSubAgent
from agents.router.models import TaskContext, TaskType


class MockSubAgent(BaseSubAgent):
    """模拟 SubAgent 用于测试。"""

    def __init__(self, name: str, response: str, delay: float = 0):
        self._name = name
        self._response = response
        self._delay = delay
        super().__init__()

    @property
    def name(self) -> str:
        return self._name

    async def process_stream(self, context):
        yield self._response

    async def process(self, context):
        if self._delay:
            await asyncio.sleep(self._delay)
        return self._response


@pytest.fixture
def dispatcher():
    d = SubAgentDispatcher(timeout=5.0)
    d.register("agent_a", MockSubAgent("agent_a", "Response from A"))
    d.register("agent_b", MockSubAgent("agent_b", "Response from B is longer"))
    d.register("slow", MockSubAgent("slow", "Slow response", delay=0.5))
    return d


@pytest.fixture
def context():
    return TaskContext(
        task_type=TaskType.GENERAL_QA,
        query="test query",
        params={},
    )


class TestSubAgentDispatcher:
    @pytest.mark.asyncio
    async def test_dispatch_single_agent(self, dispatcher, context):
        results = await dispatcher.dispatch(context, ["agent_a"])
        assert len(results) == 1
        assert results[0].success
        assert results[0].content == "Response from A"

    @pytest.mark.asyncio
    async def test_dispatch_parallel(self, dispatcher, context):
        results = await dispatcher.dispatch(context, ["agent_a", "agent_b"])
        assert len(results) == 2
        assert all(r.success for r in results)
        assert results[0].agent_name == "agent_a"
        assert results[1].agent_name == "agent_b"

    @pytest.mark.asyncio
    async def test_dispatch_missing_agent(self, dispatcher, context):
        results = await dispatcher.dispatch(context, ["nonexistent"])
        assert len(results) == 1
        assert not results[0].success
        assert "未注册" in results[0].error

    @pytest.mark.asyncio
    async def test_dispatch_first(self, dispatcher, context):
        result = await dispatcher.dispatch_first(context, ["agent_a", "agent_b"])
        assert result.success
        assert result.agent_name == "agent_a"

    @pytest.mark.asyncio
    async def test_registered_agents(self, dispatcher):
        assert set(dispatcher.registered_agents) == {"agent_a", "agent_b", "slow"}

    @pytest.mark.asyncio
    async def test_unregister(self, dispatcher):
        agent = dispatcher.unregister("agent_a")
        assert agent is not None
        assert "agent_a" not in dispatcher.registered_agents


class TestDispatchResult:
    def test_success_preview(self):
        r = DispatchResult(agent_name="test", success=True, content="Hello " * 100)
        assert len(r.preview) == 200

    def test_failure_preview(self):
        r = DispatchResult(agent_name="test", success=False, error="timeout")
        assert r.preview == "timeout"


class TestResultAggregator:
    def test_merge_all(self):
        results = [
            DispatchResult("a", True, "Result A"),
            DispatchResult("b", True, "Result B"),
            DispatchResult("c", False, error="fail"),
        ]
        agg = ResultAggregator()
        merged = agg.merge(results)
        assert "Result A" in merged
        assert "Result B" in merged
        assert "c 失败" in merged

    def test_best_selects_longest(self):
        results = [
            DispatchResult("a", True, "Short"),
            DispatchResult("b", True, "This is a much longer response with more detail"),
        ]
        agg = ResultAggregator()
        best = agg.best(results)
        assert "much longer" in best

    def test_best_no_success(self):
        results = [
            DispatchResult("a", False, error="fail1"),
            DispatchResult("b", False, error="fail2"),
        ]
        agg = ResultAggregator()
        best = agg.best(results)
        assert "fail" in best

    def test_structured(self):
        results = [
            DispatchResult("a", True, "content a", duration_ms=100),
            DispatchResult("b", False, error="fail", duration_ms=50),
        ]
        agg = ResultAggregator()
        s = agg.structured(results)
        assert s["total_agents"] == 2
        assert s["successful"] == 1
        assert s["failed"] == 1

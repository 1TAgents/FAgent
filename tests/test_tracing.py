"""
Tracing 模块测试
"""
import pytest
import sys
import os
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from agents.core.tracing import ExecutionTrace, TurnTrace, SessionMetrics, TraceStore


class TestExecutionTrace:
    def test_create_trace(self):
        trace = ExecutionTrace(trace_id="test_001", cid=42, user_message="hello")
        assert trace.cid == 42
        assert trace.user_message == "hello"
        assert trace.turns == []

    def test_start_turn(self):
        trace = ExecutionTrace(trace_id="test_001")
        turn = trace.start_turn(turn_id=1)
        assert turn.turn_id == 1
        assert len(trace.turns) == 1

    def test_turn_with_data(self):
        trace = ExecutionTrace(trace_id="test_001")
        turn = trace.start_turn(turn_id=1)
        turn.model = "qwen/qwen3.5-plus"
        turn.input_tokens = 100
        turn.output_tokens = 50
        turn.tool_calls = [{"name": "get_quote", "params": {"symbol": "600519"}}]
        turn.latency_ms = 150.5

        assert len(trace.turns) == 1
        assert trace.turns[0].input_tokens == 100

    def test_to_dict(self):
        trace = ExecutionTrace(trace_id="t1", cid=1, user_message="hi", route="chat")
        d = trace.to_dict()
        assert d["trace_id"] == "t1"
        assert d["cid"] == 1
        assert d["route"] == "chat"
        assert "turns" in d

    def test_summarize(self):
        trace = ExecutionTrace(trace_id="t1", cid=1, total_tokens=500)
        s = trace.summarize()
        assert s["total_tokens"] == 500
        assert "trace_id" in s


class TestSessionMetrics:
    def test_record_trace(self):
        metrics = SessionMetrics(cid=1)
        trace = ExecutionTrace(
            trace_id="t1", cid=1, route="market",
            total_tokens=200, total_latency_ms=1000,
            turns=[TurnTrace(turn_id=1)],
        )
        metrics.record_trace(trace)
        assert metrics.total_requests == 1
        assert metrics.total_tokens == 200
        assert metrics.route_distribution["market"] == 1

    def test_record_multiple_traces(self):
        metrics = SessionMetrics(cid=1)
        for i in range(3):
            trace = ExecutionTrace(
                trace_id=f"t{i}", cid=1, route="market" if i < 2 else "chat",
                total_tokens=100, total_latency_ms=500,
                turns=[TurnTrace(turn_id=1)],
            )
            metrics.record_trace(trace)
        assert metrics.total_requests == 3
        assert metrics.route_distribution["market"] == 2
        assert metrics.route_distribution["chat"] == 1
        assert abs(metrics.avg_tokens_per_request - 100.0) < 0.01

    def test_error_counting(self):
        metrics = SessionMetrics(cid=1)
        trace = ExecutionTrace(trace_id="t1", cid=1, error="timeout")
        metrics.record_trace(trace)
        assert metrics.error_count == 1


class TestTraceStore:
    def test_save_and_retrieve(self):
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            store = TraceStore(db_path=f.name)
            trace = ExecutionTrace(
                trace_id="test_001", cid=42, mid=100, rid=1,
                user_message="test", route="market", task_type="get_quote",
                total_tokens=300, total_latency_ms=1500,
            )
            store.save(trace)

            result = store.get_by_trace_id("test_001")
            assert result is not None
            assert result["cid"] == 42
            assert result["user_message"] == "test"

    def test_get_by_session(self):
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            store = TraceStore(db_path=f.name)
            for i in range(5):
                store.save(ExecutionTrace(
                    trace_id=f"t{i}", cid=99,
                    user_message=f"msg {i}", route="chat",
                ))
            rows = store.get_by_session(99, limit=3)
            assert len(rows) == 3

    def test_session_metrics(self):
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            store = TraceStore(db_path=f.name)
            for i in range(3):
                store.save(ExecutionTrace(
                    trace_id=f"t{i}", cid=55,
                    total_tokens=200, total_latency_ms=1000,
                    route="market",
                ))
            metrics = store.get_session_metrics(55)
            assert metrics.total_requests == 3
            assert metrics.total_tokens == 600
            assert metrics.total_latency_ms == 3000.0

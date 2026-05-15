#!/usr/bin/env python3
"""
FAgent 冒烟测试 — 端到端验证核心链路

不依赖外部服务（LLM API / backend），使用 Mock 对象。
验证：Router → ReAct Loop → Tool Registry → Memory → Tracing 全链路。
"""
import asyncio
import json
import os
import sys
import tempfile
import time
from pathlib import Path
from typing import Optional
from types import SimpleNamespace
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from agents.react.loop import ReActAgentLoop
from agents.router.models import TaskContext, RouteType
from agents.tools.registry import ToolRegistry
from agents.tools.builtin import register_builtin_tools
from agents.tools.base import BaseTool, ToolResult, DangerLevel
from agents.services.memory_bridge import memory_bridge, MemoryEntry
from agents.core.tracing import trace_store, ExecutionTrace
from agents.core.session_state import session_state
from agents.core.prompt_builder import prompt_builder


# ==================== Mock 组件 ====================


class MockLLMService:
    """模拟 LLM 服务，支持 chat_completion 和 chat_completion_stream。"""

    def __init__(self):
        self.calls = []

    async def chat_completion(self, messages, temperature=0.7, model=None, tools=None, **kw):
        self.calls.append({"type": "completion", "messages": messages})
        return SimpleNamespace(
            choices=[SimpleNamespace(
                message=SimpleNamespace(
                    content=None,
                    tool_calls=[SimpleNamespace(
                        id="tc_001",
                        function=SimpleNamespace(
                            name="get_market_summary",
                            arguments="{}",
                        ),
                    )],
                )
            )],
            model=model or "mock",
            usage=SimpleNamespace(prompt_tokens=50, completion_tokens=10, total_tokens=60),
        )

    async def chat_completion_stream(self, messages, temperature=0.7, model=None, tools=None, **kw):
        self.calls.append({"type": "stream", "messages": messages})
        # 第一次：返回工具调用
        yield SimpleNamespace(
            choices=[SimpleNamespace(
                delta=SimpleNamespace(
                    content=None,
                    tool_calls=[SimpleNamespace(
                        id="tc_001",
                        function=SimpleNamespace(
                            name="get_market_summary",
                            arguments="{}",
                        ),
                    )],
                )
            )],
            model=model or "mock",
        )
        # 第二次：返回最终回复
        yield SimpleNamespace(
            choices=[SimpleNamespace(
                delta=SimpleNamespace(content="当前市场整体平稳。", role="assistant"),
            )],
            model=model or "mock",
            usage=SimpleNamespace(prompt_tokens=80, completion_tokens=30, total_tokens=110),
        )


class MockMarketTool(BaseTool):
    """模拟行情工具，继承 BaseTool 以获得所有必需属性。"""

    name = "get_market_summary"
    description = "获取市场概况"
    parameters = {
        "type": "object",
        "properties": {},
    }
    category = "market"
    danger_level = DangerLevel.READ_ONLY

    async def execute(self, **kwargs) -> ToolResult:
        return ToolResult.ok(self.name, text="上证指数 3200 点，成交量温和。")


def run_sync(test_fn):
    """同步运行异步测试函数。"""
    return asyncio.get_event_loop().run_until_complete(test_fn())


# ==================== 测试用例 ====================


def test_tool_registry_full_registration():
    """验证所有内置工具正确注册。"""
    registry = ToolRegistry()
    register_builtin_tools(registry)

    names = registry.tool_names
    assert len(names) >= 11, f"期望至少 11 个工具，实际 {len(names)}"

    # 验证各分类
    market_tools = registry.list_by_category("market")
    backtest_tools = registry.list_by_category("backtest")
    trading_tools = registry.list_by_category("trading")

    assert len(market_tools) >= 4, f"行情工具不足: {len(market_tools)}"
    assert len(backtest_tools) >= 4, f"回测工具不足: {len(backtest_tools)}"
    assert len(trading_tools) >= 3, f"交易工具不足: {len(trading_tools)}"

    # 验证每个工具有有效的 schema
    for name in names:
        tool = registry.get(name)
        schema = tool.schema
        assert "name" in schema, f"工具 {name} 缺少 name"
        assert "description" in schema, f"工具 {name} 缺少 description"
        assert "parameters" in schema, f"工具 {name} 缺少 parameters"

    print(f"  ✓ 工具注册全链路通过 ({len(names)} tools)")


@pytest.mark.asyncio
async def test_react_loop_single_turn():
    """验证 ReAct Loop 单轮执行。"""
    mock_llm = MockLLMService()
    registry = ToolRegistry()
    registry.register(MockMarketTool())

    trace = ExecutionTrace(
        trace_id=f"smoke_{int(time.time() * 1000)}",
        cid=0, mid=0,
        user_message="市场怎么样",
        route="market",
    )

    loop = ReActAgentLoop(
        llm_service=mock_llm,
        system_prompt="你是一个市场助手。",
        registry=registry,
        max_turns=3,
        trace=trace,
    )

    history = [{"role": "user", "content": "市场怎么样"}]

    full_response = ""
    async for chunk in loop.run_stream("市场怎么样", history=history):
        full_response += chunk

    assert len(full_response) > 0, "无回复内容"

    print(f"  ✓ ReAct Loop 单轮通过 (response_len={len(full_response)})")


@pytest.mark.asyncio
async def test_react_loop_with_trace():
    """验证 ReAct Loop 正确记录 ExecutionTrace。"""
    mock_llm = MockLLMService()
    registry = ToolRegistry()
    registry.register(MockMarketTool())

    trace = ExecutionTrace(
        trace_id=f"smoke_trace_{int(time.time() * 1000)}",
        cid=99, mid=1,
        user_message="测试 trace",
        route="chat",
        started_at=time.time(),
    )

    loop = ReActAgentLoop(
        llm_service=mock_llm,
        system_prompt="你是一个助手。",
        registry=registry,
        max_turns=3,
        trace=trace,
    )

    full_response = ""
    async for chunk in loop.run_stream("测试 trace", history=[]):
        full_response += chunk

    trace.finished_at = time.time()

    # 验证 trace 数据完整性
    assert len(trace.turns) >= 1

    # 保存到 trace store
    trace_store.save(trace)

    # 验证可查询
    fetched = trace_store.get_by_trace_id(trace.trace_id)
    assert fetched is not None, "trace 未保存到 store"
    assert fetched["trace_id"] == trace.trace_id

    # 验证会话查询
    session_traces = trace_store.get_by_session(cid=99)
    assert len(session_traces) >= 1, "session trace 查询为空"

    print("  ✓ Trace 记录全链路通过")


def test_memory_bridge_store_recall():
    """验证 Memory Bridge 存储和召回。"""
    # 使用唯一内容避免去重
    import uuid
    unique_id = str(uuid.uuid4())[:8]

    entries = [
        MemoryEntry(id="", category="user_preference", content=f"偏好低风险投资_{unique_id}"),
        MemoryEntry(id="", category="fact", content=f"用户持有贵州茅台_{unique_id}"),
        MemoryEntry(id="", category="user_preference", content=f"关注科技股_{unique_id}"),
    ]

    ids = memory_bridge.store_many(entries)
    assert len(ids) == 3, f"存储条目数不对: {len(ids)}"

    # 召回
    recalled = memory_bridge.recall_all(limit_per_category=2)
    assert len(recalled) >= 3, f"召回数量不足: {len(recalled)}"

    # 验证 prompt 格式
    lines = memory_bridge.format_for_prompt(recalled)
    assert len(lines) > 0, "prompt 格式为空"

    # 验证统计
    stats = memory_bridge.stats()
    assert stats["total"] >= 3, f"统计总数不对: {stats}"

    print(f"  ✓ Memory Bridge 存储召回通过 (total={stats['total']})")


def test_prompt_builder_injection():
    """验证 Prompt Builder 正确注入工具和记忆。"""
    tool_schemas = [{"name": "test_tool", "description": "测试工具", "parameters": {}}]
    memories = ["- 用户偏好低风险投资"]

    result = prompt_builder.build(
        route="market",
        tool_schemas=tool_schemas,
        memories=memories,
    )

    assert "test_tool" in result, "工具 schema 未注入"
    assert "低风险" in result, "记忆未注入"

    print("  ✓ Prompt Builder 注入通过")


def test_session_state_machine():
    """验证会话状态机。"""
    cid = 10001

    # 确保干净状态
    if session_state.is_running(cid):
        session_state.finish(cid)

    # idle → running
    session_state.start(cid, message_id=1)
    assert session_state.is_running(cid)

    # running → finished
    session_state.finish(cid)
    assert not session_state.is_running(cid)

    # 并发保护
    session_state.start(cid, message_id=2)
    assert session_state.is_running(cid)

    # 取消
    cancelled = session_state.cancel(cid)
    assert cancelled

    print("  ✓ Session State Machine 通过")


def test_cli_commands():
    """验证 CLI 命令端到端。"""
    from src.memory.manager import MemoryManager

    memory = MemoryManager()

    # 创建会话
    cid = memory.start_session(title="smoke_test_cli")
    assert cid is not None
    assert memory.current_cid == cid

    # 保存消息
    mid = memory.save_message(cid=cid, role="user", content="冒烟测试消息")
    assert mid is not None

    # 查询消息
    messages = memory.get_messages(cid, limit=10)
    assert len(messages) >= 1
    assert messages[-1].content == "冒烟测试消息"

    # 验证 current_cid 持久化
    cid_file = memory._current_cid_file()
    assert cid_file.exists(), "current_cid 文件不存在"
    assert cid_file.read_text().strip() == cid

    # 清理
    other_cid = memory.start_session(title="smoke_temp")
    memory._current_cid = None
    memory.delete_session(cid)
    memory.delete_session(other_cid)

    print("  ✓ CLI 命令端到端通过")


def test_observability_api():
    """验证可观测性端点逻辑（无 HTTP）。"""
    # 验证全局指标
    metrics = trace_store.get_global_metrics()
    assert "total_requests" in metrics, "全局指标缺少 total_requests"
    assert "route_distribution" in metrics, "全局指标缺少 route_distribution"

    # 验证按路由过滤
    traces = trace_store.get_traces_filtered(route="market", limit=10)
    assert isinstance(traces, list), "trace 过滤返回非列表"

    print("  ✓ 可观测性端点逻辑通过")


# ==================== 测试运行器 ====================


def run_all_smoke_tests():
    """运行所有冒烟测试。"""
    import traceback

    tests = [
        ("工具注册", test_tool_registry_full_registration),
        ("ReAct Loop 单轮", lambda: run_sync(test_react_loop_single_turn)),
        ("Trace 记录", lambda: run_sync(test_react_loop_with_trace)),
        ("Memory Bridge", test_memory_bridge_store_recall),
        ("Prompt Builder", test_prompt_builder_injection),
        ("Session State", test_session_state_machine),
        ("CLI 端到端", test_cli_commands),
        ("可观测性", test_observability_api),
    ]

    results = []
    for name, fn in tests:
        try:
            fn()
            results.append((name, True, None))
        except Exception as e:
            results.append((name, False, str(e)))
            traceback.print_exc()

    # 打印汇总
    print("\n" + "=" * 60)
    print("冒烟测试汇总")
    print("=" * 60)

    passed = sum(1 for _, ok, _ in results if ok)
    failed = sum(1 for _, ok, _ in results if not ok)

    for name, ok, err in results:
        status = "PASS" if ok else "FAIL"
        print(f"  [{status}] {name}")
        if err:
            print(f"         {err}")

    print(f"\n总计: {passed} 通过, {failed} 失败")

    if failed > 0:
        print(f"\n⚠️  {failed} 个冒烟测试失败")
        return 1
    else:
        print(f"\n✅ 所有冒烟测试通过!")
        return 0


if __name__ == "__main__":
    sys.exit(run_all_smoke_tests())

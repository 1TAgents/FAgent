"""
Memory Bridge 测试
"""
import pytest
import sys
import os
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from agents.services.memory_bridge import MemoryBridge, MemoryEntry


@pytest.fixture
def bridge():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        yield MemoryBridge(db_path=f.name)


class TestMemoryBridge:
    def test_store_and_recall(self, bridge):
        entry = MemoryEntry(
            id="test_001", category="user_preference",
            content="用户偏好A股科技板块",
        )
        bridge.store(entry)
        recalled = bridge.recall(category="user_preference")
        assert len(recalled) == 1
        assert recalled[0].content == "用户偏好A股科技板块"

    def test_recall_by_category(self, bridge):
        bridge.store(MemoryEntry(id="m1", category="user_preference", content="pref"))
        bridge.store(MemoryEntry(id="m2", category="trade_history", content="trade"))
        bridge.store(MemoryEntry(id="m3", category="user_preference", content="pref2"))

        prefs = bridge.recall(category="user_preference")
        assert len(prefs) == 2
        trades = bridge.recall(category="trade_history")
        assert len(trades) == 1

    def test_recall_limit(self, bridge):
        for i in range(20):
            bridge.store(MemoryEntry(id=f"m{i}", category="fact", content=f"fact {i}"))
        results = bridge.recall(category="fact", limit=5)
        assert len(results) == 5

    def test_recall_all(self, bridge):
        bridge.store(MemoryEntry(id="m1", category="user_preference", content="pref"))
        bridge.store(MemoryEntry(id="m2", category="trade_history", content="trade"))
        bridge.store(MemoryEntry(id="m3", category="project_context", content="proj"))
        all_m = bridge.recall_all(limit_per_category=5)
        assert len(all_m) == 3

    def test_delete(self, bridge):
        bridge.store(MemoryEntry(id="del_me", category="fact", content="to delete"))
        assert bridge.delete("del_me")
        assert bridge.recall(category="fact") == []

    def test_clear_category(self, bridge):
        for i in range(5):
            bridge.store(MemoryEntry(id=f"m{i}", category="temp", content=f"temp {i}"))
        count = bridge.clear_category("temp")
        assert count == 5
        assert bridge.recall(category="temp") == []

    def test_format_for_prompt(self, bridge):
        bridge.store(MemoryEntry(id="m1", category="user_preference", content="偏好科技股"))
        bridge.store(MemoryEntry(id="m2", category="trade_history", content="持有600519"))
        text = bridge.format_for_prompt()
        assert "【记忆上下文】" in text
        assert "科技股" in text
        assert "600519" in text

    def test_format_for_prompt_empty(self, bridge):
        assert bridge.format_for_prompt() is None

    def test_stats(self, bridge):
        bridge.store(MemoryEntry(id="m1", category="user_preference", content="p"))
        bridge.store(MemoryEntry(id="m2", category="trade_history", content="t"))
        bridge.store(MemoryEntry(id="m3", category="trade_history", content="t2"))
        stats = bridge.stats()
        assert stats["total"] == 3
        assert stats["by_category"]["trade_history"] == 2

    def test_store_many(self, bridge):
        entries = [
            MemoryEntry(id=f"m{i}", category="fact", content=f"fact {i}")
            for i in range(10)
        ]
        ids = bridge.store_many(entries)
        assert len(ids) == 10
        assert bridge.stats()["total"] == 10

    def test_memory_entry_prompt_line(self):
        e = MemoryEntry(id="x", category="user_preference", content="likes tech")
        assert "[user_preference] likes tech" in e.to_prompt_line()

"""
Context Compaction 测试
"""
import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from agents.core.compaction import ContextCompaction, compaction


def make_messages(n, pattern="alternating"):
    """生成测试消息列表。"""
    msgs = []
    for i in range(n):
        if pattern == "alternating":
            if i % 2 == 0:
                msgs.append({"role": "user", "content": f"问题{i}: 这是用户的第{i}个提问"})
            else:
                msgs.append({"role": "assistant", "content": f"这是 AI 对问题{i-1}的详细回答，包含了重要的结论和分析。"})
        elif pattern == "with_tools":
            if i % 3 == 0:
                msgs.append({"role": "user", "content": f"问题{i}"})
            elif i % 3 == 1:
                msgs.append({"role": "tool", "content": f"工具结果: 价格{i}元，涨跌幅{(i*0.5):.2f}%", "name": "get_quote"})
            else:
                msgs.append({"role": "assistant", "content": f"分析结论{i}"})
    return msgs


class TestContextCompaction:
    def setup_method(self):
        self.compactor = ContextCompaction()

    def test_no_compaction_when_under_budget(self):
        msgs = make_messages(4)
        result, summary = self.compactor.compact(msgs, max_tokens=1000)
        assert summary is None
        assert len(result) == 4

    def test_compaction_when_over_budget(self):
        msgs = make_messages(20)
        result, summary = self.compactor.compact(msgs, max_tokens=300, keep_recent=4)
        assert summary is not None
        assert "用户问" in summary or "AI说" in summary
        # 应包含摘要消息 + 最近消息
        assert len(result) < len(msgs)

    def test_preserves_recent_messages(self):
        msgs = make_messages(20)
        result, summary = self.compactor.compact(msgs, max_tokens=500, keep_recent=4)
        # 最后 4 条消息应原样保留
        assert result[-4:] == msgs[-4:]

    def test_preserves_tool_call_pair_when_recent_window_starts_with_tool_result(self):
        msgs = [
            {"role": "user", "content": "旧问题 " + ("很长 " * 200)},
            {"role": "assistant", "content": "旧回答 " + ("很长 " * 200)},
            {"role": "user", "content": "查 600519"},
            {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": "call_quote",
                        "type": "function",
                        "function": {
                            "name": "get_quote",
                            "arguments": "{\"symbol\": \"600519\"}",
                        },
                    }
                ],
            },
            {
                "role": "tool",
                "tool_call_id": "call_quote",
                "content": "600519 当前价格 1800 元",
            },
            {"role": "assistant", "content": "600519 当前价格 1800 元"},
        ]

        result, summary = self.compactor.compact(msgs, max_tokens=120, keep_recent=2)

        assert summary is not None
        assert result[-3:] == msgs[-3:]

    def test_empty_messages(self):
        result, summary = self.compactor.compact([], max_tokens=500)
        assert result == []
        assert summary is None

    def test_no_old_messages(self):
        msgs = [{"role": "user", "content": "hi"}]
        result, summary = self.compactor.compact(msgs, max_tokens=100, keep_recent=4)
        assert len(result) == 1
        assert summary is None

    def test_extraction_with_tool_results(self):
        msgs = make_messages(10, pattern="with_tools")
        summary = self.compactor._extract_summary(msgs)
        assert "工具" in summary
        assert "get_quote" in summary

    def test_extraction_limit(self):
        """测试事实过多时只取最重要的几条。"""
        msgs = make_messages(40)
        summary = self.compactor._extract_summary(msgs)
        lines = [l for l in summary.split("\n") if l]
        assert len(lines) <= 10

    def test_summary_system_message_format(self):
        msgs = make_messages(15)
        result, summary = self.compactor.compact(msgs, max_tokens=200, keep_recent=4)
        # 摘要应作为 system 消息注入
        assert result[0]["role"] == "system"
        assert "历史对话摘要" in result[0]["content"]

    def test_compaction_reduces_size(self):
        msgs = make_messages(30)
        result, _ = self.compactor.compact(msgs, max_tokens=200, keep_recent=4)
        assert len(result) < len(msgs)

    def test_recent_only_no_old(self):
        """当消息数刚好等于 keep_recent 时，不压缩。"""
        msgs = make_messages(4)
        result, summary = self.compactor.compact(msgs, max_tokens=100, keep_recent=4)
        assert summary is None
        assert len(result) == 4


class TestGlobalCompaction:
    def test_global_instance_exists(self):
        assert compaction is not None
        assert isinstance(compaction, ContextCompaction)

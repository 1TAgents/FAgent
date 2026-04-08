#!/usr/bin/env python3
"""
Memory 数据模型测试
"""

import sys
sys.path.insert(0, '<repo-root>/src')

from memory.models import RawMessage, Role, MessageStatus, MessageSummary, ToolResponse, ResponseStorage, MemoryExtraction


def test_raw_message_create():
    """测试原始消息创建"""
    msg = RawMessage(
        cid="session_001",
        mid="msg_abc123",
        role=Role.USER,
        content="测试消息",
        sequence_num=1
    )
    assert msg.cid == "session_001"
    assert msg.mid == "msg_abc123"
    assert msg.role == Role.USER
    assert msg.content == "测试消息"
    assert msg.content_hash is not None
    assert len(msg.content_hash) == 16
    print(f"✓ RawMessage 创建：{msg.mid}")


def test_raw_message_to_dict():
    """测试消息序列化"""
    msg = RawMessage(
        cid="session_001",
        mid="msg_abc123",
        role=Role.ASSISTANT,
        content="回复消息",
        sequence_num=2
    )
    data = msg.to_dict()
    assert data["cid"] == "session_001"
    assert data["role"] == "assistant"
    assert data["content"] == "回复消息"
    print("✓ RawMessage 序列化")


def test_raw_message_from_dict():
    """测试消息反序列化"""
    data = {
        "cid": "session_001",
        "mid": "msg_def456",
        "role": "user",
        "content": "从字典创建",
        "sequence_num": 3
    }
    msg = RawMessage.from_dict(data)
    assert msg.cid == "session_001"
    assert msg.mid == "msg_def456"
    assert msg.role == Role.USER
    print("✓ RawMessage 反序列化")


def test_message_summary_create():
    """测试摘要创建"""
    summary = MessageSummary(
        sid="sum_abc123",
        cid="session_001",
        summary_type="window",
        covered_mids=["msg_001", "msg_002", "msg_003"],
        start_mid="msg_001",
        end_mid="msg_003",
        message_count=3,
        summary="测试摘要内容",
        key_points=["关键点 1", "关键点 2"]
    )
    assert summary.sid == "sum_abc123"
    assert len(summary.covered_mids) == 3
    assert summary.message_count == 3
    assert summary.can_expand == True
    print(f"✓ MessageSummary 创建：{summary.sid}")


def test_message_summary_navigation():
    """测试摘要导航信息"""
    summary = MessageSummary(
        sid="sum_def456",
        cid="session_001",
        summary_type="window",
        covered_mids=["msg_001", "msg_002"],
        start_mid="msg_001",
        end_mid="msg_002",
        message_count=2,
        summary="测试"
    )
    nav = summary.to_navigation_info()
    assert "sid" in nav
    assert "message_count" in nav
    assert "can_expand" in nav
    assert nav["message_count"] == 2
    print("✓ MessageSummary 导航信息")


def test_tool_response_inline():
    """测试内联工具响应"""
    response = ToolResponse(
        rid="resp_abc123",
        cid="session_001",
        mid="msg_001",
        tool_call_id="call_001",
        tool_name="market_data",
        tool_input='{"symbol": "600519"}',
        response_size=100,
        storage_type=ResponseStorage.INLINE,
        inline_content="小响应内容",
        summary="响应摘要"
    )
    assert response.storage_type == ResponseStorage.INLINE
    assert response.inline_content == "小响应内容"
    assert response.get_full_content() == "小响应内容"
    print(f"✓ ToolResponse 内联：{response.rid}")


def test_tool_response_navigation():
    """测试工具响应导航"""
    response = ToolResponse(
        rid="resp_def456",
        cid="session_001",
        mid="msg_001",
        tool_call_id="call_001",
        tool_name="financial_report",
        tool_input='{"symbol": "600519"}',
        response_size=5000,
        storage_type=ResponseStorage.FILE,
        summary="大响应摘要"
    )
    nav = response.to_navigation_info()
    assert "tool_name" in nav
    assert "response_size" in nav
    assert nav["tool_name"] == "financial_report"
    print("✓ ToolResponse 导航信息")


def test_memory_extraction():
    """测试记忆提取"""
    extraction = MemoryExtraction(
        extraction_id="ext_abc123",
        cid="session_001",
        mid="msg_001",
        intent_type="preference",
        confidence=0.95,
        extracted_data={"risk": "medium", "holding_period": "long"},
        saved_to_longterm=True
    )
    assert extraction.intent_type == "preference"
    assert extraction.confidence == 0.95
    assert extraction.saved_to_longterm == True
    print(f"✓ MemoryExtraction: {extraction.extraction_id}")


def main():
    """运行所有测试"""
    print("运行 Memory 数据模型测试...\n")
    
    tests = [
        test_raw_message_create,
        test_raw_message_to_dict,
        test_raw_message_from_dict,
        test_message_summary_create,
        test_message_summary_navigation,
        test_tool_response_inline,
        test_tool_response_navigation,
        test_memory_extraction,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"✗ {test.__name__} 失败：{e}")
            failed += 1
        except Exception as e:
            print(f"✗ {test.__name__} 错误：{e}")
            failed += 1
    
    print(f"\n{'='*50}")
    print(f"测试完成：{passed} 通过，{failed} 失败")
    
    if failed > 0:
        sys.exit(1)
    else:
        print("✓ 所有数据模型测试通过!")
        sys.exit(0)


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""
Memory 摘要存储测试
"""

import sys
import tempfile
sys.path.insert(0, '<repo-root>/src')

from memory.storage.database import MemoryDatabase
from memory.models import MessageSummary


def test_save_summary():
    """测试保存摘要"""
    with tempfile.TemporaryDirectory() as tmpdir:
        db = MemoryDatabase(tmpdir)
        
        summary = MessageSummary(
            sid="sum_abc123",
            cid="session_001",
            summary_type="window",
            covered_mids=["msg_001", "msg_002"],
            start_mid="msg_001",
            end_mid="msg_002",
            message_count=2,
            summary="测试摘要",
            key_points=["关键点 1"]
        )
        
        db.save_summary(summary)
        
        count = db.get_table_count("summaries")
        assert count == 1
        print("✓ 保存摘要")


def test_get_summary():
    """测试获取摘要"""
    with tempfile.TemporaryDirectory() as tmpdir:
        db = MemoryDatabase(tmpdir)
        
        summary = MessageSummary(
            sid="sum_def456",
            cid="session_001",
            summary_type="window",
            covered_mids=["msg_001", "msg_002"],
            start_mid="msg_001",
            end_mid="msg_002",
            message_count=2,
            summary="测试摘要"
        )
        db.save_summary(summary)
        
        retrieved = db.get_summary("sum_def456")
        assert retrieved is not None
        assert retrieved.summary == "测试摘要"
        assert len(retrieved.covered_mids) == 2
        print("✓ 获取摘要")


def test_get_summaries_for_conversation():
    """测试获取会话摘要列表"""
    with tempfile.TemporaryDirectory() as tmpdir:
        db = MemoryDatabase(tmpdir)
        
        # 保存多个摘要
        for i in range(3):
            summary = MessageSummary(
                sid=f"sum_{i:03d}",
                cid="session_001",
                summary_type="window",
                covered_mids=[f"msg_{i*2:03d}", f"msg_{i*2+1:03d}"],
                start_mid=f"msg_{i*2:03d}",
                end_mid=f"msg_{i*2+1:03d}",
                message_count=2,
                summary=f"摘要 {i}"
            )
            db.save_summary(summary)
        
        summaries = db.get_summaries_for_conversation("session_001")
        assert len(summaries) == 3
        assert summaries[0].sid == "sum_000"
        print(f"✓ 获取会话摘要列表：{len(summaries)} 个")


def main():
    """运行所有测试"""
    print("运行 Memory 摘要存储测试...\n")
    
    tests = [
        test_save_summary,
        test_get_summary,
        test_get_summaries_for_conversation,
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
        print("✓ 所有摘要存储测试通过!")
        sys.exit(0)


if __name__ == '__main__':
    main()

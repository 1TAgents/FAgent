#!/usr/bin/env python3
"""
Memory 消息存储测试
"""

import sys
import tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'src'))

from memory.storage.database import MemoryDatabase
from memory.models import RawMessage, Role


def test_save_message():
    """测试保存消息"""
    with tempfile.TemporaryDirectory() as tmpdir:
        db = MemoryDatabase(tmpdir)
        
        msg = RawMessage(
            cid="session_001",
            mid="msg_abc123",
            role=Role.USER,
            content="测试消息",
            sequence_num=1
        )
        
        db.save_message(msg)
        
        # 验证保存
        count = db.get_table_count("raw_messages")
        assert count == 1
        print("✓ 保存消息")


def test_get_message():
    """测试获取消息"""
    with tempfile.TemporaryDirectory() as tmpdir:
        db = MemoryDatabase(tmpdir)
        
        msg = RawMessage(
            cid="session_001",
            mid="msg_abc123",
            role=Role.USER,
            content="测试消息",
            sequence_num=1
        )
        db.save_message(msg)
        
        # 获取消息
        retrieved = db.get_message("session_001", "msg_abc123")
        assert retrieved is not None
        assert retrieved.content == "测试消息"
        assert retrieved.role == Role.USER
        print("✓ 获取消息")


def test_get_messages():
    """测试获取消息列表"""
    with tempfile.TemporaryDirectory() as tmpdir:
        db = MemoryDatabase(tmpdir)
        
        # 保存多条消息
        for i in range(5):
            msg = RawMessage(
                cid="session_001",
                mid=f"msg_{i:03d}",
                role=Role.USER if i % 2 == 0 else Role.ASSISTANT,
                content=f"消息 {i}",
                sequence_num=i
            )
            db.save_message(msg)
        
        # 获取消息列表
        messages = db.get_messages("session_001", limit=10)
        assert len(messages) == 5
        assert messages[0].sequence_num == 0
        assert messages[4].sequence_num == 4
        print(f"✓ 获取消息列表：{len(messages)} 条")


def test_get_messages_pagination():
    """测试分页获取"""
    with tempfile.TemporaryDirectory() as tmpdir:
        db = MemoryDatabase(tmpdir)
        
        # 保存 10 条消息
        for i in range(10):
            msg = RawMessage(
                cid="session_001",
                mid=f"msg_{i:03d}",
                role=Role.USER,
                content=f"消息 {i}",
                sequence_num=i
            )
            db.save_message(msg)
        
        # 分页获取
        page1 = db.get_messages("session_001", start=0, limit=5)
        page2 = db.get_messages("session_001", start=5, limit=5)
        
        assert len(page1) == 5
        assert len(page2) == 5
        assert page1[0].sequence_num == 0
        assert page2[0].sequence_num == 5
        print("✓ 分页获取")


def test_delete_message():
    """测试删除消息"""
    with tempfile.TemporaryDirectory() as tmpdir:
        db = MemoryDatabase(tmpdir)
        
        msg = RawMessage(
            cid="session_001",
            mid="msg_delete",
            role=Role.USER,
            content="待删除消息",
            sequence_num=1
        )
        db.save_message(msg)
        
        # 删除
        success = db.delete_message("session_001", "msg_delete")
        assert success == True
        
        # 验证删除
        retrieved = db.get_message("session_001", "msg_delete")
        assert retrieved is None
        print("✓ 删除消息")


def test_conversation_auto_update():
    """测试会话元数据自动更新"""
    with tempfile.TemporaryDirectory() as tmpdir:
        db = MemoryDatabase(tmpdir)
        
        # 保存消息
        for i in range(3):
            msg = RawMessage(
                cid="session_001",
                mid=f"msg_{i:03d}",
                role=Role.USER,
                content=f"消息 {i}",
                sequence_num=i
            )
            db.save_message(msg)
        
        # 检查会话元数据
        count = db.get_table_count("conversations")
        assert count == 1
        print("✓ 会话元数据自动更新")


def main():
    """运行所有测试"""
    print("运行 Memory 消息存储测试...\n")
    
    tests = [
        test_save_message,
        test_get_message,
        test_get_messages,
        test_get_messages_pagination,
        test_delete_message,
        test_conversation_auto_update,
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
        print("✓ 所有消息存储测试通过!")
        sys.exit(0)


if __name__ == '__main__':
    main()

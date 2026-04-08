#!/usr/bin/env python3
"""
Memory Manager 集成测试
"""

import sys
import tempfile
sys.path.insert(0, '<repo-root>/src')

from memory.manager import MemoryManager


def test_manager_init():
    """测试 Manager 初始化"""
    with tempfile.TemporaryDirectory() as tmpdir:
        mm = MemoryManager(tmpdir)
        assert mm.db is not None
        print("✓ MemoryManager 初始化")


def test_session_management():
    """测试会话管理"""
    with tempfile.TemporaryDirectory() as tmpdir:
        mm = MemoryManager(tmpdir)
        
        # 创建会话
        cid = mm.start_session(title="测试会话")
        assert cid.startswith("session_")
        assert mm.current_cid == cid
        print(f"✓ 创建会话：{cid}")
        
        # 列出会话
        sessions = mm.list_sessions()
        assert len(sessions) == 1
        assert sessions[0]['cid'] == cid
        print(f"✓ 列出会话：{len(sessions)} 个")
        
        # 获取会话信息
        info = mm.get_session_info(cid)
        assert info['title'] == "测试会话"
        print(f"✓ 获取会话信息：{info['title']}")
        
        # 切换会话
        cid2 = mm.start_session(title="会话 2")
        assert mm.current_cid == cid2
        success = mm.switch_session(cid)
        assert success == True
        assert mm.current_cid == cid
        print("✓ 切换会话")


def test_message_operations():
    """测试消息操作"""
    with tempfile.TemporaryDirectory() as tmpdir:
        mm = MemoryManager(tmpdir)
        
        # 创建会话
        cid = mm.start_session()
        
        # 保存消息
        mid1 = mm.save_message(cid=cid, role="user", content="第一条消息")
        assert mid1.startswith("msg_")
        print(f"✓ 保存消息：{mid1}")
        
        mid2 = mm.save_message(cid=cid, role="assistant", content="回复消息")
        print(f"✓ 保存消息：{mid2}")
        
        # 获取消息
        msg = mm.get_message(cid, mid1)
        assert msg is not None
        assert msg.content == "第一条消息"
        print(f"✓ 获取消息：{msg.content}")
        
        # 获取消息列表
        messages = mm.get_messages(cid)
        assert len(messages) == 2
        print(f"✓ 获取消息列表：{len(messages)} 条")


def test_summary_operations():
    """测试摘要操作"""
    with tempfile.TemporaryDirectory() as tmpdir:
        mm = MemoryManager(tmpdir)
        
        from memory.models import MessageSummary
        
        # 创建会话和消息
        cid = mm.start_session()
        mm.save_message(cid=cid, role="user", content="消息 1")
        mm.save_message(cid=cid, role="user", content="消息 2")
        
        # 创建摘要
        summary = MessageSummary(
            sid="sum_test",
            cid=cid,
            summary_type="window",
            covered_mids=["msg_001", "msg_002"],
            start_mid="msg_001",
            end_mid="msg_002",
            message_count=2,
            summary="测试摘要"
        )
        
        # 保存摘要
        mm.save_summary(summary)
        print("✓ 保存摘要")
        
        # 获取摘要
        retrieved = mm.get_summary("sum_test")
        assert retrieved is not None
        assert retrieved.summary == "测试摘要"
        print(f"✓ 获取摘要：{retrieved.summary}")
        
        # 获取会话摘要列表
        summaries = mm.get_summaries(cid)
        assert len(summaries) == 1
        print(f"✓ 获取会话摘要列表：{len(summaries)} 个")


def main():
    """运行所有测试"""
    print("运行 Memory Manager 集成测试...\n")
    
    tests = [
        test_manager_init,
        test_session_management,
        test_message_operations,
        test_summary_operations,
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
        print("✓ 所有 Manager 集成测试通过!")
        sys.exit(0)


if __name__ == '__main__':
    main()

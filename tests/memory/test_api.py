#!/usr/bin/env python3
"""
Memory API 测试
"""

import sys
import tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'src'))

from memory.manager import MemoryManager
from memory.api import MemoryAPI
from memory.models import MessageSummary


def test_api_init():
    """测试 API 初始化"""
    with tempfile.TemporaryDirectory() as tmpdir:
        mm = MemoryManager(tmpdir)
        api = MemoryAPI(mm)
        assert api.memory == mm
        print("✓ API 初始化")


def test_level1_overview():
    """测试 Level 1 概览"""
    with tempfile.TemporaryDirectory() as tmpdir:
        mm = MemoryManager(tmpdir)
        api = MemoryAPI(mm)
        
        # 创建会话
        cid = mm.start_session()
        
        # 获取概览
        overview = api.get_conversation_overview(cid)
        assert overview["cid"] == cid
        assert overview["type"] == "overview"
        assert "summaries" in overview
        assert overview["has_raw_messages"] == True
        print("✓ Level 1 概览")


def test_level2_messages():
    """测试 Level 2 消息列表"""
    with tempfile.TemporaryDirectory() as tmpdir:
        mm = MemoryManager(tmpdir)
        api = MemoryAPI(mm)
        
        # 创建会话和消息
        cid = mm.start_session()
        mm.save_message(cid=cid, role="user", content="消息 1")
        mm.save_message(cid=cid, role="assistant", content="消息 2")
        
        # 获取消息列表
        result = api.get_conversation_messages(cid, limit=10)
        assert result["type"] == "messages"
        assert len(result["messages"]) == 2
        assert result["pagination"]["has_more"] == False
        print(f"✓ Level 2 消息列表：{len(result['messages'])} 条")


def test_level3_detail():
    """测试 Level 3 消息详情"""
    with tempfile.TemporaryDirectory() as tmpdir:
        mm = MemoryManager(tmpdir)
        api = MemoryAPI(mm)
        
        # 创建会话和消息
        cid = mm.start_session()
        mid = mm.save_message(cid=cid, role="user", content="完整消息内容")
        
        # 获取详情
        result = api.get_message_detail(cid, mid)
        assert result["type"] == "message_detail"
        assert result["message"]["content"] == "完整消息内容"
        print("✓ Level 3 消息详情")


def test_level4_tool_response():
    """测试 Level 4 工具响应"""
    with tempfile.TemporaryDirectory() as tmpdir:
        mm = MemoryManager(tmpdir)
        api = MemoryAPI(mm)
        
        # TODO: 需要实现工具响应保存
        # result = api.get_tool_response_detail("rid_test")
        print("✓ Level 4 工具响应（待实现）")


def test_level5_expand():
    """测试 Level 5 摘要展开"""
    with tempfile.TemporaryDirectory() as tmpdir:
        mm = MemoryManager(tmpdir)
        api = MemoryAPI(mm)
        
        # 创建会话、消息和摘要
        cid = mm.start_session()
        mid1 = mm.save_message(cid=cid, role="user", content="消息 1")
        mid2 = mm.save_message(cid=cid, role="user", content="消息 2")
        
        summary = MessageSummary(
            sid="sum_test",
            cid=cid,
            summary_type="window",
            covered_mids=[mid1, mid2],
            start_mid=mid1,
            end_mid=mid2,
            message_count=2,
            summary="测试摘要",
            key_points=["关键点 1"]
        )
        mm.save_summary(summary)
        
        # 展开摘要
        result = api.expand_summary("sum_test")
        assert result["type"] == "summary_expanded"
        assert len(result["covered_messages"]) == 2
        assert result["summary"]["summary"] == "测试摘要"
        print(f"✓ Level 5 摘要展开：{len(result['covered_messages'])} 条消息")


def test_search():
    """测试搜索"""
    with tempfile.TemporaryDirectory() as tmpdir:
        mm = MemoryManager(tmpdir)
        api = MemoryAPI(mm)
        
        # 创建会话和消息
        cid = mm.start_session()
        mm.save_message(cid=cid, role="user", content="贵州茅台股价多少")
        mm.save_message(cid=cid, role="assistant", content="贵州茅台当前价 1800 元")
        
        # 搜索
        result = api.search_messages(cid, "贵州茅台", limit=10)
        assert result["query"] == "贵州茅台"
        assert len(result["results"]) == 2
        assert result["total_found"] == 2
        print(f"✓ 搜索：找到 {result['total_found']} 条")


def main():
    """运行所有测试"""
    print("运行 Memory API 测试...\n")
    
    tests = [
        test_api_init,
        test_level1_overview,
        test_level2_messages,
        test_level3_detail,
        test_level4_tool_response,
        test_level5_expand,
        test_search,
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
        print("✓ 所有 API 测试通过!")
        sys.exit(0)


if __name__ == '__main__':
    main()

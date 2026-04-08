#!/usr/bin/env python3
"""
Memory ID 体系测试
"""

import sys
sys.path.insert(0, '<repo-root>/src')

from memory.ids import MemoryID, generate_cid, generate_mid, generate_sid, generate_rid


def test_generate_cid():
    """测试会话 ID 生成"""
    cid = generate_cid()
    assert cid.startswith("session_")
    assert len(cid) > 20
    print(f"✓ generate_cid: {cid}")


def test_generate_mid():
    """测试消息 ID 生成"""
    mid = generate_mid()
    assert mid.startswith("msg_")
    assert len(mid) == 16
    print(f"✓ generate_mid: {mid}")


def test_generate_sid():
    """测试摘要 ID 生成"""
    sid = generate_sid()
    assert sid.startswith("sum_")
    assert len(sid) == 16
    print(f"✓ generate_sid: {sid}")


def test_generate_rid():
    """测试工具响应 ID 生成"""
    rid = generate_rid()
    assert rid.startswith("resp_")
    assert len(rid) == 17
    print(f"✓ generate_rid: {rid}")


def test_memory_id_new_message():
    """测试消息 ID 创建"""
    msg_id = MemoryID.new_message("session_001")
    assert msg_id.cid == "session_001"
    assert msg_id.mid.startswith("msg_")
    assert msg_id.sid is None
    assert msg_id.rid is None
    assert msg_id.is_message()
    print(f"✓ new_message: {msg_id}")


def test_memory_id_new_summary():
    """测试摘要 ID 创建"""
    sum_id = MemoryID.new_summary("session_001", "msg_abc123")
    assert sum_id.cid == "session_001"
    assert sum_id.mid == "msg_abc123"
    assert sum_id.sid.startswith("sum_")
    assert sum_id.is_summary()
    print(f"✓ new_summary: {sum_id}")


def test_memory_id_new_response():
    """测试工具响应 ID 创建"""
    resp_id = MemoryID.new_response("session_001", "market_data")
    assert resp_id.cid == "session_001"
    assert resp_id.mid.startswith("tool_market_data_")
    assert resp_id.rid.startswith("resp_")
    assert resp_id.is_response()
    print(f"✓ new_response: {resp_id}")


def test_memory_id_to_string():
    """测试 ID 格式化"""
    msg_id = MemoryID.new_message("session_001")
    id_str = str(msg_id)
    assert id_str.startswith("session_001:msg_")
    print(f"✓ to_string: {id_str}")
    
    sum_id = MemoryID.new_summary("session_001", "msg_abc123")
    id_str = str(sum_id)
    assert id_str.startswith("session_001:msg_abc123:sum_")
    print(f"✓ to_string (summary): {id_str}")


def test_memory_id_parse():
    """测试 ID 解析"""
    # 解析消息 ID
    msg_id = MemoryID.parse("session_001:msg_abc123")
    assert msg_id.cid == "session_001"
    assert msg_id.mid == "msg_abc123"
    assert msg_id.sid is None
    assert msg_id.rid is None
    
    # 解析摘要 ID
    sum_id = MemoryID.parse("session_001:msg_abc123:sum_def456")
    assert sum_id.cid == "session_001"
    assert sum_id.mid == "msg_abc123"
    assert sum_id.sid == "sum_def456"
    
    # 解析工具响应 ID
    resp_id = MemoryID.parse("session_001:msg_abc123:sum_def456:resp_xyz789")
    assert resp_id.cid == "session_001"
    assert resp_id.mid == "msg_abc123"
    assert resp_id.sid == "sum_def456"
    assert resp_id.rid == "resp_xyz789"
    
    print("✓ parse: 所有格式解析正确")


def test_memory_id_invalid():
    """测试无效 ID 解析"""
    try:
        MemoryID.parse("invalid")
        assert False, "应该抛出异常"
    except ValueError:
        print("✓ invalid: 正确抛出异常")


def main():
    """运行所有测试"""
    print("运行 Memory ID 体系测试...\n")
    
    tests = [
        test_generate_cid,
        test_generate_mid,
        test_generate_sid,
        test_generate_rid,
        test_memory_id_new_message,
        test_memory_id_new_summary,
        test_memory_id_new_response,
        test_memory_id_to_string,
        test_memory_id_parse,
        test_memory_id_invalid,
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
        print("✓ 所有 ID 体系测试通过!")
        sys.exit(0)


if __name__ == '__main__':
    main()

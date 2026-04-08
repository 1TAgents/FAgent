#!/usr/bin/env python3
"""
Memory 数据库测试
"""

import sys
import tempfile
sys.path.insert(0, '<repo-root>/src')

from memory.storage.database import MemoryDatabase


def test_database_init():
    """测试数据库初始化"""
    with tempfile.TemporaryDirectory() as tmpdir:
        db = MemoryDatabase(tmpdir)
        assert db.db_path.exists()
        print(f"✓ 数据库初始化：{db.db_path}")


def test_tables_created():
    """测试表创建"""
    with tempfile.TemporaryDirectory() as tmpdir:
        db = MemoryDatabase(tmpdir)
        
        expected_tables = [
            "raw_messages",
            "summaries",
            "tool_responses",
            "conversations",
            "memory_extractions"
        ]
        
        for table in expected_tables:
            assert db.table_exists(table), f"表 {table} 不存在"
        
        print(f"✓ 所有表已创建：{expected_tables}")


def test_get_tables():
    """测试获取表列表"""
    with tempfile.TemporaryDirectory() as tmpdir:
        db = MemoryDatabase(tmpdir)
        tables = db.get_tables()
        assert len(tables) == 5
        print(f"✓ 表列表：{tables}")


def test_table_count():
    """测试表记录数"""
    with tempfile.TemporaryDirectory() as tmpdir:
        db = MemoryDatabase(tmpdir)
        
        # 新数据库应该都是 0 条记录
        for table in ["raw_messages", "summaries", "tool_responses"]:
            count = db.get_table_count(table)
            assert count == 0, f"表 {table} 应该有 0 条记录"
        
        print("✓ 表记录数初始为 0")


def main():
    """运行所有测试"""
    print("运行 Memory 数据库测试...\n")
    
    tests = [
        test_database_init,
        test_tables_created,
        test_get_tables,
        test_table_count,
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
        print("✓ 所有数据库测试通过!")
        sys.exit(0)


if __name__ == '__main__':
    main()

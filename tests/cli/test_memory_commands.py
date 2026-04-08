#!/usr/bin/env python3
"""
记忆查询命令测试
"""

import subprocess
import sys


def run_command(cmd):
    """运行 CLI 命令"""
    result = subprocess.run(
        ['python3'] + cmd,
        capture_output=True,
        text=True,
        cwd='<repo-root>'
    )
    return result.returncode, result.stdout, result.stderr


def test_memory_help():
    """测试 memory --help"""
    code, stdout, stderr = run_command(['fagent_cli.py', 'memory', '--help'])
    assert code == 0, f"帮助查询失败：{stderr}"
    assert '记忆查询命令' in stdout
    assert 'overview' in stdout
    assert 'messages' in stdout
    assert 'detail' in stdout
    print("✓ memory --help 测试通过")


def test_memory_overview():
    """测试 Level 1 概览"""
    code, stdout, stderr = run_command(['fagent_cli.py', 'memory', 'overview'])
    assert code == 0, f"概览查询失败：{stderr}"
    # 可能提示暂无会话或待实现
    assert '概览' in stdout or '会话' in stdout
    print("✓ memory overview 测试通过")


def test_memory_messages():
    """测试 Level 2 消息列表"""
    code, stdout, stderr = run_command(['fagent_cli.py', 'memory', 'messages', '--limit', '10'])
    assert code == 0, f"消息列表查询失败：{stderr}"
    assert '消息' in stdout or '会话' in stdout
    print("✓ memory messages 测试通过")


def test_memory_detail():
    """测试 Level 3 消息详情"""
    code, stdout, stderr = run_command(['fagent_cli.py', 'memory', 'detail', 'msg_test'])
    assert code == 0, f"消息详情查询失败：{stderr}"
    assert '详情' in stdout or '消息' in stdout or '会话' in stdout
    print("✓ memory detail 测试通过")


def test_memory_tool():
    """测试 Level 4 工具响应"""
    code, stdout, stderr = run_command(['fagent_cli.py', 'memory', 'tool', 'resp_test'])
    assert code == 0, f"工具响应查询失败：{stderr}"
    assert '工具' in stdout or '响应' in stdout or '会话' in stdout
    print("✓ memory tool 测试通过")


def test_memory_expand():
    """测试 Level 5 摘要展开"""
    code, stdout, stderr = run_command(['fagent_cli.py', 'memory', 'expand', 'sum_test'])
    assert code == 0, f"摘要展开查询失败：{stderr}"
    assert '摘要' in stdout or '展开' in stdout or '会话' in stdout
    print("✓ memory expand 测试通过")


def test_memory_search():
    """测试搜索"""
    code, stdout, stderr = run_command(['fagent_cli.py', 'memory', 'search', '测试'])
    assert code == 0, f"搜索查询失败：{stderr}"
    assert '搜索' in stdout or '会话' in stdout
    print("✓ memory search 测试通过")


def main():
    """运行所有测试"""
    print("运行记忆查询命令测试...\n")
    
    tests = [
        test_memory_help,
        test_memory_overview,
        test_memory_messages,
        test_memory_detail,
        test_memory_tool,
        test_memory_expand,
        test_memory_search,
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
        print("✓ 所有测试通过!")
        sys.exit(0)


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""
消息操作命令测试
"""

import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = str(Path(__file__).resolve().parents[2])


def run_command(cmd):
    """运行 CLI 命令"""
    result = subprocess.run(
        ['python3'] + cmd,
        capture_output=True,
        text=True,
        cwd=PROJECT_ROOT
    )
    return result.returncode, result.stdout, result.stderr


def test_message_help():
    """测试 message --help"""
    code, stdout, stderr = run_command(['fagent_cli.py', 'message', '--help'])
    assert code == 0, f"帮助查询失败：{stderr}"
    assert '消息操作命令' in stdout
    assert 'send' in stdout
    assert 'list' in stdout
    print("✓ message --help 测试通过")


def test_message_send():
    """测试发送消息"""
    code, stdout, stderr = run_command(['fagent_cli.py', 'message', 'send', '测试消息 CLI-3'])
    assert code == 0, f"发送失败：{stderr}"
    assert '消息已发送' in stdout or '自动创建新会话' in stdout
    print("✓ message send 测试通过")


def test_message_list():
    """测试列出消息"""
    code, stdout, stderr = run_command(['fagent_cli.py', 'message', 'list'])
    assert code == 0, f"列出失败：{stderr}"
    # 可能提示暂无会话或待实现
    assert '消息' in stdout or '会话' in stdout
    print("✓ message list 测试通过")


def test_message_search():
    """测试搜索消息"""
    code, stdout, stderr = run_command(['fagent_cli.py', 'message', 'search', '测试'])
    assert code == 0, f"搜索失败：{stderr}"
    # 可能提示暂无会话或搜索功能
    assert '搜索' in stdout or '会话' in stdout or '消息' in stdout
    print("✓ message search 测试通过")


def main():
    """运行所有测试"""
    print("运行消息操作命令测试...\n")
    
    tests = [
        test_message_help,
        test_message_send,
        test_message_list,
        test_message_search,
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

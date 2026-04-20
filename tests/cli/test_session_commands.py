#!/usr/bin/env python3
"""
会话管理命令测试
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


def test_session_new():
    """测试创建会话"""
    code, stdout, stderr = run_command(['fagent_cli.py', 'session', 'new', '--title', '测试 CLI-2'])
    assert code == 0, f"创建失败：{stderr}"
    assert '创建新会话成功' in stdout
    print("✓ session new 测试通过")
    return stdout  # 返回输出用于提取 CID


def test_session_list():
    """测试列出会话"""
    code, stdout, stderr = run_command(['fagent_cli.py', 'session', 'list'])
    assert code == 0, f"列出失败：{stderr}"
    assert '会话列表' in stdout or '暂无会话' in stdout
    print("✓ session list 测试通过")


def test_session_info():
    """测试会话信息"""
    # 需要先创建一个会话并获取 CID
    code, stdout, stderr = run_command(['fagent_cli.py', 'session', 'new', '--title', 'Info 测试'])
    assert code == 0
    
    # 提取 CID
    import re
    match = re.search(r'CID: (session_\S+)', stdout)
    if match:
        cid = match.group(1)
        code, stdout, stderr = run_command(['fagent_cli.py', 'session', 'info', cid])
        assert code == 0, f"查询失败：{stderr}"
        assert 'CID:' in stdout
    
    print("✓ session info 测试通过")


def test_session_switch():
    """测试切换会话"""
    # 创建会话
    code, stdout, stderr = run_command(['fagent_cli.py', 'session', 'new', '--title', 'Switch 测试'])
    assert code == 0
    
    # 提取 CID
    import re
    match = re.search(r'CID: (session_\S+)', stdout)
    if match:
        cid = match.group(1)
        code, stdout, stderr = run_command(['fagent_cli.py', 'session', 'switch', cid])
        assert code == 0, f"切换失败：{stderr}"
        assert '已切换到会话' in stdout
    
    print("✓ session switch 测试通过")


def main():
    """运行所有测试"""
    print("运行会话管理命令测试...\n")
    
    tests = [
        test_session_new,
        test_session_list,
        test_session_info,
        test_session_switch,
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

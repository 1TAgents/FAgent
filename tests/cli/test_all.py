#!/usr/bin/env python3
"""
CLI 全部命令测试
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


def test_all_commands():
    """测试所有 CLI 命令"""
    print("测试所有 CLI 命令...\n")
    
    commands = [
        # 基础命令
        (['fagent_cli.py', '--help'], "主帮助"),
        (['fagent_cli.py', '--version'], "版本号"),
        (['fagent_cli.py', 'hello'], "hello 测试"),
        
        # 会话命令
        (['fagent_cli.py', 'session', '--help'], "session 帮助"),
        (['fagent_cli.py', 'session', 'new'], "session new"),
        (['fagent_cli.py', 'session', 'list'], "session list"),
        
        # 消息命令
        (['fagent_cli.py', 'message', '--help'], "message 帮助"),
        (['fagent_cli.py', 'message', 'send', '测试'], "message send"),
        (['fagent_cli.py', 'message', 'list'], "message list"),
        
        # 记忆命令
        (['fagent_cli.py', 'memory', '--help'], "memory 帮助"),
        (['fagent_cli.py', 'memory', 'overview'], "memory overview"),
        (['fagent_cli.py', 'memory', 'messages'], "memory messages"),

        # 诊断命令
        (['fagent_cli.py', 'doctor', '--help'], "doctor 帮助"),
        (['fagent_cli.py', 'doctor', 'security-scan'], "doctor security-scan"),

        # 测试命令
        (['fagent_cli.py', 'test', '--help'], "test 帮助"),
        (['fagent_cli.py', 'test', 'session'], "test session"),
    ]
    
    passed = 0
    failed = 0
    
    for cmd, name in commands:
        code, stdout, stderr = run_command(cmd)
        
        if code == 0:
            print(f"✓ {name}")
            passed += 1
        else:
            print(f"✗ {name}: {stderr[:100]}")
            failed += 1
    
    print(f"\n{'='*50}")
    print(f"测试完成：{passed} 通过，{failed} 失败")
    
    if failed > 0:
        raise AssertionError(f"{failed} CLI commands failed")
    else:
        print("✓ 所有 CLI 命令测试通过!")


if __name__ == '__main__':
    test_all_commands()

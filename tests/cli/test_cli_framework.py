#!/usr/bin/env python3
"""
CLI 框架测试
"""

import subprocess
import sys


def test_help():
    """测试 --help 命令"""
    result = subprocess.run(
        ['python3', 'fagent_cli.py', '--help'],
        capture_output=True,
        text=True
    )
    assert result.returncode == 0
    assert 'FAgent CLI' in result.stdout
    assert '--version' in result.stdout
    assert '--help' in result.stdout
    print("✓ --help 测试通过")


def test_version():
    """测试 --version 命令"""
    result = subprocess.run(
        ['python3', 'fagent_cli.py', '--version'],
        capture_output=True,
        text=True
    )
    assert result.returncode == 0
    assert '0.1.0' in result.stdout
    print("✓ --version 测试通过")


def test_hello():
    """测试 hello 命令"""
    result = subprocess.run(
        ['python3', 'fagent_cli.py', 'hello'],
        capture_output=True,
        text=True
    )
    assert result.returncode == 0
    assert '欢迎使用 FAgent CLI' in result.stdout
    print("✓ hello 命令测试通过")


def main():
    """运行所有测试"""
    print("运行 CLI 框架测试...\n")
    
    tests = [
        test_help,
        test_version,
        test_hello,
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

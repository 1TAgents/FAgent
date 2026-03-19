#!/usr/bin/env python3
"""
RQSDK 最简单测试 - 仅验证导入和版本
"""
import sys

print("=" * 70)
print("RQSDK 安装验证")
print("=" * 70)

# 测试 1: 导入
print("\n1. 测试导入 rqdatac...")
try:
    import rqdatac
    print(f"✓ 导入成功")
    print(f"  版本：{rqdatac.__version__}")
except Exception as e:
    print(f"✗ 导入失败：{e}")
    sys.exit(1)

# 测试 2: 检查 License 配置
print("\n2. 检查 License 配置...")
try:
    # 尝试获取已保存的 token
    token = rqdatac.get_token()
    if token:
        print(f"✓ 已配置 License")
        print(f"  Token 前缀：{token[:20]}...")
    else:
        print(f"⚠ 未配置 License")
        print(f"  请运行：rqdatac set <your_license_key>")
except Exception as e:
    print(f"✗ 检查失败：{e}")

# 测试 3: 尝试初始化
print("\n3. 尝试初始化...")
try:
    import rqdatac as rq
    rq.init()
    print(f"✓ 初始化成功")
    print(f"  可以开始使用 RQSDK 了！")
except Exception as e:
    print(f"✗ 初始化失败：{e}")
    print(f"\n解决方案:")
    print(f"  1. 配置 License: rqdatac set <your_license_key>")
    print(f"  2. 检查网络连接")
    print(f"  3. 联系米筐技术支持：support@ricequant.com")

print("\n" + "=" * 70)
print("验证完成！")
print("=" * 70)

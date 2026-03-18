#!/usr/bin/env python3
"""
模块化架构测试脚本

测试股票/期货模块和路由功能
"""
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from router.main_router import MainRouter


def test_router():
    """测试路由器"""
    print("=" * 60)
    print("测试 MainRouter")
    print("=" * 60)
    
    router = MainRouter()
    
    # 测试 1: 获取模块信息
    print("\n1. 获取模块信息:")
    info = router.get_module_info()
    print(f"   股票：{info['stock']['display_name']}")
    print(f"   期货：{info['future']['display_name']}")
    
    # 测试 2: 路由到股票
    print("\n2. 测试股票路由:")
    result = router.process("帮我看看茅台行情", mode="stock")
    print(f"   模式：{result['mode']}")
    print(f"   回复：{result['reply']}")
    print(f"   建议：{result.get('suggestions', [])}")
    
    # 测试 3: 路由到期货
    print("\n3. 测试期货路由:")
    result = router.process("沪深 300 股指期货走势", mode="future")
    print(f"   模式：{result['mode']}")
    print(f"   回复：{result['reply']}")
    print(f"   建议：{result.get('suggestions', [])}")
    
    # 测试 4: 自动识别（期货关键词）
    print("\n4. 测试自动识别（期货）:")
    test_messages = [
        "IF2403 主力合约怎么样",
        "螺纹钢期货走势",
        "原油价格",
    ]
    
    for msg in test_messages:
        result = router.process(msg, mode=None)
        print(f"   消息：{msg[:20]:20s} → 识别为：{result['mode']}")
    
    # 测试 5: 自动识别（默认股票）
    print("\n5. 测试自动识别（默认股票）:")
    test_messages = [
        "茅台行情",
        "平安银行怎么样",
        "宁德时代走势",
    ]
    
    for msg in test_messages:
        result = router.process(msg, mode=None)
        print(f"   消息：{msg[:20]:20s} → 识别为：{result['mode']}")
    
    print("\n" + "=" * 60)
    print("✓ 所有测试完成")
    print("=" * 60)


def test_stock_module():
    """测试股票模块"""
    print("\n" + "=" * 60)
    print("测试 StockModule")
    print("=" * 60)
    
    from modules.stock.api import StockModule
    
    module = StockModule()
    
    print(f"\n模块名称：{module.module_name}")
    print(f"显示名称：{module.display_name}")
    
    # 测试查询行情（需要数据库有数据）
    print("\n查询行情:")
    try:
        quote = module.query_quote("600519")
        print(f"   贵州茅台：{quote}")
    except Exception as e:
        print(f"   ✗ 查询失败：{e}")
    
    # 测试查询 K 线
    print("\n查询 K 线:")
    try:
        klines = module.query_klines(
            symbol="600519",
            period="daily",
            start_date="2024-01-01",
            end_date="2024-12-31",
            limit=5
        )
        print(f"   返回 {len(klines)} 条数据")
        if klines:
            print(f"   第一条：{klines[0]}")
    except Exception as e:
        print(f"   ✗ 查询失败：{e}")


def test_future_module():
    """测试期货模块"""
    print("\n" + "=" * 60)
    print("测试 FutureModule")
    print("=" * 60)
    
    from modules.future.api import FutureModule
    
    module = FutureModule()
    
    print(f"\n模块名称：{module.module_name}")
    print(f"显示名称：{module.display_name}")
    
    # 测试查询行情（需要数据库有数据）
    print("\n查询行情:")
    try:
        quote = module.query_quote("IF2403")
        print(f"   IF2403: {quote}")
    except Exception as e:
        print(f"   ✗ 查询失败：{e}")
    
    # 测试查询主力合约 K 线
    print("\n查询主力合约 K 线:")
    try:
        klines = module.query_klines(
            symbol="IF",  # 主力合约
            period="daily",
            start_date="2024-01-01",
            end_date="2024-12-31",
            limit=5
        )
        print(f"   返回 {len(klines)} 条数据")
        if klines:
            print(f"   第一条：{klines[0]}")
    except Exception as e:
        print(f"   ✗ 查询失败：{e}")


def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("FAgent 模块化架构测试")
    print("=" * 60)
    
    try:
        # 测试路由器
        test_router()
        
        # 测试股票模块
        test_stock_module()
        
        # 测试期货模块
        test_future_module()
        
        print("\n" + "=" * 60)
        print("✅ 所有测试完成！")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ 测试失败：{e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

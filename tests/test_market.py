"""
Market SubAgent 测试脚本

测试行情数据服务和 Market SubAgent
"""

import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_market_service():
    """测试 Market Service"""
    print("\n" + "=" * 60)
    print("测试 Market Service")
    print("=" * 60)
    
    from agents.common.market import market_service
    
    # 测试 A 股行情
    print("\n1. 测试 A 股行情 (600519 贵州茅台)")
    quote = market_service.get_quote("600519")
    if quote:
        print(f"   ✅ 成功: {quote.summary()}")
    else:
        print("   ❌ 失败: 未获取到数据")
    
    # 测试 K 线
    print("\n2. 测试 A 股日 K 线 (600519)")
    from agents.common.market import KLinePeriod
    kline = market_service.get_kline("600519", KLinePeriod.DAILY, 10)
    if kline:
        print(f"   ✅ 成功: 获取 {len(kline.data)} 条数据")
        print(f"   {kline.summary()}")
    else:
        print("   ❌ 失败: 未获取到数据")
    
    # 测试搜索
    print("\n3. 测试股票搜索 (茅台)")
    results = market_service.search("茅台", limit=5)
    if results:
        print(f"   ✅ 成功: 找到 {len(results)} 条结果")
        for r in results[:3]:
            print(f"      - {r.name} ({r.symbol})")
    else:
        print("   ❌ 失败: 未找到结果")
    
    # # 测试美股
    # print("\n4. 测试美股行情 (AAPL)")
    # quote_us = market_service.get_quote("AAPL")
    # if quote_us:
    #     print(f"   ✅ 成功: {quote_us.summary()}")
    # else:
    #     print("   ⚠️ 跳过: 美股数据可能需要市场开盘")


def test_market_subagent():
    """测试 Market SubAgent"""
    print("\n" + "=" * 60)
    print("测试 Market SubAgent")
    print("=" * 60)
    
    from agents.subagents import market_subagent
    from agents.subagents.market_agent import MarketQuery, MarketIntent
    
    # 测试行情查询
    print("\n1. 测试行情查询 (000001 平安银行)")
    query = MarketQuery(
        intent=MarketIntent.GET_QUOTE,
        symbol="000001",
    )
    result = market_subagent.process(query)
    print(f"   成功: {result.success}")
    print(f"   摘要: {result.summary}")
    
    # 测试趋势分析
    print("\n2. 测试趋势分析 (600519)")
    query = MarketQuery(
        intent=MarketIntent.ANALYZE_TREND,
        symbol="600519",
        count=30,
    )
    result = market_subagent.process(query)
    print(f"   成功: {result.success}")
    print(f"   摘要: {result.summary}")
    
    # 测试快捷方法
    print("\n3. 测试快捷方法")
    print(f"   quick_quote: {market_subagent.quick_quote('600519')}")


def test_api():
    """测试 API（需要先启动服务）"""
    print("\n" + "=" * 60)
    print("测试 API（确保 agents 服务已启动在 8001 端口）")
    print("=" * 60)
    
    import httpx
    
    base_url = "http://localhost:8001"
    
    try:
        # 健康检查
        resp = httpx.get(f"{base_url}/health", timeout=5)
        if resp.status_code != 200:
            print("   ⚠️ 服务未启动，跳过 API 测试")
            return
        
        print("\n1. 测试 GET /market/quote/600519")
        resp = httpx.get(f"{base_url}/market/quote/600519")
        data = resp.json()
        print(f"   成功: {data.get('success')}")
        print(f"   摘要: {data.get('summary')}")
        
        print("\n2. 测试 GET /market/kline/600519?count=5")
        resp = httpx.get(f"{base_url}/market/kline/600519?count=5")
        data = resp.json()
        print(f"   成功: {data.get('success')}")
        print(f"   数据条数: {len(data.get('data', {}).get('data', []))}")
        
        print("\n3. 测试 GET /market/search?keyword=银行")
        resp = httpx.get(f"{base_url}/market/search?keyword=银行&limit=3")
        data = resp.json()
        print(f"   成功: {data.get('success')}")
        print(f"   结果数: {len(data.get('results', []))}")
        
        print("\n4. 测试 GET /market/analysis/600519")
        resp = httpx.get(f"{base_url}/market/analysis/600519")
        data = resp.json()
        print(f"   成功: {data.get('success')}")
        print(f"   摘要: {data.get('summary')}")
        
    except httpx.ConnectError:
        print("   ⚠️ 无法连接到服务，请先启动 agents 服务:")
        print("   uvicorn agents.api.main:app --reload --port 8001")


if __name__ == "__main__":
    print("FAgent Market 测试")
    print("=" * 60)
    
    # 选择测试模式
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--api", action="store_true", help="测试 API（需要服务运行）")
    parser.add_argument("--all", action="store_true", help="运行所有测试")
    args = parser.parse_args()
    
    if args.api:
        test_api()
    elif args.all:
        test_market_service()
        test_market_subagent()
        test_api()
    else:
        # 默认只测试本地模块
        test_market_service()
        test_market_subagent()
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)


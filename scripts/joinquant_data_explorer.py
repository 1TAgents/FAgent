#!/usr/bin/env python3
"""
聚宽 (JoinQuant) 数据接口探索

评估聚宽有哪些数据，哪些对 FAgent 有价值
"""
import jqdatasdk as jq
import pandas as pd
import sys
from datetime import datetime

# 聚宽账号配置（从环境变量读取更安全）
JQ_USER = "your_username"  # 替换为你的聚宽账号
JQ_PASS = "your_password"  # 替换为你的聚宽密码

def init_joinquant():
    """初始化聚宽连接"""
    try:
        jq.auth(JQ_USER, JQ_PASS)
        print("✅ 聚宽登录成功")
        return True
    except Exception as e:
        print(f"❌ 聚宽登录失败：{e}")
        print("\n请在脚本中配置正确的聚宽账号密码")
        return False

def explore_data_types():
    """探索聚宽支持的数据类型"""
    print("\n" + "="*70)
    print("聚宽数据类型探索")
    print("="*70)
    
    # 1. 股票数据
    print("\n📈 1. 股票数据")
    print("-" * 50)
    
    # 获取股票列表
    try:
        stocks = jq.get_all_securities(types=['stock'], date=datetime.now())
        print(f"   - A 股股票数量：{len(stocks)}")
        print(f"   - 字段：{list(stocks.columns)}")
        print(f"   - 示例：{stocks.head(3)}")
    except Exception as e:
        print(f"   ❌ 获取失败：{e}")
    
    # 2. 指数数据
    print("\n📊 2. 指数数据")
    print("-" * 50)
    try:
        indices = jq.get_all_securities(types=['index'], date=datetime.now())
        print(f"   - 指数数量：{len(indices)}")
        print(f"   - 示例：{indices.head(5)}")
    except Exception as e:
        print(f"   ❌ 获取失败：{e}")
    
    # 3. 基金数据
    print("\n💰 3. 基金数据")
    print("-" * 50)
    try:
        funds = jq.get_all_securities(types=['fund'], date=datetime.now())
        print(f"   - 基金数量：{len(funds)}")
    except Exception as e:
        print(f"   ❌ 获取失败：{e}")
    
    # 4. 期货数据
    print("\n🔮 4. 期货数据")
    print("-" * 50)
    try:
        futures = jq.get_all_securities(types=['futures'], date=datetime.now())
        print(f"   - 期货合约数量：{len(futures)}")
        print(f"   - 示例：{futures.head(5)}")
    except Exception as e:
        print(f"   ❌ 获取失败：{e}")
    
    # 5. K 线数据测试
    print("\n📉 5. K 线数据测试")
    print("-" * 50)
    try:
        # 日线
        df_daily = jq.get_price('000001.XSHE', start_date='2026-03-01', end_date='2026-04-03', frequency='daily')
        print(f"   - 日线数据：{len(df_daily)} 条")
        print(f"   - 字段：{list(df_daily.columns)}")
        
        # 分钟线
        df_minute = jq.get_price('000001.XSHE', start_date='2026-04-02', end_date='2026-04-03', frequency='30m')
        print(f"   - 30 分钟线：{len(df_minute)} 条")
        
        #  tick 数据
        df_tick = jq.get_price('000001.XSHE', start_date='2026-04-02', end_date='2026-04-02', frequency='tick')
        print(f"   - Tick 数据：{len(df_tick)} 条")
    except Exception as e:
        print(f"   ❌ 获取失败：{e}")
    
    # 6. 财务数据
    print("\n💵 6. 财务数据")
    print("-" * 50)
    try:
        # 资产负债表
        balance = jq.get_balance('000001.XSHE', date='2025-12-31')
        print(f"   - 资产负债表字段数：{len(balance.columns)}")
        
        # 利润表
        income = jq.get_income('000001.XSHE', date='2025-12-31')
        print(f"   - 利润表字段数：{len(income.columns)}")
        
        # 现金流量表
        cashflow = jq.get_cashflow('000001.XSHE', date='2025-12-31')
        print(f"   - 现金流量表字段数：{len(cashflow.columns)}")
    except Exception as e:
        print(f"   ❌ 获取失败：{e}")
    
    # 7. 其他数据
    print("\n📋 7. 其他数据")
    print("-" * 50)
    try:
        # 龙虎榜
        bbq = jq.get_billboard_list('000001.XSHE', end_date='2026-04-03', count=1)
        print(f"   - 龙虎榜：可用")
    except:
        print(f"   - 龙虎榜：不可用或无数据")
    
    try:
        # 股东人数
        holders = jq.get_stock_holders('000001.XSHE', end_date='2026-04-03')
        print(f"   - 股东人数：可用")
    except:
        print(f"   - 股东人数：不可用")
    
    try:
        # 北向资金
        north = jq.get_north_money_flow(start_date='2026-04-01', end_date='2026-04-03')
        print(f"   - 北向资金：可用，{len(north)} 条")
    except:
        print(f"   - 北向资金：不可用")

def evaluate_for_fagent():
    """评估对 FAgent 有价值的数据"""
    print("\n" + "="*70)
    print("🎯 对 FAgent 有价值的数据评估")
    print("="*70)
    
    recommendations = {
        "高优先级": [
            "✅ 股票日线/分钟线 K 线（核心交易数据）",
            "✅ 指数成分股及历史行情（沪深 300、中证 500 等）",
            "✅ 北向资金流向（聪明钱指标）",
            "✅ 龙虎榜数据（游资动向）",
            "✅ 股票基本信息（市值、行业、概念）",
        ],
        "中优先级": [
            "⭕ 财务数据（PE/PB、ROE 等基本面指标）",
            "⭕ 股东人数变化（筹码集中度）",
            "⭕ ETF 基金数据（资金流向参考）",
            "⭕ 期货主力合约数据（商品期货趋势）",
        ],
        "低优先级": [
            "⚪ 港股通数据（如有港股交易需求）",
            "⚪ 宏观经济数据（CPI、PPI 等）",
            "⚪ 新闻情绪数据（需要 NLP 处理）",
        ]
    }
    
    for priority, items in recommendations.items():
        print(f"\n{priority}:")
        for item in items:
            print(f"   {item}")
    
    print("\n" + "="*70)
    print("📋 推荐下载清单")
    print("="*70)
    print("""
1. 股票数据
   - 全部 A 股日线数据（2020 年至今）
   - 全部 A 股 60 分钟线数据（最近 1 年）
   - 沪深 300 + 中证 500 成分股

2. 资金流向
   - 北向资金历史数据
   - 个股资金流向（主力/散户）

3. 市场情绪
   - 龙虎榜数据（最近 1 年）
   - 涨跌停统计

4. 基本面
   - 最新财报数据（PE/PB/ROE）
   - 行业分类信息

5. 期货数据（可选）
   - 主要商品期货日线
   - 股指期货数据
    """)

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--auth":
        # 从参数获取账号密码
        if len(sys.argv) >= 4:
            JQ_USER = sys.argv[2]
            JQ_PASS = sys.argv[3]
    
    print("="*70)
    print("聚宽 (JoinQuant) 数据探索工具")
    print("="*70)
    print("\n⚠️  请先配置聚宽账号密码（编辑脚本或注册聚宽）")
    print("   注册地址：https://www.joinquant.com")
    print()
    
    # 尝试登录
    if init_joinquant():
        explore_data_types()
        evaluate_for_fagent()
    else:
        evaluate_for_fagent()

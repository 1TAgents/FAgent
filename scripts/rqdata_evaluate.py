#!/usr/bin/env python3
"""
RQData (米筐/聚宽) 数据评估工具

评估 RQData 支持的数据类型，为 FAgent 项目制定下载策略
"""
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

print("="*70)
print("RQData (米筐/聚宽) 数据评估报告")
print("="*70)

print("""
📊 RQData 数据总览
-----------------
RQData (米筐数据) 是国内领先的量化金融数据服务商，提供:

✅ 已配置 License (在 test_rqdata_quick.py 中)
⚠️  需要正确初始化才能使用

📁 支持的数据类型:
""")

data_types = {
    "行情数据": {
        "日线": "get_price(frequency='1d') - 支持 2005 年至今",
        "分钟线": "get_price(frequency='1m'/'5m'/'15m'/'30m'/'60m')",
        "Tick 数据": "get_price(frequency='tick') - 高频交易",
        "实时行情": "get_current_tick() - 实时快照",
    },
    "股票数据": {
        "A 股列表": "all_instruments(type='CS') - 全部 A 股",
        "指数成分股": "index_components() - 沪深 300/中证 500 等",
        "停牌股票": "get_suspend_list() - 停牌信息",
        "涨跌停": "get_limit_list() - 涨跌停信息",
    },
    "基金数据": {
        "ETF 列表": "all_instruments(type='ETF')",
        "LOF 基金": "all_instruments(type='LOF')",
        "分级基金": "all_instruments(type='Structured Fund')",
        "场内基金": "get_price() 支持",
    },
    "期货数据": {
        "期货合约": "all_instruments(type='Future')",
        "主力合约": "get_dominant_price() - 主力连续合约",
        "商品期货": "支持全部国内期货品种",
        "金融期货": "股指期货、国债期货",
    },
    "财务数据": {
        "估值指标": "get_fundamentals(valuation) - PE/PB/市值等",
        "资产负债表": "get_fundamentals(balanceSheet)",
        "利润表": "get_fundamentals(incomeStatement)",
        "现金流量表": "get_fundamentals(cashFlowStatement)",
    },
    "其他数据": {
        "分红送配": "get_dividends() - 分红历史",
        "股东人数": "get_share_holder_num()",
        "北向资金": "get_north_flow() - 沪深股通",
        "龙虎榜": "get_billboard_list()",
        "行业分类": "get_industry() - 申万/中信行业",
        "概念板块": "get_concept() - 主题概念",
    }
}

for category, items in data_types.items():
    print(f"\n{category}:")
    for name, desc in items.items():
        print(f"   • {name}: {desc}")

print("\n\n" + "="*70)
print("🎯 对 FAgent 有价值的数据评估")
print("="*70)

recommendations = """
高优先级 ⭐⭐⭐ (立即历史数据下载 + 每日更新):
----------------------------------------
1. A 股日线数据 (2020 年至今)
   - 用途：策略回测、趋势分析
   - 数据量：~5500 只 × 1500 天 ≈ 825 万条
   - 命令：rq.get_price(..., frequency='1d')

2. 沪深 300 + 中证 500 成分股及历史行情
   - 用途：核心资产池、指数跟踪
   - 数据量：800 只 × 1500 天 ≈ 120 万条
   - 命令：rq.index_components('000300.XSHG')

3. 北向资金流向
   - 用途：聪明钱指标、市场情绪
   - 数据量：~1500 条 (每日汇总)
   - 命令：rq.get_north_flow()

4. 龙虎榜数据 (2023 年至今)
   - 用途：游资动向、强势股追踪
   - 数据量：~50,000 条
   - 命令：rq.get_billboard_list()

5. 估值指标 (PE/PB/市值)
   - 用途：基本面选股、价值策略
   - 数据量：5500 只 × 250 交易日 ≈ 137 万条
   - 命令：rq.get_fundamentals(query(valuation))

中优先级 ⭐⭐ (按需下载):
----------------------------------------
6. A 股 60 分钟线 (最近 90 天)
   - 用途：短线交易、日内策略
   - 数据量：5500 只 × 90 天 × 4 小时 ≈ 200 万条

7. ETF 基金数据
   - 用途：资金流向参考、套利策略
   - 数据量：~300 只 ETF

8. 期货主力合约数据
   - 用途：商品趋势、通胀预期
   - 数据量：~20 品种 × 1500 天 ≈ 3 万条
   - 注：已有 AKShare 数据，可选

9. 行业指数数据
   - 用途：板块轮动分析
   - 数据量：~30 个申万一级行业

低优先级 ⭐ (暂缓):
----------------------------------------
10. Tick 数据 - 数据量太大，按需获取
11. 宏观数据 - FAgent 暂不需要
12. 新闻情绪 - 需要 NLP 处理
"""

print(recommendations)

print("\n" + "="*70)
print("📋 推荐下载策略")
print("="*70)

print("""
Phase 1: 核心数据 (预计 2-3 小时)
----------------------------------
python3 scripts/download_rqdata_basic.py

下载内容:
  ✅ A 股日线 (2010-2026) - 前复权
  ✅ 期货日线 (2020-2026)
  ✅ 财务数据 (最新报告期)
  ✅ 分红送配数据

Phase 2: 补充数据 (预计 1-2 小时)
----------------------------------
python3 scripts/download_rqdata_enhanced.py

下载内容:
  ⭕ 60 分钟线 (最近 90 天)
  ⭕ 北向资金历史
  ⭕ 龙虎榜 (2023 至今)
  ⭕ 指数成分股及历史

Phase 3: 每日增量更新 (cron 定时任务)
----------------------------------
python3 scripts/update_rqdata_daily.py

更新时间: 每个交易日 16:00
更新内容:
  - 最新日线数据
  - 北向资金
  - 龙虎榜
""")

print("\n" + "="*70)
print("⚠️  注意事项")
print("="*70)

print("""
1. License 配置
   - 已有 License (test_rqdata_quick.py)
   - 需要正确初始化：rq.init(user='xxx', password='xxx') 或使用配置文件

2. 限流控制
   - 免费版：10 次/秒，100 万单元格/天
   - 脚本已内置限流，不要删除 time.sleep()

3. 数据存储
   - 建议路径：data/rqdata/database/
   - 预计总大小：2-3GB (全部历史数据)

4. 更新策略
   - 日线：每日 15:30 后更新
   - 财务：季度更新 (财报季后)
   - 实时：按需获取

5. 与 AKShare 对比
   - RQData 优势：数据质量高、复权准确、API 稳定
   - AKShare 优势：完全免费、无需账号
   - 建议：RQData 为主，AKShare 备份
""")

print("\n" + "="*70)
print("✅ 评估完成")
print("="*70)

print("""
下一步操作:
1. 确认 RQData License 有效性
2. 运行 download_rqdata_basic.py 下载核心数据
3. 配置每日定时更新任务

相关脚本:
- scripts/test_rqdata_quick.py - 快速测试
- scripts/download_rqdata_basic.py - 基础数据下载
- scripts/test_rqdata_exploration.py - 数据能力探索
""")

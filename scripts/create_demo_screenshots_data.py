#!/usr/bin/env python3
"""
创建 Demo 截图数据 - 静态 JSON

用于 GDPS 路演 Demo 展示，不依赖真实运行
"""
import json
from pathlib import Path

# Demo 数据 1: 对话查询结果
demo_query_result = {
    "symbol": "600519",
    "name": "贵州茅台",
    "current_price": 1780.50,
    "change_percent": 2.3,
    "technical_indicators": {
        "ma20": 1750.00,
        "ma20_status": "上方，偏多",
        "rsi_14": 58,
        "rsi_status": "中性",
        "macd": "金叉第 3 天"
    },
    "capital_flow": {
        "northbound": "连续 3 日净流入",
        "main_force": "+1.2 亿"
    }
}

# Demo 数据 2: 策略回测结果
demo_backtest_result = {
    "strategy": "双均线策略",
    "symbol": "600519 贵州茅台",
    "period": "2025-03-01 至 2026-03-01",
    "params": {
        "short_period": 5,
        "long_period": 20
    },
    "metrics": {
        "initial_capital": 100000,
        "final_capital": 128500,
        "total_return": 28.5,
        "annual_return": 28.5,
        "sharpe_ratio": 1.42,
        "max_drawdown": -15.3,
        "total_trades": 12,
        "win_rate": 58,
        "profit_factor": 2.1
    },
    "trades": [
        {"entry_date": "2025-04-15", "exit_date": "2025-05-20", "entry_price": 1720, "exit_price": 1850, "pnl": 7.6},
        {"entry_date": "2025-07-10", "exit_date": "2025-08-05", "entry_price": 1680, "exit_price": 1750, "pnl": 4.2},
        {"entry_date": "2025-09-01", "exit_date": "2025-09-25", "entry_price": 1710, "exit_price": 1800, "pnl": 5.3},
        {"entry_date": "2025-10-15", "exit_date": "2025-11-10", "entry_price": 1760, "exit_price": 1720, "pnl": -2.3},
        {"entry_date": "2025-12-01", "exit_date": "2025-12-20", "entry_price": 1740, "exit_price": 1820, "pnl": 4.6},
    ],
    "equity_curve": [
        {"date": "2025-03-01", "value": 100000},
        {"date": "2025-04-01", "value": 102500},
        {"date": "2025-05-01", "value": 108200},
        {"date": "2025-06-01", "value": 106800},
        {"date": "2025-07-01", "value": 109500},
        {"date": "2025-08-01", "value": 114200},
        {"date": "2025-09-01", "value": 118600},
        {"date": "2025-10-01", "value": 116200},
        {"date": "2025-11-01", "value": 113800},
        {"date": "2025-12-01", "value": 119500},
        {"date": "2026-01-01", "value": 124300},
        {"date": "2026-02-01", "value": 126800},
        {"date": "2026-03-01", "value": 128500},
    ]
}

# Demo 数据 3: 策略库列表
demo_strategies = {
    "total": 4,
    "strategies": [
        {
            "id": "stock-dual-ma",
            "name": "双均线策略",
            "market": "股票",
            "type": "趋势跟踪",
            "description": "金叉买入，死叉卖出",
            "params": {
                "short_period": "5-10 日",
                "long_period": "20-30 日"
            },
            "suitable": "趋势明显的股票"
        },
        {
            "id": "stock-rsi",
            "name": "RSI 策略",
            "market": "股票",
            "type": "均值回归",
            "description": "超买超卖，低买高卖",
            "params": {
                "rsi_period": "14",
                "threshold": "30/70"
            },
            "suitable": "震荡市"
        },
        {
            "id": "future-dual-ma",
            "name": "双均线策略（期货）",
            "market": "期货",
            "type": "趋势跟踪",
            "description": "支持做多 + 做空双向交易",
            "params": {
                "short_period": "10 日",
                "long_period": "30 日"
            },
            "suitable": "趋势明显的期货品种"
        },
        {
            "id": "future-rsi",
            "name": "RSI 策略（期货）",
            "market": "期货",
            "type": "均值回归",
            "description": "支持做多 + 做空 + 中性平仓",
            "params": {
                "rsi_period": "14",
                "threshold": "30/70"
            },
            "suitable": "震荡市"
        }
    ]
}

# 保存文件
output_dir = Path(__file__).parent.parent / 'data' / 'demo'
output_dir.mkdir(parents=True, exist_ok=True)

with open(output_dir / 'demo_query_result.json', 'w', encoding='utf-8') as f:
    json.dump(demo_query_result, f, indent=2, ensure_ascii=False)

with open(output_dir / 'demo_backtest_result.json', 'w', encoding='utf-8') as f:
    json.dump(demo_backtest_result, f, indent=2, ensure_ascii=False)

with open(output_dir / 'demo_strategies.json', 'w', encoding='utf-8') as f:
    json.dump(demo_strategies, f, indent=2, ensure_ascii=False)

print("✅ Demo 数据已生成:")
print(f"   📁 {output_dir}/")
print(f"   📄 demo_query_result.json - 对话查询结果")
print(f"   📄 demo_backtest_result.json - 策略回测结果")
print(f"   📄 demo_strategies.json - 策略库列表")
print("\n💡 使用方式:")
print("1. 打开 JSON 文件查看数据")
print("2. 用数据制作截图（浏览器/Figma/Sketch）")
print("3. 截图插入 PPT 的 P4.5（Demo 演示页）")

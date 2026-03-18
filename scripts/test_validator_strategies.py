#!/usr/bin/env python3
"""
验证器模块测试 - 寻找年化 20%+ 的优秀策略

测试不同类型的策略，使用滚动窗口验证
直接从 SQLite 数据库加载数据
"""
import sys
from pathlib import Path

# 动态添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import pandas as pd
import numpy as np
import sqlite3
from agents.backtest.vectorized_strategies import get_vectorized_strategy
from agents.backtest.validator_engine import create_validator_engine

# 数据库路径
DB_PATH = Path(__file__).parent.parent / "data" / "stock_data.db"

# 测试的股票列表（从数据库中选择）
TEST_STOCKS = [
    ("600519", "贵州茅台"),
    ("002252", "上海莱士"),
    ("002600", "领益智造"),
    ("300589", "江龙船艇"),
    ("600026", "中远海能"),
    ("600354", "盟固利"),
    ("600508", "上海能源"),
    ("601607", "上海医药"),
]

# 测试的策略（覆盖不同类型）
TEST_STRATEGIES = [
    # 趋势型策略
    {"name": "macd", "params": {"fast_period": 12, "slow_period": 26, "signal_period": 9}},
    {"name": "dual_ma", "params": {"short_period": 10, "long_period": 50}},
    {"name": "momentum", "params": {"lookback": 20, "threshold": 0.03}},
    
    # 震荡型策略
    {"name": "rsi", "params": {"period": 14, "oversold": 30, "overbought": 70}},
    {"name": "kdj", "params": {"n": 9, "m1": 3, "m2": 3}},
    {"name": "bollinger", "params": {"period": 20, "std_dev": 2.0}},
]

# 验证器配置
VALIDATOR_CONFIG = {
    "window_size": 120,   # 6 个月训练
    "step_size": 20,      # 1 个月滚动
    "test_size": 20       # 1 个月测试
}


def load_klines_from_db(symbol: str) -> pd.DataFrame:
    """
    直接从 SQLite 数据库加载 K 线数据
    
    Returns:
        DataFrame 包含 OHLCV 数据，索引为日期
    """
    conn = sqlite3.connect(DB_PATH)
    
    query = """
    SELECT date, open, high, low, close, volume, turnover, change_percent
    FROM klines
    WHERE symbol = ?
    ORDER BY date
    """
    
    df = pd.read_sql_query(query, conn, params=(symbol,))
    conn.close()
    
    if not df.empty:
        df['date'] = pd.to_datetime(df['date'])
        df = df.set_index('date')
    
    return df


def run_strategy_validation(symbol: str, strategy_config: dict, data: pd.DataFrame) -> dict:
    """
    对单个策略执行验证
    
    Returns:
        验证结果字典
    """
    try:
        # 检查数据量
        if len(data) < VALIDATOR_CONFIG["window_size"] + VALIDATOR_CONFIG["test_size"]:
            return {
                "success": False,
                "strategy": strategy_config["name"],
                "error": f"数据量不足 ({len(data)}行)"
            }
        
        # 创建验证器引擎
        engine = create_validator_engine(
            validator_type="walk_forward",
            validator_config=VALIDATOR_CONFIG,
            initial_capital=100000.0
        )
        
        # 执行验证
        report = engine.run(
            strategy_name=strategy_config["name"],
            data=data,
            default_params=strategy_config["params"]
        )
        
        # 提取关键指标
        summary = report.summary
        overfitting = report.overfitting_analysis
        
        return {
            "success": True,
            "strategy": strategy_config["name"],
            "params": strategy_config["params"],
            "avg_annual_return": summary.get("avg_returns", 0) * 100,  # 转换为百分比
            "avg_sharpe": summary.get("avg_sharpe", 0),
            "sharpe_std": summary.get("sharpe_std", 0),
            "avg_max_drawdown": summary.get("avg_max_drawdown", 0) * 100,
            "num_rounds": summary.get("num_rounds", 0),
            "risk_level": overfitting.risk_level,
            "sharpe_consistency": overfitting.sharpe_consistency,
            "param_stability": overfitting.param_stability,
            "warnings": overfitting.warnings
        }
        
    except Exception as e:
        return {
            "success": False,
            "strategy": strategy_config["name"],
            "error": str(e)
        }


def main():
    """主函数"""
    print("\n")
    print("=" * 80)
    print(" " * 25 + "策略验证测试 - 寻找年化 20%+ 策略")
    print("=" * 80)
    print()
    
    results = []
    
    # 遍历股票和策略
    for symbol, name in TEST_STOCKS:
        print(f"\n📈 测试股票：{symbol} ({name})")
        print("-" * 60)
        
        # 加载数据
        try:
            data = load_klines_from_db(symbol)
            
            if data.empty:
                print(f"  ⚠️  无数据，跳过")
                continue
            
            print(f"  数据量：{len(data)} 行 | {data.index[0].date()} ~ {data.index[-1].date()}")
            
        except Exception as e:
            print(f"  ⚠️  加载失败：{e}")
            continue
        
        # 测试每个策略
        for strategy_config in TEST_STRATEGIES:
            result = run_strategy_validation(symbol, strategy_config, data)
            
            if result["success"]:
                # 标记年化 20%+ 的策略
                marker = "⭐" if result["avg_annual_return"] >= 20 else "  "
                print(f"  {marker} {result['strategy']:12s} | "
                      f"年化：{result['avg_annual_return']:6.1f}% | "
                      f"夏普：{result['avg_sharpe']:5.2f} | "
                      f"回撤：{result['avg_max_drawdown']:6.1f}% | "
                      f"风险：{result['risk_level']}")
                
                results.append({
                    "symbol": symbol,
                    "name": name,
                    **result
                })
            else:
                print(f"  ❌ {result['strategy']:12s} | 失败：{result.get('error', 'Unknown')}")
    
    # 汇总结果
    print("\n")
    print("=" * 80)
    print(" " * 35 + "优秀策略汇总（年化≥20%）")
    print("=" * 80)
    print()
    
    # 筛选年化 20%+ 的策略
    top_strategies = [r for r in results if r.get("avg_annual_return", 0) >= 20]
    
    if not top_strategies:
        print("⚠️  未找到年化 20%+ 的策略")
        print()
        print("可能原因：")
        print("  1. 数据时间范围太短（需要更长的历史数据）")
        print("  2. 市场整体表现不佳")
        print("  3. 策略参数需要优化")
        print()
        
        # 显示最佳策略（即使不到 20%）
        if results:
            print("最佳策略（Top 5）：")
            sorted_results = sorted(results, key=lambda x: x.get("avg_annual_return", 0), reverse=True)[:5]
            for i, r in enumerate(sorted_results, 1):
                print(f"  {i}. {r['symbol']} - {r['strategy']}: {r['avg_annual_return']:.1f}% "
                      f"(夏普：{r['avg_sharpe']:.2f}, 风险：{r['risk_level']})")
    else:
        print(f"找到 {len(top_strategies)} 个年化 20%+ 的策略：\n")
        
        # 按年化收益排序
        top_strategies.sort(key=lambda x: x["avg_annual_return"], reverse=True)
        
        # 按策略类型分组展示
        strategy_types = {
            "趋势型": ["macd", "dual_ma", "momentum"],
            "震荡型": ["rsi", "kdj", "bollinger"]
        }
        
        for type_name, strategies in strategy_types.items():
            type_results = [r for r in top_strategies if r["strategy"] in strategies]
            if type_results:
                print(f"【{type_name}】")
                for r in type_results[:3]:  # 每类最多显示 3 个
                    print(f"  ⭐ {r['symbol']} - {r['strategy']}: {r['avg_annual_return']:.1f}% | "
                          f"夏普：{r['avg_sharpe']:.2f} | "
                          f"回撤：{r['avg_max_drawdown']:.1f}% | "
                          f"风险：{r['risk_level']}")
                print()
        
        # 综合最佳
        if top_strategies:
            best = top_strategies[0]
            print("=" * 80)
            print("🏆 综合最佳策略")
            print("=" * 80)
            print(f"  股票：{best['symbol']} ({best['name']})")
            print(f"  策略：{best['strategy']}")
            print(f"  参数：{best['params']}")
            print(f"  年化收益：{best['avg_annual_return']:.1f}%")
            print(f"  夏普比率：{best['avg_sharpe']:.2f}")
            print(f"  最大回撤：{best['avg_max_drawdown']:.1f}%")
            print(f"  验证轮数：{best['num_rounds']}")
            print(f"  过拟合风险：{best['risk_level']}")
            if best['warnings']:
                print(f"  警告：{', '.join(best['warnings'])}")
    
    print()
    print("=" * 80)
    print("测试完成！")
    print("=" * 80)
    print()
    
    # 保存结果
    if results:
        output_file = Path(__file__).parent / "validation_results.csv"
        df = pd.DataFrame(results)
        df.to_csv(output_file, index=False, encoding="utf-8-sig")
        print(f"📊 结果已保存：{output_file}")
    
    return results


if __name__ == "__main__":
    main()

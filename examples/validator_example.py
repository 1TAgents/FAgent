#!/usr/bin/env python3
"""
验证器模块使用示例

展示如何使用三种验证器进行策略验证
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# 导入验证器模块
from agents.backtest.validators import (
    HoldoutValidator, WalkForwardValidator, ExpandingWindowValidator,
    create_validator
)
from agents.backtest.validator_engine import (
    ValidatorEngine, create_validator_engine
)
from agents.backtest.data_loader import get_data_loader


def create_mock_data(num_rows: int = 200) -> pd.DataFrame:
    """创建模拟 K 线数据（用于演示）"""
    dates = pd.date_range(start="2024-01-01", periods=num_rows, freq="D")
    np.random.seed(42)
    
    return pd.DataFrame({
        "open": 100 + np.cumsum(np.random.randn(num_rows) * 0.5),
        "high": 100 + np.cumsum(np.random.randn(num_rows) * 0.5) + np.abs(np.random.randn(num_rows)),
        "low": 100 + np.cumsum(np.random.randn(num_rows) * 0.5) - np.abs(np.random.randn(num_rows)),
        "close": 100 + np.cumsum(np.random.randn(num_rows) * 0.5),
        "volume": np.random.randint(1000, 10000, num_rows)
    }, index=dates)


def example_holdout_validator():
    """
    示例 1：HoldoutValidator（固定分割验证）
    
    适用场景：长期策略，参数稳定
    """
    print("=" * 60)
    print("示例 1：HoldoutValidator - 固定分割验证")
    print("=" * 60)
    
    # 1. 创建验证器
    validator = HoldoutValidator(train_ratio=0.6)
    
    # 2. 准备数据
    data = create_mock_data(200)
    
    # 3. 划分数据
    train_data, test_data = validator.split(data)
    
    print(f"总数据量：{len(data)} 行")
    print(f"训练集：{len(train_data)} 行 ({len(train_data)/len(data)*100:.0f}%)")
    print(f"测试集：{len(test_data)} 行 ({len(test_data)/len(data)*100:.0f}%)")
    print(f"训练集时间：{train_data.index[0].date()} ~ {train_data.index[-1].date()}")
    print(f"测试集时间：{test_data.index[0].date()} ~ {test_data.index[-1].date()}")
    print()


def example_walk_forward_validator():
    """
    示例 2：WalkForwardValidator（滚动窗口验证）
    
    适用场景：中短期策略，参数随市场变化
    """
    print("=" * 60)
    print("示例 2：WalkForwardValidator - 滚动窗口验证")
    print("=" * 60)
    
    # 1. 创建验证器（6 个月训练，1 个月测试，每月滚动）
    validator = WalkForwardValidator(
        window_size=120,  # 6 个月≈120 交易日
        step_size=20,     # 1 个月≈20 交易日
        test_size=20      # 1 个月测试
    )
    
    # 2. 准备数据（1 年数据）
    data = create_mock_data(250)
    
    # 3. 划分数据
    splits = validator.split(data)
    
    print(f"总数据量：{len(data)} 行")
    print(f"验证轮数：{len(splits)} 轮")
    print(f"配置：window={validator.window_size}d, step={validator.step_size}d, test={validator.test_size}d")
    print()
    
    # 4. 展示每轮划分
    for i, (train, test) in enumerate(splits[:5], 1):  # 只显示前 5 轮
        print(f"第 {i} 轮:")
        print(f"  训练集：{len(train)} 行 | {train.index[0].date()} ~ {train.index[-1].date()}")
        print(f"  测试集：{len(test)} 行 | {test.index[0].date()} ~ {test.index[-1].date()}")
    print()


def example_expanding_window_validator():
    """
    示例 3：ExpandingWindowValidator（扩展窗口验证）
    
    适用场景：参数稳定的策略，希望用更多历史数据训练
    """
    print("=" * 60)
    print("示例 3：ExpandingWindowValidator - 扩展窗口验证")
    print("=" * 60)
    
    # 1. 创建验证器
    validator = ExpandingWindowValidator(
        initial_window=60,  # 初始 3 个月
        step_size=20,       # 每月扩展
        test_size=20        # 1 个月测试
    )
    
    # 2. 准备数据
    data = create_mock_data(200)
    
    # 3. 划分数据
    splits = validator.split(data)
    
    print(f"总数据量：{len(data)} 行")
    print(f"验证轮数：{len(splits)} 轮")
    print(f"配置：initial={validator.initial_window}d, step={validator.step_size}d, test={validator.test_size}d")
    print()
    
    # 4. 展示训练集扩展过程
    for i, (train, test) in enumerate(splits[:5], 1):
        print(f"第 {i} 轮:")
        print(f"  训练集：{len(train)} 行 (扩展中) | {train.index[0].date()} ~ {train.index[-1].date()}")
        print(f"  测试集：{len(test)} 行 (固定) | {test.index[0].date()} ~ {test.index[-1].date()}")
    print()


def example_validator_engine():
    """
    示例 4：ValidatorEngine（完整验证流程）
    
    展示如何使用验证器引擎执行完整验证
    """
    print("=" * 60)
    print("示例 4：ValidatorEngine - 完整验证流程")
    print("=" * 60)
    
    # 1. 创建验证器引擎（使用滚动窗口验证）
    engine = create_validator_engine(
        validator_type="walk_forward",
        validator_config={
            "window_size": 60,
            "step_size": 20,
            "test_size": 20
        },
        initial_capital=100000.0
    )
    
    # 2. 准备数据
    data = create_mock_data(200)
    
    print(f"验证器类型：{engine.validator.name}")
    print(f"初始资金：{engine.initial_capital:,.0f}")
    print(f"数据量：{len(data)} 行")
    print()
    
    # 3. 说明
    print("注意：完整验证需要策略类支持，此处仅演示流程")
    print("实际使用：report = engine.run(strategy_name='macd', data=data, param_grid={...})")
    print()
    
    # 4. 展示验证器配置
    print("验证器配置:")
    config = engine.validator.get_config()
    for key, value in config.items():
        print(f"  {key}: {value}")
    print()


def example_with_real_data():
    """
    示例 5：使用真实数据（需要数据库中有数据）
    """
    print("=" * 60)
    print("示例 5：使用真实数据验证")
    print("=" * 60)
    
    try:
        # 1. 加载真实数据
        data_loader = get_data_loader()
        data = data_loader.load_klines(
            symbol="600519",  # 贵州茅台
            start_date="2024-01-01",
            end_date="2024-12-31",
            period="daily",
            adjust="qfq"
        )
        
        if data.empty:
            print("⚠️  无数据，请先同步股票数据")
            print("运行：python scripts/sync_klines.py 600519 2024-01-01 2024-12-31")
            return
        
        print(f"成功加载数据：{len(data)} 行")
        print(f"时间范围：{data.index[0]} ~ {data.index[-1]}")
        print()
        
        # 2. 创建验证器
        validator = WalkForwardValidator(
            window_size=120,  # 6 个月
            step_size=20,     # 1 个月
            test_size=20      # 1 个月
        )
        
        # 3. 划分数据
        splits = validator.split(data)
        
        print(f"验证轮数：{len(splits)} 轮")
        print()
        
        # 4. 展示第一轮
        if splits:
            train, test = splits[0]
            print("第 1 轮验证:")
            print(f"  训练集：{len(train)} 行 | {train.index[0]} ~ {train.index[-1]}")
            print(f"  测试集：{len(test)} 行 | {test.index[0]} ~ {test.index[-1]}")
        
    except Exception as e:
        print(f"⚠️  加载数据失败：{e}")
        print("请确保数据库中有股票数据")


def main():
    """运行所有示例"""
    print("\n")
    print("╔" + "=" * 58 + "╗")
    print("║" + " " * 15 + "回测验证器模块使用示例" + " " * 15 + "║")
    print("╚" + "=" * 58 + "╝")
    print()
    
    # 运行示例
    example_holdout_validator()
    example_walk_forward_validator()
    example_expanding_window_validator()
    example_validator_engine()
    example_with_real_data()
    
    print("=" * 60)
    print("示例完成！")
    print("=" * 60)
    print()
    print("📖 更多信息请查看:")
    print("   - docs/VALIDATOR_DESIGN.md (设计文档)")
    print("   - docs/REQUIREMENTS_LOG.md (需求日志)")
    print()


if __name__ == "__main__":
    main()

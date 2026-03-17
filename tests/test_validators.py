"""
验证器模块单元测试
"""
import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from agents.backtest.validators import (
    HoldoutValidator, WalkForwardValidator, ExpandingWindowValidator,
    create_validator
)
from agents.backtest.validator_engine import (
    ValidatorEngine, create_validator_engine, OverfittingAnalysis
)


def create_mock_data(num_rows: int = 200) -> pd.DataFrame:
    """创建模拟 K 线数据"""
    dates = pd.date_range(start="2024-01-01", periods=num_rows, freq="D")
    np.random.seed(42)
    
    return pd.DataFrame({
        "open": 100 + np.cumsum(np.random.randn(num_rows) * 0.5),
        "high": 100 + np.cumsum(np.random.randn(num_rows) * 0.5) + np.abs(np.random.randn(num_rows)),
        "low": 100 + np.cumsum(np.random.randn(num_rows) * 0.5) - np.abs(np.random.randn(num_rows)),
        "close": 100 + np.cumsum(np.random.randn(num_rows) * 0.5),
        "volume": np.random.randint(1000, 10000, num_rows)
    }, index=dates)


class TestHoldoutValidator:
    """测试 HoldoutValidator"""
    
    def test_split_ratio(self):
        """测试分割比例正确"""
        validator = HoldoutValidator(train_ratio=0.6)
        data = create_mock_data(200)
        
        train, test = validator.split(data)
        
        assert len(train) == 120  # 200 * 0.6
        assert len(test) == 80    # 200 - 120
        assert len(train) + len(test) == len(data)
    
    def test_default_ratio(self):
        """测试默认分割比例"""
        validator = HoldoutValidator()
        data = create_mock_data(100)
        
        train, test = validator.split(data)
        
        assert len(train) == 60  # 默认 0.6
        assert len(test) == 40
    
    def test_invalid_ratio(self):
        """测试无效比例抛出异常"""
        with pytest.raises(ValueError):
            HoldoutValidator(train_ratio=0.3)  # < 0.5
        
        with pytest.raises(ValueError):
            HoldoutValidator(train_ratio=0.95)  # > 0.9
    
    def test_min_data_requirement(self):
        """测试最小数据量检查"""
        validator = HoldoutValidator()
        too_short_data = create_mock_data(30)  # < 60
        
        with pytest.raises(ValueError, match="数据量不足"):
            validator.split(too_short_data)
    
    def test_get_config(self):
        """测试配置序列化"""
        validator = HoldoutValidator(train_ratio=0.7, shuffle=False)
        config = validator.get_config()
        
        assert config["type"] == "holdout"
        assert config["train_ratio"] == 0.7
        assert config["shuffle"] is False


class TestWalkForwardValidator:
    """测试 WalkForwardValidator"""
    
    def test_rolling_windows(self):
        """测试滚动窗口生成"""
        validator = WalkForwardValidator(
            window_size=60,
            step_size=20,
            test_size=20
        )
        data = create_mock_data(200)
        
        splits = validator.split(data)
        
        # 200 行数据，window=60, test=20, step=20
        # 第 1 轮：0-60 train, 60-80 test
        # 第 2 轮：20-80 train, 80-100 test
        # 第 3 轮：40-100 train, 100-120 test
        # 第 4 轮：60-120 train, 120-140 test
        # 第 5 轮：80-130 train, 130-150 test
        # 第 6 轮：100-160 train, 160-180 test
        # 第 7 轮：120-180 train, 180-200 test
        assert len(splits) == 7
    
    def test_window_sizes(self):
        """测试每个窗口的大小"""
        validator = WalkForwardValidator(
            window_size=60,
            step_size=20,
            test_size=20
        )
        data = create_mock_data(200)
        splits = validator.split(data)
        
        for train, test in splits:
            assert len(train) == 60
            assert len(test) == 20
    
    def test_no_overlap(self):
        """测试训练集和测试集无重叠"""
        validator = WalkForwardValidator(window_size=60, step_size=20, test_size=20)
        data = create_mock_data(200)
        splits = validator.split(data)
        
        for train, test in splits:
            # 训练集的最后一个索引应该小于测试集的第一个索引
            assert train.index[-1] < test.index[0]
    
    def test_min_data_requirement(self):
        """测试最小数据量检查"""
        validator = WalkForwardValidator(window_size=60, step_size=20, test_size=20)
        too_short_data = create_mock_data(50)  # < 60+20=80
        
        with pytest.raises(ValueError, match="数据量不足"):
            validator.split(too_short_data)
    
    def test_get_config(self):
        """测试配置序列化"""
        validator = WalkForwardValidator(window_size=100, step_size=10, test_size=30)
        config = validator.get_config()
        
        assert config["type"] == "walk_forward"
        assert config["window_size"] == 100
        assert config["step_size"] == 10
        assert config["test_size"] == 30


class TestExpandingWindowValidator:
    """测试 ExpandingWindowValidator"""
    
    def test_expanding_windows(self):
        """测试扩展窗口生成"""
        validator = ExpandingWindowValidator(
            initial_window=60,
            step_size=20,
            test_size=20
        )
        data = create_mock_data(200)
        
        splits = validator.split(data)
        
        # 第 1 轮：0-60 train, 60-80 test
        # 第 2 轮：0-80 train, 80-100 test
        # 第 3 轮：0-100 train, 100-120 test
        # 第 4 轮：0-120 train, 120-140 test
        # 第 5 轮：0-140 train, 140-160 test
        # 第 6 轮：0-160 train, 160-180 test
        # 第 7 轮：0-180 train, 180-200 test
        assert len(splits) == 7
    
    def test_window_expansion(self):
        """测试训练集逐步扩展"""
        validator = ExpandingWindowValidator(
            initial_window=60,
            step_size=20,
            test_size=20
        )
        data = create_mock_data(200)
        splits = validator.split(data)
        
        prev_train_size = 0
        for train, test in splits:
            # 训练集应该逐步扩大
            assert len(train) > prev_train_size or prev_train_size == 0
            assert len(test) == 20  # 测试集大小固定
            prev_train_size = len(train)
        
        # 验证第一个和最后一个训练集大小
        first_train, _ = splits[0]
        last_train, _ = splits[-1]
        assert len(first_train) == 60  # initial_window
        assert len(last_train) == 180  # 扩展到接近末尾
    
    def test_get_config(self):
        """测试配置序列化"""
        validator = ExpandingWindowValidator(
            initial_window=100,
            step_size=15,
            test_size=25
        )
        config = validator.get_config()
        
        assert config["type"] == "expanding_window"
        assert config["initial_window"] == 100
        assert config["step_size"] == 15
        assert config["test_size"] == 25


class TestCreateValidator:
    """测试工厂函数"""
    
    def test_create_holdout(self):
        """测试创建 HoldoutValidator"""
        validator = create_validator("holdout", {"train_ratio": 0.7})
        
        assert isinstance(validator, HoldoutValidator)
        assert validator.train_ratio == 0.7
    
    def test_create_walk_forward(self):
        """测试创建 WalkForwardValidator"""
        validator = create_validator("walk_forward", {"window_size": 100})
        
        assert isinstance(validator, WalkForwardValidator)
        assert validator.window_size == 100
    
    def test_create_expanding_window(self):
        """测试创建 ExpandingWindowValidator"""
        validator = create_validator("expanding_window", {"initial_window": 150})
        
        assert isinstance(validator, ExpandingWindowValidator)
        assert validator.initial_window == 150
    
    def test_create_unknown_type(self):
        """测试未知类型抛出异常"""
        with pytest.raises(ValueError, match="未知的验证器类型"):
            create_validator("unknown_type")


class TestValidatorEngine:
    """测试 ValidatorEngine"""
    
    def test_create_engine(self):
        """测试创建验证器引擎"""
        engine = create_validator_engine(
            validator_type="walk_forward",
            validator_config={"window_size": 60},
            initial_capital=50000.0
        )
        
        assert isinstance(engine, ValidatorEngine)
        assert engine.initial_capital == 50000.0
        assert isinstance(engine.validator, WalkForwardValidator)
    
    def test_create_auto_engine(self):
        """测试自动选择验证器"""
        engine = create_validator_engine(validator_type="auto")
        
        assert isinstance(engine, ValidatorEngine)
        # auto 默认使用 walk_forward
        assert isinstance(engine.validator, WalkForwardValidator)
    
    def test_overfitting_analysis_good(self):
        """测试过拟合分析 - 稳定策略"""
        analysis = OverfittingAnalysis(
            sharpe_consistency="good",
            sharpe_std=0.15,
            param_stability="stable",
            param_variance=0.1,
            train_test_gap=0.1,
            risk_level="low"
        )
        
        assert analysis.risk_level == "low"
        assert len(analysis.warnings) == 0
    
    def test_overfitting_analysis_warning(self):
        """测试过拟合分析 - 警告"""
        analysis = OverfittingAnalysis(
            sharpe_consistency="warning",
            sharpe_std=0.45,
            param_stability="unstable",
            param_variance=0.35,
            train_test_gap=0.4,
            risk_level="medium",
            warnings=["夏普比率波动较大", "最优参数波动较大"]
        )
        
        assert analysis.risk_level == "medium"
        assert len(analysis.warnings) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

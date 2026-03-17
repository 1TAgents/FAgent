"""
回测验证器模块

支持三种验证方式：
1. HoldoutValidator - 固定训练/测试集分割（适合长期策略）
2. WalkForwardValidator - 滚动窗口验证（适合中短期策略）
3. ExpandingWindowValidator - 扩展窗口验证（适合参数稳定策略）
"""
from abc import ABC, abstractmethod
from typing import List, Tuple, Dict, Any, Optional
import pandas as pd
import numpy as np


class BacktestValidator(ABC):
    """回测验证器基类"""
    
    def __init__(self, name: str, description: str = ""):
        self.name = name
        self.description = description
    
    @abstractmethod
    def split(self, data: pd.DataFrame) -> Any:
        """
        划分数据集
        
        Returns:
            根据验证器类型返回不同结构：
            - Holdout: (train_df, test_df)
            - WalkForward: List[(train_df, test_df), ...]
            - ExpandingWindow: List[(train_df, test_df), ...]
        """
        pass
    
    @abstractmethod
    def get_config(self) -> Dict[str, Any]:
        """返回验证器配置（用于序列化/日志）"""
        pass
    
    def validate(self, data: pd.DataFrame) -> bool:
        """验证数据是否满足要求（最小数据量等）"""
        min_rows = self._get_min_required_rows()
        if len(data) < min_rows:
            raise ValueError(f"数据量不足：需要至少 {min_rows} 行，实际 {len(data)} 行")
        return True
    
    @abstractmethod
    def _get_min_required_rows(self) -> int:
        """获取最小需要的数据行数"""
        pass


class HoldoutValidator(BacktestValidator):
    """
    固定训练/测试集分割
    
    适用于：长期策略（参数稳定，不需要频繁调整）
    
    示例：
    - 训练集：2024-01-01 ~ 2024-06-30 (60%)
    - 测试集：2024-07-01 ~ 2024-10-31 (40%)
    """
    
    def __init__(self, train_ratio: float = 0.6, shuffle: bool = False):
        """
        Args:
            train_ratio: 训练集比例 (0.5-0.9)
            shuffle: 是否打乱（时间序列一般不打乱）
        """
        super().__init__(
            name="holdout",
            description="固定训练/测试集分割"
        )
        if not 0.5 <= train_ratio <= 0.9:
            raise ValueError("train_ratio 必须在 0.5-0.9 之间")
        self.train_ratio = train_ratio
        self.shuffle = shuffle
    
    def split(self, data: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
        self.validate(data)
        split_point = int(len(data) * self.train_ratio)
        train_data = data.iloc[:split_point].copy()
        test_data = data.iloc[split_point:].copy()
        return train_data, test_data
    
    def get_config(self) -> Dict[str, Any]:
        return {
            "type": "holdout",
            "train_ratio": self.train_ratio,
            "shuffle": self.shuffle
        }
    
    def _get_min_required_rows(self) -> int:
        return 60  # 至少 60 个交易日（约 3 个月）


class WalkForwardValidator(BacktestValidator):
    """
    滚动窗口验证（Walk-Forward Analysis）
    
    适用于：中短期策略（参数需要随市场变化调整）
    
    示例：
    - 第 1 轮：训练 (1-6 月) → 测试 (7 月)
    - 第 2 轮：训练 (2-7 月) → 测试 (8 月)
    - 第 3 轮：训练 (3-8 月) → 测试 (9 月)
    """
    
    def __init__(
        self,
        window_size: int = 120,  # 训练窗口长度（交易日）
        step_size: int = 20,     # 滚动步长
        test_size: int = 20      # 测试窗口长度
    ):
        """
        Args:
            window_size: 训练窗口长度（默认 120 天≈6 个月）
            step_size: 每次滚动的步长（默认 20 天≈1 个月）
            test_size: 测试窗口长度（默认 20 天≈1 个月）
        """
        super().__init__(
            name="walk_forward",
            description="滚动窗口验证"
        )
        if window_size <= 0:
            raise ValueError("window_size 必须大于 0")
        if step_size <= 0:
            raise ValueError("step_size 必须大于 0")
        if test_size <= 0:
            raise ValueError("test_size 必须大于 0")
        
        self.window_size = window_size
        self.step_size = step_size
        self.test_size = test_size
    
    def split(self, data: pd.DataFrame) -> List[Tuple[pd.DataFrame, pd.DataFrame]]:
        self.validate(data)
        splits = []
        n = len(data)
        
        # 至少需要 window_size + test_size 才能进行第一轮
        start_idx = 0
        while start_idx + self.window_size + self.test_size <= n:
            train_end = start_idx + self.window_size
            test_end = train_end + self.test_size
            
            train_data = data.iloc[start_idx:train_end].copy()
            test_data = data.iloc[train_end:test_end].copy()
            splits.append((train_data, test_data))
            
            start_idx += self.step_size
        
        if len(splits) == 0:
            raise ValueError(
                f"数据量不足，无法进行滚动验证。"
                f"需要至少 {self.window_size + self.test_size} 行，实际 {n} 行"
            )
        
        return splits
    
    def get_config(self) -> Dict[str, Any]:
        return {
            "type": "walk_forward",
            "window_size": self.window_size,
            "step_size": self.step_size,
            "test_size": self.test_size
        }
    
    def _get_min_required_rows(self) -> int:
        return self.window_size + self.test_size


class ExpandingWindowValidator(BacktestValidator):
    """
    扩展窗口验证
    
    适用于：参数稳定的策略，但希望用更多历史数据训练
    
    示例：
    - 第 1 轮：训练 (1-6 月) → 测试 (7 月)
    - 第 2 轮：训练 (1-7 月) → 测试 (8 月)  # 训练集扩展
    - 第 3 轮：训练 (1-8 月) → 测试 (9 月)
    """
    
    def __init__(
        self,
        initial_window: int = 120,  # 初始训练窗口
        step_size: int = 20,        # 扩展步长
        test_size: int = 20         # 测试窗口长度
    ):
        """
        Args:
            initial_window: 初始训练窗口长度
            step_size: 每次扩展的步长
            test_size: 测试窗口长度
        """
        super().__init__(
            name="expanding_window",
            description="扩展窗口验证"
        )
        if initial_window <= 0:
            raise ValueError("initial_window 必须大于 0")
        if step_size <= 0:
            raise ValueError("step_size 必须大于 0")
        if test_size <= 0:
            raise ValueError("test_size 必须大于 0")
        
        self.initial_window = initial_window
        self.step_size = step_size
        self.test_size = test_size
    
    def split(self, data: pd.DataFrame) -> List[Tuple[pd.DataFrame, pd.DataFrame]]:
        self.validate(data)
        splits = []
        n = len(data)
        
        # 从 initial_window 开始，逐步扩展
        train_end = self.initial_window
        while train_end + self.test_size <= n:
            train_data = data.iloc[:train_end].copy()  # 从起点到当前位置（扩展）
            test_data = data.iloc[train_end:train_end + self.test_size].copy()
            splits.append((train_data, test_data))
            
            train_end += self.step_size
        
        if len(splits) == 0:
            raise ValueError(
                f"数据量不足，无法进行扩展窗口验证。"
                f"需要至少 {self.initial_window + self.test_size} 行，实际 {n} 行"
            )
        
        return splits
    
    def get_config(self) -> Dict[str, Any]:
        return {
            "type": "expanding_window",
            "initial_window": self.initial_window,
            "step_size": self.step_size,
            "test_size": self.test_size
        }
    
    def _get_min_required_rows(self) -> int:
        return self.initial_window + self.test_size


def create_validator(
    validator_type: str,
    config: Optional[Dict[str, Any]] = None
) -> BacktestValidator:
    """
    工厂函数：根据类型创建验证器
    
    Args:
        validator_type: "holdout" | "walk_forward" | "expanding_window"
        config: 验证器配置参数
    
    Returns:
        BacktestValidator 实例
    """
    config = config or {}
    
    if validator_type == "holdout":
        return HoldoutValidator(
            train_ratio=config.get("train_ratio", 0.6),
            shuffle=config.get("shuffle", False)
        )
    elif validator_type == "walk_forward":
        return WalkForwardValidator(
            window_size=config.get("window_size", 120),
            step_size=config.get("step_size", 20),
            test_size=config.get("test_size", 20)
        )
    elif validator_type == "expanding_window":
        return ExpandingWindowValidator(
            initial_window=config.get("initial_window", 120),
            step_size=config.get("step_size", 20),
            test_size=config.get("test_size", 20)
        )
    else:
        raise ValueError(f"未知的验证器类型：{validator_type}")

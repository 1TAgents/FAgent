"""
验证器执行引擎

负责：
1. 根据策略类型选择验证器
2. 执行多轮回测
3. 汇总结果
4. 过拟合检测
"""
import logging
from typing import List, Dict, Any, Optional, Type
from dataclasses import dataclass, field
import pandas as pd
import numpy as np

from .validators import BacktestValidator, HoldoutValidator, WalkForwardValidator, ExpandingWindowValidator
from .engine import BacktestEngine
from .models import StrategyConfig, BacktestReport
from .vectorized_strategies import get_vectorized_strategy, split_vectorized_params

logger = logging.getLogger(__name__)


@dataclass
class RoundResult:
    """单轮验证结果"""
    round: int
    train_period: str
    test_period: str
    train_size: int
    test_size: int
    params: Dict[str, Any]
    train_result: Dict[str, Any]
    test_result: Dict[str, Any]


@dataclass
class OverfittingAnalysis:
    """过拟合分析结果"""
    sharpe_consistency: str  # "good" | "warning" | "bad"
    sharpe_std: float
    param_stability: str  # "stable" | "unstable"
    param_variance: float
    train_test_gap: float  # 训练集和测试集表现差异
    risk_level: str  # "low" | "medium" | "high"
    warnings: List[str] = field(default_factory=list)


@dataclass
class ValidationReport:
    """验证报告"""
    validator_type: str
    validator_config: Dict[str, Any]
    num_rounds: int
    round_results: List[RoundResult]
    summary: Dict[str, Any]
    overfitting_analysis: Optional[OverfittingAnalysis] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典（用于 JSON 序列化）"""
        return {
            "validator_type": self.validator_type,
            "validator_config": self.validator_config,
            "num_rounds": self.num_rounds,
            "round_results": [
                {
                    "round": r.round,
                    "train_period": r.train_period,
                    "test_period": r.test_period,
                    "train_size": r.train_size,
                    "test_size": r.test_size,
                    "params": r.params,
                    "train_result": r.train_result,
                    "test_result": r.test_result
                }
                for r in self.round_results
            ],
            "summary": self.summary,
            "overfitting_analysis": (
                self.overfitting_analysis.__dict__ 
                if self.overfitting_analysis else None
            )
        }


class ValidatorEngine:
    """
    验证器执行引擎
    
    负责执行完整的验证流程，包括多轮回测和过拟合检测
    """
    
    def __init__(
        self,
        validator: BacktestValidator,
        initial_capital: float = 100000.0
    ):
        """
        Args:
            validator: 验证器实例
            initial_capital: 初始资金
        """
        self.validator = validator
        self.initial_capital = initial_capital
    
    def run(
        self,
        strategy_name: str,
        data: pd.DataFrame,
        param_grid: Optional[Dict[str, List[Any]]] = None,
        default_params: Optional[Dict[str, Any]] = None
    ) -> ValidationReport:
        """
        执行验证
        
        Args:
            strategy_name: 策略名称（如 "macd", "dual_ma"）
            data: 完整数据集
            param_grid: 参数网格（用于优化），如 {"fast_period": [8, 12, 15], ...}
            default_params: 默认参数（如果不做参数优化）
        
        Returns:
            ValidationReport 验证报告
        """
        logger.info(
            f"开始验证 | strategy={strategy_name} | "
            f"validator={self.validator.name} | data_rows={len(data)}"
        )
        
        # 1. 划分数据
        splits = self.validator.split(data)
        logger.info(f"数据划分为 {len(splits)} 轮验证")
        
        # 2. 执行回测
        round_results = []
        for i, (train_data, test_data) in enumerate(splits):
            logger.info(f"第 {i+1}/{len(splits)} 轮验证")
            
            # 2.1 在训练集上优化参数
            if param_grid:
                best_params = self._optimize_on_train(
                    strategy_name, train_data, param_grid
                )
            else:
                best_params = default_params or {}
            
            # 2.2 在训练集上验证
            train_result = self._run_backtest(
                strategy_name, train_data, best_params
            )
            
            # 2.3 在测试集上验证
            test_result = self._run_backtest(
                strategy_name, test_data, best_params
            )
            
            # 2.4 记录结果
            round_result = RoundResult(
                round=i + 1,
                train_period=f"{train_data.index[0]} ~ {train_data.index[-1]}",
                test_period=f"{test_data.index[0]} ~ {test_data.index[-1]}",
                train_size=len(train_data),
                test_size=len(test_data),
                params=best_params,
                train_result=train_result,
                test_result=test_result
            )
            round_results.append(round_result)
        
        # 3. 汇总分析
        summary = self._aggregate_results(round_results)
        
        # 4. 过拟合检测
        overfitting_analysis = self._check_overfitting(round_results)
        
        # 5. 生成报告
        report = ValidationReport(
            validator_type=self.validator.name,
            validator_config=self.validator.get_config(),
            num_rounds=len(round_results),
            round_results=round_results,
            summary=summary,
            overfitting_analysis=overfitting_analysis
        )
        
        logger.info(
            f"验证完成 | 轮数={len(round_results)} | "
            f"平均夏普={summary['avg_sharpe']:.2f} | "
            f"过拟合风险={overfitting_analysis.risk_level}"
        )
        
        return report
    
    def _optimize_on_train(
        self,
        strategy_name: str,
        train_data: pd.DataFrame,
        param_grid: Dict[str, List[Any]]
    ) -> Dict[str, Any]:
        """
        在训练集上进行参数优化（网格搜索）
        
        简化版：只测试参数组合，返回最优的
        """
        from itertools import product
        
        best_params = None
        best_sharpe = -np.inf
        
        # 生成所有参数组合
        param_names = list(param_grid.keys())
        param_values = list(param_grid.values())
        
        for values in product(*param_values):
            params = dict(zip(param_names, values))
            
            try:
                result = self._run_backtest(strategy_name, train_data, params)
                sharpe = result.get("sharpe_ratio", 0)
                
                if sharpe > best_sharpe:
                    best_sharpe = sharpe
                    best_params = params
            except Exception as e:
                logger.warning(f"参数组合 {params} 回测失败：{e}")
                continue
        
        return best_params or {}
    
    def _run_backtest(
        self,
        strategy_name: str,
        data: pd.DataFrame,
        params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        执行单次回测
        
        Returns:
            绩效指标字典
        """
        try:
            strategy_params, execution_params = split_vectorized_params(params)

            # 获取策略
            strategy = get_vectorized_strategy(strategy_name, **strategy_params)
            
            # 生成信号
            signals = strategy.generate_signals(data)
            
            # 执行回测
            result = strategy.backtest(signals, self.initial_capital, **execution_params)
            
            return {
                "total_returns": result.get("total_returns", 0),
                "sharpe_ratio": result.get("sharpe_ratio", 0),
                "max_drawdown": result.get("max_drawdown", 0),
                "win_rate": result.get("win_rate", 0),
                "num_trades": result.get("num_trades", 0)
            }
        except Exception as e:
            logger.error(f"回测失败：{e}")
            return {
                "total_returns": 0,
                "sharpe_ratio": 0,
                "max_drawdown": 0,
                "win_rate": 0,
                "num_trades": 0,
                "error": str(e)
            }
    
    def _aggregate_results(
        self,
        round_results: List[RoundResult]
    ) -> Dict[str, Any]:
        """汇总多轮验证结果"""
        if not round_results:
            return {}
        
        # 提取测试集结果
        test_sharpes = [r.test_result["sharpe_ratio"] for r in round_results]
        test_returns = [r.test_result["total_returns"] for r in round_results]
        test_drawdowns = [r.test_result["max_drawdown"] for r in round_results]
        
        return {
            "avg_sharpe": float(np.mean(test_sharpes)),
            "sharpe_std": float(np.std(test_sharpes)),
            "avg_returns": float(np.mean(test_returns)),
            "returns_std": float(np.std(test_returns)),
            "avg_max_drawdown": float(np.mean(test_drawdowns)),
            "best_sharpe": float(max(test_sharpes)),
            "worst_sharpe": float(min(test_sharpes)),
            "num_rounds": len(round_results)
        }
    
    def _check_overfitting(
        self,
        round_results: List[RoundResult]
    ) -> OverfittingAnalysis:
        """
        过拟合检测
        
        检查项：
        1. 测试集夏普比率的标准差（稳定性）
        2. 参数稳定性（不同轮次最优参数是否一致）
        3. 训练集 vs 测试集表现差异
        """
        warnings = []
        
        # 1. 检查测试集表现的标准差
        test_sharpes = [r.test_result["sharpe_ratio"] for r in round_results]
        sharpe_std = float(np.std(test_sharpes))
        
        if sharpe_std < 0.3:
            sharpe_consistency = "good"
        elif sharpe_std < 0.6:
            sharpe_consistency = "warning"
            warnings.append(f"夏普比率波动较大 (std={sharpe_std:.2f})")
        else:
            sharpe_consistency = "bad"
            warnings.append(f"夏普比率波动过大 (std={sharpe_std:.2f})，策略可能不稳定")
        
        # 2. 检查参数稳定性
        params_history = [r.params for r in round_results]
        param_variance = self._calculate_param_variance(params_history)
        
        if param_variance < 0.2:
            param_stability = "stable"
        elif param_variance < 0.5:
            param_stability = "unstable"
            warnings.append(f"最优参数波动较大，策略可能对参数敏感")
        else:
            param_stability = "unstable"
            warnings.append(f"最优参数极不稳定，策略可能过拟合")
        
        # 3. 检查训练/测试差异
        train_sharpes = [r.train_result["sharpe_ratio"] for r in round_results]
        avg_train_sharpe = np.mean(train_sharpes)
        avg_test_sharpe = np.mean(test_sharpes)
        train_test_gap = float(avg_train_sharpe - avg_test_sharpe)
        
        if train_test_gap > 0.5:
            warnings.append(
                f"训练集表现明显优于测试集 (gap={train_test_gap:.2f})，可能过拟合"
            )
        
        # 4. 综合风险评估
        risk_score = 0
        if sharpe_consistency == "warning":
            risk_score += 1
        elif sharpe_consistency == "bad":
            risk_score += 2
        
        if param_stability == "unstable":
            risk_score += 1
        
        if train_test_gap > 0.3:
            risk_score += 1
        if train_test_gap > 0.5:
            risk_score += 1
        
        if risk_score <= 1:
            risk_level = "low"
        elif risk_score <= 3:
            risk_level = "medium"
        else:
            risk_level = "high"
        
        return OverfittingAnalysis(
            sharpe_consistency=sharpe_consistency,
            sharpe_std=sharpe_std,
            param_stability=param_stability,
            param_variance=param_variance,
            train_test_gap=train_test_gap,
            risk_level=risk_level,
            warnings=warnings
        )
    
    def _calculate_param_variance(
        self,
        params_history: List[Dict[str, Any]]
    ) -> float:
        """
        计算参数历史的变化程度
        
        Returns:
            归一化的方差值 (0-1)，越小越稳定
        """
        if not params_history or len(params_history) < 2:
            return 0.0
        
        # 收集所有参数名
        all_param_names = set()
        for params in params_history:
            all_param_names.update(params.keys())
        
        if not all_param_names:
            return 0.0
        
        # 计算每个参数的方差，然后取平均
        variances = []
        for param_name in all_param_names:
            values = [
                p.get(param_name, 0) 
                for p in params_history 
                if param_name in p
            ]
            if len(values) >= 2:
                # 归一化方差
                mean_val = np.mean(values)
                std_val = np.std(values)
                if mean_val != 0:
                    cv = std_val / abs(mean_val)  # 变异系数
                    variances.append(min(cv, 1.0))  # 上限为 1
        
        return float(np.mean(variances)) if variances else 0.0


def create_validator_engine(
    validator_type: str,
    validator_config: Optional[Dict[str, Any]] = None,
    initial_capital: float = 100000.0
) -> ValidatorEngine:
    """
    工厂函数：创建验证器引擎
    
    Args:
        validator_type: "holdout" | "walk_forward" | "expanding_window" | "auto"
        validator_config: 验证器配置
        initial_capital: 初始资金
    
    Returns:
        ValidatorEngine 实例
    """
    from .validators import create_validator
    
    # 自动选择验证器（根据配置或默认）
    if validator_type == "auto":
        # 默认使用滚动窗口验证（最通用）
        validator_type = "walk_forward"
    
    validator = create_validator(validator_type, validator_config)
    return ValidatorEngine(validator, initial_capital)

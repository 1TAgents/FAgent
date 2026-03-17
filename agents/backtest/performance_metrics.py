"""
Performance Metrics - 回测性能指标（行业最佳实践）

基于量化投资行业标准，实现完整的回测指标体系
参考：QuantConnect、聚宽、优矿等主流平台
"""
import numpy as np
import pandas as pd
from typing import Dict, List, Optional
from dataclasses import dataclass, field


@dataclass
class PerformanceMetrics:
    """
    回测性能指标（行业标准）
    
    分为 6 大类：
    1. 收益类指标
    2. 风险类指标
    3. 风险调整收益指标
    4. 交易统计指标
    5. 资金曲线指标
    6. 基准对比指标
    """
    
    # ========== 1. 收益类指标 ==========
    total_return: float = 0.0          # 总收益率 (%)
    annual_return: float = 0.0         # 年化收益率 (%)
    excess_return: float = 0.0         # 超额收益率 (%)
    monthly_return: float = 0.0        # 月均收益率 (%)
    best_month_return: float = 0.0     # 最佳月度收益 (%)
    worst_month_return: float = 0.0    # 最差月度收益 (%)
    
    # ========== 2. 风险类指标 ==========
    volatility: float = 0.0            # 年化波动率 (%)
    downside_volatility: float = 0.0   # 下行波动率 (%)
    max_drawdown: float = 0.0          # 最大回撤 (%)
    avg_drawdown: float = 0.0          # 平均回撤 (%)
    max_drawdown_days: int = 0         # 最大回撤持续期 (天)
    var_95: float = 0.0                # VaR 95% (%)
    var_99: float = 0.0                # VaR 99% (%)
    cvar_95: float = 0.0               # 条件 VaR 95% (%)
    
    # ========== 3. 风险调整收益指标 ==========
    sharpe_ratio: float = 0.0          # 夏普比率
    sortino_ratio: float = 0.0         # 索提诺比率
    calmar_ratio: float = 0.0          # 卡玛比率
    omega_ratio: float = 0.0           # 欧米伽比率
    information_ratio: float = 0.0     # 信息比率
    
    # ========== 4. 交易统计指标 ==========
    total_trades: int = 0              # 总交易次数
    winning_trades: int = 0            # 盈利交易次数
    losing_trades: int = 0             # 亏损交易次数
    win_rate: float = 0.0              # 胜率 (%)
    profit_factor: float = 0.0         # 盈亏比
    avg_win: float = 0.0               # 平均盈利 (%)
    avg_loss: float = 0.0              # 平均亏损 (%)
    avg_trade_return: float = 0.0      # 平均每笔收益 (%)
    avg_holding_days: float = 0.0      # 平均持仓天数
    max_consecutive_wins: int = 0      # 最大连续盈利
    max_consecutive_losses: int = 0    # 最大连续亏损
    
    # ========== 5. 资金曲线指标 ==========
    initial_capital: float = 0.0       # 初始资金
    final_capital: float = 0.0         # 最终资金
    total_pnl: float = 0.0             # 总盈亏 (绝对值)
    equity_curve: List[float] = field(default_factory=list)  # 资金曲线
    daily_returns: List[float] = field(default_factory=list)  # 日收益率
    
    # ========== 6. 基准对比指标 ==========
    benchmark_return: float = 0.0      # 基准收益率 (%)
    alpha: float = 0.0                 # Alpha (%)
    beta: float = 0.0                  # Beta
    correlation: float = 0.0           # 与基准相关系数
    tracking_error: float = 0.0        # 跟踪误差 (%)
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            '收益类': {
                '总收益率': f"{self.total_return:.2f}%",
                '年化收益率': f"{self.annual_return:.2f}%",
                '超额收益率': f"{self.excess_return:.2f}%",
                '月均收益率': f"{self.monthly_return:.2f}%",
                '最佳月度': f"{self.best_month_return:.2f}%",
                '最差月度': f"{self.worst_month_return:.2f}%",
            },
            '风险类': {
                '波动率': f"{self.volatility:.2f}%",
                '下行波动率': f"{self.downside_volatility:.2f}%",
                '最大回撤': f"{self.max_drawdown:.2f}%",
                '平均回撤': f"{self.avg_drawdown:.2f}%",
                '回撤持续期': f"{self.max_drawdown_days}天",
                'VaR(95%)': f"{self.var_95:.2f}%",
                'CVaR(95%)': f"{self.cvar_95:.2f}%",
            },
            '风险调整收益': {
                '夏普比率': f"{self.sharpe_ratio:.2f}",
                '索提诺比率': f"{self.sortino_ratio:.2f}",
                '卡玛比率': f"{self.calmar_ratio:.2f}",
                '欧米伽比率': f"{self.omega_ratio:.2f}",
                '信息比率': f"{self.information_ratio:.2f}",
            },
            '交易统计': {
                '总交易次数': self.total_trades,
                '盈利次数': self.winning_trades,
                '亏损次数': self.losing_trades,
                '胜率': f"{self.win_rate:.1f}%",
                '盈亏比': f"{self.profit_factor:.2f}",
                '平均盈利': f"{self.avg_win:.2f}%",
                '平均亏损': f"{self.avg_loss:.2f}%",
                '平均持仓': f"{self.avg_holding_days:.1f}天",
                '最大连胜': self.max_consecutive_wins,
                '最大连亏': self.max_consecutive_losses,
            },
            '基准对比': {
                '基准收益': f"{self.benchmark_return:.2f}%",
                'Alpha': f"{self.alpha:.2f}%",
                'Beta': f"{self.beta:.2f}",
                '相关系数': f"{self.correlation:.2f}",
                '跟踪误差': f"{self.tracking_error:.2f}%",
            },
        }
    
    def summary(self) -> str:
        """生成摘要"""
        return (
            f"总收益：{self.total_return:+.2f}% | "
            f"年化：{self.annual_return:+.2f}% | "
            f"夏普：{self.sharpe_ratio:.2f} | "
            f"最大回撤：{self.max_drawdown:.2f}% | "
            f"胜率：{self.win_rate:.1f}%"
        )


class MetricsCalculator:
    """
    指标计算器
    
    实现所有回测指标的计算逻辑
    """
    
    def __init__(self, risk_free_rate: float = 0.03):
        """
        初始化
        
        Args:
            risk_free_rate: 无风险利率（年化，默认 3%）
        """
        self.risk_free_rate = risk_free_rate
    
    def calculate_all_metrics(
        self,
        equity_curve: List[float],
        daily_returns: List[float],
        trades: List[Dict] = None,
        benchmark_returns: List[float] = None
    ) -> PerformanceMetrics:
        """
        计算所有指标
        
        Args:
            equity_curve: 资金曲线
            daily_returns: 日收益率序列
            trades: 交易记录列表
            benchmark_returns: 基准收益率序列（可选）
            
        Returns:
            PerformanceMetrics 对象
        """
        metrics = PerformanceMetrics()
        
        # 1. 收益类指标
        metrics.total_return = self._calc_total_return(equity_curve)
        metrics.annual_return = self._calc_annual_return(equity_curve, daily_returns)
        metrics.monthly_return = metrics.annual_return / 12
        metrics.best_month_return, metrics.worst_month_return = self._calc_monthly_returns(daily_returns)
        
        # 2. 风险类指标
        metrics.volatility = self._calc_volatility(daily_returns)
        metrics.downside_volatility = self._calc_downside_volatility(daily_returns)
        metrics.max_drawdown, metrics.max_drawdown_days = self._calc_max_drawdown(equity_curve)
        metrics.avg_drawdown = self._calc_avg_drawdown(equity_curve)
        metrics.var_95, metrics.var_99, metrics.cvar_95 = self._calc_var(daily_returns)
        
        # 3. 风险调整收益指标
        metrics.sharpe_ratio = self._calc_sharpe_ratio(daily_returns)
        metrics.sortino_ratio = self._calc_sortino_ratio(daily_returns)
        metrics.calmar_ratio = self._calc_calmar_ratio(metrics.annual_return, metrics.max_drawdown)
        metrics.omega_ratio = self._calc_omega_ratio(daily_returns)
        
        if benchmark_returns:
            metrics.information_ratio = self._calc_information_ratio(daily_returns, benchmark_returns)
            metrics.alpha, metrics.beta = self._calc_alpha_beta(daily_returns, benchmark_returns)
            metrics.correlation = self._calc_correlation(daily_returns, benchmark_returns)
            metrics.tracking_error = self._calc_tracking_error(daily_returns, benchmark_returns)
            metrics.excess_return = metrics.annual_return - self._calc_total_return_from_returns(benchmark_returns)
        
        # 4. 交易统计指标
        if trades:
            metrics.total_trades = len(trades)
            metrics.winning_trades = sum(1 for t in trades if t.get('pnl', 0) > 0)
            metrics.losing_trades = sum(1 for t in trades if t.get('pnl', 0) <= 0)
            metrics.win_rate = metrics.winning_trades / metrics.total_trades * 100 if metrics.total_trades > 0 else 0
            metrics.profit_factor = self._calc_profit_factor(trades)
            metrics.avg_win = self._calc_avg_win(trades)
            metrics.avg_loss = self._calc_avg_loss(trades)
            metrics.avg_trade_return = self._calc_avg_trade_return(trades)
            metrics.avg_holding_days = self._calc_avg_holding_days(trades)
            metrics.max_consecutive_wins, metrics.max_consecutive_losses = self._calc_consecutive(trades)
        
        # 5. 资金曲线指标
        metrics.initial_capital = equity_curve[0] if equity_curve else 0
        metrics.final_capital = equity_curve[-1] if equity_curve else 0
        metrics.total_pnl = metrics.final_capital - metrics.initial_capital
        metrics.equity_curve = equity_curve
        metrics.daily_returns = daily_returns
        
        return metrics
    
    def _calc_total_return(self, equity_curve: List[float]) -> float:
        """计算总收益率"""
        if not equity_curve or len(equity_curve) < 2:
            return 0.0
        return (equity_curve[-1] / equity_curve[0] - 1) * 100
    
    def _calc_annual_return(self, equity_curve: List[float], daily_returns: List[float]) -> float:
        """计算年化收益率"""
        if not equity_curve or len(equity_curve) < 2:
            return 0.0
        total_return = equity_curve[-1] / equity_curve[0] - 1
        n_years = len(daily_returns) / 252 if daily_returns else 1
        return ((1 + total_return) ** (1 / n_years) - 1) * 100
    
    def _calc_volatility(self, daily_returns: List[float]) -> float:
        """计算年化波动率"""
        if not daily_returns or len(daily_returns) < 2:
            return 0.0
        return np.std(daily_returns) * np.sqrt(252) * 100
    
    def _calc_downside_volatility(self, daily_returns: List[float]) -> float:
        """计算下行波动率"""
        if not daily_returns or len(daily_returns) < 2:
            return 0.0
        downside_returns = [r for r in daily_returns if r < 0]
        if not downside_returns:
            return 0.0
        return np.std(downside_returns) * np.sqrt(252) * 100
    
    def _calc_max_drawdown(self, equity_curve: List[float]) -> tuple:
        """计算最大回撤和持续期"""
        if not equity_curve or len(equity_curve) < 2:
            return 0.0, 0
        
        equity = np.array(equity_curve)
        peak = np.maximum.accumulate(equity)
        drawdown = (equity - peak) / peak * 100
        
        max_dd = drawdown.min()
        
        # 计算持续期
        max_dd_start = np.argmin(equity / peak)
        max_dd_end = len(equity) - 1
        for i in range(max_dd_start, len(equity)):
            if equity[i] >= peak[max_dd_start]:
                max_dd_end = i
                break
        
        duration = max_dd_end - max_dd_start
        return max_dd, duration
    
    def _calc_avg_drawdown(self, equity_curve: List[float]) -> float:
        """计算平均回撤"""
        if not equity_curve or len(equity_curve) < 2:
            return 0.0
        equity = np.array(equity_curve)
        peak = np.maximum.accumulate(equity)
        drawdown = (equity - peak) / peak * 100
        return np.mean(np.abs(drawdown))
    
    def _calc_sharpe_ratio(self, daily_returns: List[float]) -> float:
        """计算夏普比率"""
        if not daily_returns or len(daily_returns) < 2:
            return 0.0
        excess_returns = np.array(daily_returns) - self.risk_free_rate / 252
        if np.std(excess_returns) == 0:
            return 0.0
        return np.sqrt(252) * np.mean(excess_returns) / np.std(excess_returns)
    
    def _calc_sortino_ratio(self, daily_returns: List[float]) -> float:
        """计算索提诺比率"""
        if not daily_returns or len(daily_returns) < 2:
            return 0.0
        excess_returns = np.array(daily_returns) - self.risk_free_rate / 252
        downside_returns = excess_returns[excess_returns < 0]
        if len(downside_returns) == 0 or np.std(downside_returns) == 0:
            return 0.0
        return np.sqrt(252) * np.mean(excess_returns) / np.std(downside_returns)
    
    def _calc_calmar_ratio(self, annual_return: float, max_drawdown: float) -> float:
        """计算卡玛比率"""
        if max_drawdown == 0:
            return 0.0
        return annual_return / abs(max_drawdown)
    
    def _calc_omega_ratio(self, daily_returns: List[float], threshold: float = 0.0) -> float:
        """计算欧米伽比率"""
        if not daily_returns or len(daily_returns) < 2:
            return 0.0
        returns = np.array(daily_returns)
        gains = returns[returns > threshold]
        losses = returns[returns <= threshold]
        
        if len(losses) == 0:
            return float('inf')
        
        return np.sum(gains) / abs(np.sum(losses))
    
    def _calc_var(self, daily_returns: List[float]) -> tuple:
        """计算 VaR 和 CVaR"""
        if not daily_returns or len(daily_returns) < 2:
            return 0.0, 0.0, 0.0
        
        returns = np.array(daily_returns)
        var_95 = np.percentile(returns, 5) * 100
        var_99 = np.percentile(returns, 1) * 100
        cvar_95 = np.mean(returns[returns <= np.percentile(returns, 5)]) * 100
        
        return var_95, var_99, cvar_95
    
    def _calc_monthly_returns(self, daily_returns: List[float]) -> tuple:
        """计算最佳和最差月度收益"""
        if not daily_returns or len(daily_returns) < 20:
            return 0.0, 0.0
        
        # 按月分组（简化：每 21 天为一个月）
        monthly = []
        for i in range(0, len(daily_returns), 21):
            month_returns = daily_returns[i:i+21]
            if len(month_returns) >= 10:
                monthly.append(np.prod(1 + np.array(month_returns)) - 1)
        
        if not monthly:
            return 0.0, 0.0
        
        return max(monthly) * 100, min(monthly) * 100
    
    def _calc_profit_factor(self, trades: List[Dict]) -> float:
        """计算盈亏比"""
        if not trades:
            return 0.0
        
        total_profit = sum(t.get('pnl', 0) for t in trades if t.get('pnl', 0) > 0)
        total_loss = abs(sum(t.get('pnl', 0) for t in trades if t.get('pnl', 0) < 0))
        
        if total_loss == 0:
            return float('inf') if total_profit > 0 else 0.0
        
        return total_profit / total_loss
    
    def _calc_avg_win(self, trades: List[Dict]) -> float:
        """计算平均盈利"""
        winning_trades = [t for t in trades if t.get('pnl', 0) > 0]
        if not winning_trades:
            return 0.0
        return np.mean([t.get('pnl_percent', 0) for t in winning_trades]) * 100
    
    def _calc_avg_loss(self, trades: List[Dict]) -> float:
        """计算平均亏损"""
        losing_trades = [t for t in trades if t.get('pnl', 0) < 0]
        if not losing_trades:
            return 0.0
        return np.mean([t.get('pnl_percent', 0) for t in losing_trades]) * 100
    
    def _calc_avg_trade_return(self, trades: List[Dict]) -> float:
        """计算平均每笔收益"""
        if not trades:
            return 0.0
        return np.mean([t.get('pnl_percent', 0) for t in trades]) * 100
    
    def _calc_avg_holding_days(self, trades: List[Dict]) -> float:
        """计算平均持仓天数"""
        if not trades:
            return 0.0
        
        from datetime import datetime
        holding_days = []
        for trade in trades:
            if 'entry_time' in trade and 'exit_time' in trade:
                entry = datetime.strptime(trade['entry_time'], '%Y-%m-%d')
                exit = datetime.strptime(trade['exit_time'], '%Y-%m-%d')
                holding_days.append((exit - entry).days)
        
        return np.mean(holding_days) if holding_days else 0.0
    
    def _calc_consecutive(self, trades: List[Dict]) -> tuple:
        """计算最大连续盈利和亏损"""
        if not trades:
            return 0, 0
        
        max_wins = max_losses = current_wins = current_losses = 0
        
        for trade in trades:
            pnl = trade.get('pnl', 0)
            if pnl > 0:
                current_wins += 1
                current_losses = 0
                max_wins = max(max_wins, current_wins)
            else:
                current_losses += 1
                current_wins = 0
                max_losses = max(max_losses, current_losses)
        
        return max_wins, max_losses
    
    def _calc_information_ratio(self, strategy_returns: List[float], benchmark_returns: List[float]) -> float:
        """计算信息比率"""
        if not strategy_returns or not benchmark_returns:
            return 0.0
        
        excess_returns = np.array(strategy_returns) - np.array(benchmark_returns)
        if np.std(excess_returns) == 0:
            return 0.0
        
        return np.sqrt(252) * np.mean(excess_returns) / np.std(excess_returns)
    
    def _calc_alpha_beta(self, strategy_returns: List[float], benchmark_returns: List[float]) -> tuple:
        """计算 Alpha 和 Beta"""
        if not strategy_returns or not benchmark_returns or len(strategy_returns) < 10:
            return 0.0, 0.0
        
        # 简化计算：使用线性回归
        x = np.array(benchmark_returns)
        y = np.array(strategy_returns)
        
        if len(x) != len(y):
            min_len = min(len(x), len(y))
            x = x[:min_len]
            y = y[:min_len]
        
        # Beta = Cov(Rs, Rm) / Var(Rm)
        beta = np.cov(y, x)[0, 1] / np.var(x) if np.var(x) > 0 else 0
        
        # Alpha = mean(Rs) - Beta * mean(Rm)
        alpha = np.mean(y) - beta * np.mean(x)
        
        # 年化
        alpha = alpha * 252 * 100
        
        return alpha, beta
    
    def _calc_correlation(self, strategy_returns: List[float], benchmark_returns: List[float]) -> float:
        """计算相关系数"""
        if not strategy_returns or not benchmark_returns or len(strategy_returns) < 10:
            return 0.0
        
        x = np.array(benchmark_returns)
        y = np.array(strategy_returns)
        
        if len(x) != len(y):
            min_len = min(len(x), len(y))
            x = x[:min_len]
            y = y[:min_len]
        
        return np.corrcoef(x, y)[0, 1]
    
    def _calc_tracking_error(self, strategy_returns: List[float], benchmark_returns: List[float]) -> float:
        """计算跟踪误差"""
        if not strategy_returns or not benchmark_returns:
            return 0.0
        
        excess_returns = np.array(strategy_returns) - np.array(benchmark_returns)
        return np.std(excess_returns) * np.sqrt(252) * 100
    
    def _calc_total_return_from_returns(self, returns: List[float]) -> float:
        """从收益率序列计算总收益"""
        if not returns:
            return 0.0
        return (np.prod(1 + np.array(returns)) - 1) * 100


# 示例用法
if __name__ == "__main__":
    # 测试数据
    np.random.seed(42)
    n_days = 252
    
    # 生成模拟资金曲线
    daily_returns = np.random.normal(0.0005, 0.02, n_days).tolist()
    equity_curve = [100000]
    for r in daily_returns:
        equity_curve.append(equity_curve[-1] * (1 + r))
    
    # 生成模拟交易
    trades = []
    for i in range(20):
        trades.append({
            'pnl': np.random.normal(1000, 2000),
            'pnl_percent': np.random.normal(0.01, 0.02),
            'entry_time': f'2025-01-{(i*10)%28+1:02d}',
            'exit_time': f'2025-01-{(i*10+5)%28+1:02d}'
        })
    
    # 计算指标
    calculator = MetricsCalculator(risk_free_rate=0.03)
    metrics = calculator.calculate_all_metrics(
        equity_curve=equity_curve,
        daily_returns=daily_returns,
        trades=trades
    )
    
    print("=" * 70)
    print("📊 回测性能指标（行业最佳实践）")
    print("=" * 70)
    print(metrics.summary())
    print("\n详细指标:")
    
    for category, indicators in metrics.to_dict().items():
        print(f"\n{category}:")
        for name, value in indicators.items():
            print(f"  {name}: {value}")
    
    print("=" * 70)

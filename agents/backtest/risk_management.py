"""
Risk Management - 风险控制模块

提供仓位管理、止损止盈、风险控制等功能
"""
import numpy as np
from typing import Dict, Optional
from dataclasses import dataclass


@dataclass
class PositionConfig:
    """仓位配置"""
    max_position_ratio: float = 1.0  # 最大仓位比例（1=100%）
    max_single_stock_ratio: float = 0.2  # 单只股票最大仓位（0.2=20%）
    max_sector_ratio: float = 0.3  # 单行业最大仓位
    cash_reserve_ratio: float = 0.0  # 现金保留比例


@dataclass
class StopLossConfig:
    """止损止盈配置"""
    stop_loss_ratio: float = 0.0  # 止损比例（0.05=5%）
    take_profit_ratio: float = 0.0  # 止盈比例
    trailing_stop_ratio: float = 0.0  # 移动止损比例
    stop_loss_days: Optional[int] = None  # 止损天数（持有 N 天后止损）


class RiskManager:
    """
    风险管理器
    
    负责仓位控制、止损止盈、风险指标计算
    """
    
    def __init__(
        self,
        position_config: PositionConfig = None,
        stop_loss_config: StopLossConfig = None
    ):
        """
        初始化
        
        Args:
            position_config: 仓位配置
            stop_loss_config: 止损止盈配置
        """
        self.position_config = position_config or PositionConfig()
        self.stop_loss_config = stop_loss_config or StopLossConfig()
        
        # 持仓记录
        self.positions = {}  # symbol -> {quantity, avg_cost, entry_date, entry_price}
        
        # 交易历史
        self.trade_history = []
        
        # 权益曲线
        self.equity_curve = []
        
        # 峰值（用于计算回撤）
        self.peak_equity = 0
    
    def calculate_position_size(
        self,
        symbol: str,
        price: float,
        total_capital: float,
        current_position_value: float = 0
    ) -> int:
        """
        计算仓位大小
        
        Args:
            symbol: 股票代码
            price: 当前价格
            total_capital: 总资金
            current_position_value: 当前持仓市值
            
        Returns:
            可购买股数
        """
        config = self.position_config
        
        # 1. 计算可用资金
        available_capital = total_capital * (1 - config.max_position_ratio)
        available_capital = max(0, available_capital - current_position_value)
        
        # 2. 单只股票限制
        max_stock_value = total_capital * config.max_single_stock_ratio
        
        # 3. 计算最大可买股数
        max_quantity = int(max_stock_value / price / 100) * 100  # 100 的整数倍
        
        # 4. 考虑可用资金
        affordable_quantity = int(available_capital / price / 100) * 100
        
        # 取较小值
        quantity = min(max_quantity, affordable_quantity)
        
        return quantity
    
    def check_stop_loss(
        self,
        symbol: str,
        current_price: float,
        current_date: str,
        highest_price: float = None
    ) -> Optional[str]:
        """
        检查是否需要止损
        
        Args:
            symbol: 股票代码
            current_price: 当前价格
            current_date: 当前日期
            highest_price: 最高价（用于移动止损）
            
        Returns:
            止损原因（如果需要止损），否则 None
        """
        if symbol not in self.positions:
            return None
        
        position = self.positions[symbol]
        entry_price = position['entry_price']
        entry_date = position['entry_date']
        
        config = self.stop_loss_config
        
        # 1. 固定止损
        if config.stop_loss_ratio > 0:
            loss_ratio = (current_price - entry_price) / entry_price
            if loss_ratio <= -config.stop_loss_ratio:
                return f"固定止损 ({loss_ratio:.1%} <= {-config.stop_loss_ratio:.1%})"
        
        # 2. 止盈
        if config.take_profit_ratio > 0:
            profit_ratio = (current_price - entry_price) / entry_price
            if profit_ratio >= config.take_profit_ratio:
                return f"止盈 ({profit_ratio:.1%} >= {config.take_profit_ratio:.1%})"
        
        # 3. 移动止损
        if config.trailing_stop_ratio > 0 and highest_price:
            from_highest = (current_price - highest_price) / highest_price
            if from_highest <= -config.trailing_stop_ratio:
                return f"移动止损 ({from_highest:.1%} <= {-config.trailing_stop_ratio:.1%})"
        
        # 4. 时间止损
        if config.stop_loss_days is not None:
            from datetime import datetime
            entry_dt = datetime.strptime(entry_date, '%Y-%m-%d')
            current_dt = datetime.strptime(current_date, '%Y-%m-%d')
            holding_days = (current_dt - entry_dt).days
            
            if holding_days >= config.stop_loss_days:
                return f"时间止损 (持有{holding_days}天 >= {config.stop_loss_days}天)"
        
        return None
    
    def update_position(
        self,
        symbol: str,
        quantity: int,
        price: float,
        date: str,
        side: str = 'buy'
    ):
        """
        更新持仓
        
        Args:
            symbol: 股票代码
            quantity: 数量
            price: 价格
            date: 日期
            side: buy/sell
        """
        if side == 'buy':
            if symbol in self.positions:
                pos = self.positions[symbol]
                # 加权平均成本
                total_cost = pos['avg_cost'] * pos['quantity'] + price * quantity
                total_quantity = pos['quantity'] + quantity
                pos['avg_cost'] = total_cost / total_quantity
                pos['quantity'] = total_quantity
            else:
                self.positions[symbol] = {
                    'quantity': quantity,
                    'avg_cost': price,
                    'entry_date': date,
                    'entry_price': price,
                    'highest_price': price
                }
        else:  # sell
            if symbol in self.positions:
                pos = self.positions[symbol]
                pos['quantity'] -= quantity
                if pos['quantity'] <= 0:
                    del self.positions[symbol]
    
    def calculate_risk_metrics(self, equity_curve: list) -> Dict:
        """
        计算风险指标
        
        Args:
            equity_curve: 权益曲线
            
        Returns:
            风险指标字典
        """
        if not equity_curve or len(equity_curve) < 2:
            return {}
        
        equity = np.array(equity_curve)
        
        # 1. 最大回撤
        peak = np.maximum.accumulate(equity)
        drawdown = (equity - peak) / peak
        max_drawdown = drawdown.min()
        
        # 2. 波动率（年化）
        returns = np.diff(equity) / equity[:-1]
        volatility = np.std(returns) * np.sqrt(252)
        
        # 3. VaR（95% 置信度）
        var_95 = np.percentile(returns, 5)
        
        # 4. 夏普比率
        sharpe = np.sqrt(252) * np.mean(returns) / np.std(returns) if np.std(returns) > 0 else 0
        
        # 5. 卡玛比率
        annual_return = (equity[-1] / equity[0]) ** (252 / len(equity)) - 1
        calmar = annual_return / abs(max_drawdown) if max_drawdown != 0 else 0
        
        return {
            'max_drawdown': max_drawdown,
            'volatility': volatility,
            'var_95': var_95,
            'sharpe_ratio': sharpe,
            'calmar_ratio': calmar,
            'annual_return': annual_return
        }
    
    def get_position_summary(self) -> Dict:
        """
        获取持仓摘要
        
        Returns:
            持仓摘要字典
        """
        if not self.positions:
            return {'count': 0, 'total_value': 0}
        
        total_value = sum(pos['quantity'] * pos['avg_cost'] for pos in self.positions.values())
        
        return {
            'count': len(self.positions),
            'total_value': total_value,
            'positions': self.positions
        }


# 凯利公式仓位计算
def kelly_position_size(win_rate: float, win_loss_ratio: float) -> float:
    """
    凯利公式计算最优仓位
    
    Args:
        win_rate: 胜率（0-1）
        win_loss_ratio: 盈亏比（平均盈利/平均亏损）
        
    Returns:
        最优仓位比例（0-1）
    """
    if win_loss_ratio <= 0:
        return 0.0
    
    kelly = win_rate - (1 - win_rate) / win_loss_ratio
    
    # 限制在 0-1 之间，并且使用半凯利（更保守）
    return max(0, min(0.5, kelly / 2))


# 示例用法
if __name__ == "__main__":
    # 测试风险控制
    risk_manager = RiskManager(
        position_config=PositionConfig(
            max_position_ratio=0.95,
            max_single_stock_ratio=0.2
        ),
        stop_loss_config=StopLossConfig(
            stop_loss_ratio=0.05,
            take_profit_ratio=0.15
        )
    )
    
    # 测试仓位计算
    quantity = risk_manager.calculate_position_size(
        symbol="600519",
        price=1500.0,
        total_capital=100000
    )
    print(f"可购买股数：{quantity}")
    
    # 测试凯利公式
    kelly = kelly_position_size(win_rate=0.55, win_loss_ratio=2.0)
    print(f"凯利仓位：{kelly:.1%}")

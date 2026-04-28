"""
Backtest Models - 回测数据模型定义
"""
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from enum import Enum
from datetime import datetime


class OrderSide(str, Enum):
    """订单方向"""
    BUY = "buy"
    SELL = "sell"


class OrderStatus(str, Enum):
    """订单状态"""
    PENDING = "pending"
    FILLED = "filled"
    CANCELLED = "cancelled"


class SignalType(str, Enum):
    """信号类型"""
    ENTRY_LONG = "entry_long"       # 做多入场
    EXIT_LONG = "exit_long"         # 做多出场
    ENTRY_SHORT = "entry_short"     # 做空入场
    EXIT_SHORT = "exit_short"       # 做空出场


# ==================== 策略定义 ====================

class StrategyConfig(BaseModel):
    """策略配置"""
    name: str = Field(..., description="策略名称")
    description: str = Field("", description="策略描述")
    initial_capital: float = Field(100000.0, description="初始资金")
    commission_rate: float = Field(0.0003, description="佣金费率（默认万分之三）")
    slippage: float = Field(0.001, description="滑点（默认 0.1%）")
    stop_loss: Optional[float] = Field(None, description="止损比例（如 0.05=5%）")
    take_profit: Optional[float] = Field(None, description="止盈比例")
    max_position: Optional[float] = Field(None, description="最大仓位比例（0-1）")
    
    # 策略参数（由具体策略定义）
    params: Dict[str, Any] = Field(default_factory=dict, description="策略参数")


# ==================== 交易信号 ====================

class TradingSignal(BaseModel):
    """交易信号"""
    signal_type: SignalType = Field(..., description="信号类型")
    symbol: str = Field(..., description="股票代码")
    price: float = Field(..., description="信号价格")
    timestamp: str = Field(..., description="信号时间")
    strength: float = Field(1.0, description="信号强度（0-1）")
    reason: str = Field("", description="信号原因")
    
    # 建议仓位（0-1，1=满仓）
    position_size: Optional[float] = Field(None, description="建议仓位比例")
    stop_loss_price: Optional[float] = Field(None, description="止损价")
    take_profit_price: Optional[float] = Field(None, description="止盈价")


# ==================== 订单与成交 ====================

class Order(BaseModel):
    """订单"""
    order_id: str = Field(..., description="订单 ID")
    signal_id: str = Field(..., description="关联信号 ID")
    symbol: str = Field(..., description="股票代码")
    side: OrderSide = Field(..., description="买卖方向")
    order_type: str = Field("market", description="订单类型（market/limit）")
    price: float = Field(..., description="订单价格")
    quantity: int = Field(..., description="订单数量（股）")
    timestamp: str = Field(..., description="下单时间")
    status: OrderStatus = Field(OrderStatus.PENDING, description="订单状态")
    
    # 成交信息
    fill_price: Optional[float] = Field(None, description="成交均价")
    fill_quantity: Optional[int] = Field(None, description="成交数量")
    fill_time: Optional[str] = Field(None, description="成交时间")
    commission: Optional[float] = Field(None, description="佣金")
    slippage_cost: Optional[float] = Field(None, description="滑点成本")


class Trade(BaseModel):
    """成交记录（完整的交易对：开仓 + 平仓）"""
    trade_id: str = Field(..., description="交易 ID")
    symbol: str = Field(..., description="股票代码")
    entry_price: float = Field(..., description="入场价")
    exit_price: Optional[float] = Field(None, description="出场价")
    entry_time: str = Field(..., description="入场时间")
    exit_time: Optional[str] = Field(None, description="出场时间")
    quantity: int = Field(..., description="交易数量")
    side: str = Field(..., description="交易方向（long/short）")
    
    # 盈亏
    pnl: Optional[float] = Field(None, description="盈亏金额")
    pnl_percent: Optional[float] = Field(None, description="盈亏比例")
    commission_total: Optional[float] = Field(None, description="总佣金")
    
    # 状态
    is_open: bool = Field(True, description="是否未平仓")
    exit_reason: Optional[str] = Field(None, description="平仓原因")


# ==================== 投资组合 ====================

class Position(BaseModel):
    """当前持仓"""
    symbol: str = Field(..., description="股票代码")
    quantity: int = Field(..., description="持仓数量")
    avg_cost: float = Field(..., description="平均成本")
    current_price: float = Field(0.0, description="当前价格")
    market_value: float = Field(0.0, description="市值")
    unrealized_pnl: float = Field(0.0, description="浮盈浮亏")
    unrealized_pnl_percent: float = Field(0.0, description="浮盈浮亏比例")


class Portfolio(BaseModel):
    """投资组合状态"""
    cash: float = Field(..., description="可用现金")
    total_value: float = Field(..., description="总资产")
    positions: List[Position] = Field(default_factory=list, description="持仓列表")
    position_value: float = Field(0.0, description="持仓总市值")
    position_ratio: float = Field(0.0, description="仓位比例")


# ==================== 绩效报告 ====================

class PerformanceMetrics(BaseModel):
    """绩效指标"""
    # 收益指标
    total_return: float = Field(0.0, description="总收益率")
    annual_return: float = Field(0.0, description="年化收益率")
    benchmark_return: Optional[float] = Field(None, description="基准收益率")
    alpha: Optional[float] = Field(None, description="Alpha")
    beta: Optional[float] = Field(None, description="Beta")
    
    # 风险指标
    volatility: float = Field(0.0, description="年化波动率")
    max_drawdown: float = Field(0.0, description="最大回撤")
    max_drawdown_duration: int = Field(0, description="最大回撤持续期（天）")
    sharpe_ratio: float = Field(0.0, description="夏普比率")
    sortino_ratio: float = Field(0.0, description="索提诺比率")
    calmar_ratio: float = Field(0.0, description="卡玛比率")
    
    # 交易统计
    total_trades: int = Field(0, description="总交易次数")
    winning_trades: int = Field(0, description="盈利交易次数")
    losing_trades: int = Field(0, description="亏损交易次数")
    win_rate: float = Field(0.0, description="胜率")
    profit_factor: float = Field(0.0, description="盈亏比")
    avg_win: float = Field(0.0, description="平均盈利")
    avg_loss: float = Field(0.0, description="平均亏损")
    avg_holding_period: float = Field(0.0, description="平均持仓期（天）")
    
    # 资金曲线
    initial_capital: float = Field(0.0, description="初始资金")
    final_capital: float = Field(0.0, description="最终资金")
    total_pnl: float = Field(0.0, description="总盈亏")


class BacktestReport(BaseModel):
    """回测报告"""
    # 策略信息
    strategy_name: str = Field(..., description="策略名称")
    symbol: str = Field(..., description="回测标的")
    
    # 回测区间
    start_date: str = Field(..., description="开始日期")
    end_date: str = Field(..., description="结束日期")
    trading_days: int = Field(0, description="交易天数")
    
    # 配置
    config: StrategyConfig = Field(..., description="策略配置")
    
    # 绩效指标
    metrics: PerformanceMetrics = Field(..., description="绩效指标")
    
    # 交易记录
    trades: List[Trade] = Field(default_factory=list, description="交易记录")
    
    # 资金曲线（日期：资产值）
    equity_curve: Dict[str, float] = Field(default_factory=dict, description="资金曲线")
    
    # 月度收益（YYYY-MM：收益率）
    monthly_returns: Dict[str, float] = Field(default_factory=dict, description="月度收益")
    
    def summary(self) -> str:
        """生成回测摘要"""
        m = self.metrics
        summary = f"【{self.strategy_name}】回测报告\n"
        summary += f"回测区间：{self.start_date} ~ {self.end_date}\n"
        summary += f"总收益率：{m.total_return:+.2f}% | 年化：{m.annual_return:+.2f}%\n"
        summary += f"夏普比率：{m.sharpe_ratio:.2f} | 最大回撤：{m.max_drawdown:.2f}%\n"
        if m.total_trades > 0 and m.winning_trades == 0 and m.losing_trades == 0:
            summary += f"交易次数：{m.total_trades}"
        else:
            summary += f"胜率：{m.win_rate:.1f}% | 交易次数：{m.total_trades} | 盈亏比：{m.profit_factor:.2f}"
        return summary


# ==================== 回测请求/响应 ====================

class BacktestRequest(BaseModel):
    """回测请求"""
    strategy_name: str = Field(..., description="策略名称")
    symbol: str = Field(..., description="回测标的")
    start_date: str = Field(..., description="开始日期（YYYY-MM-DD）")
    end_date: str = Field(..., description="结束日期（YYYY-MM-DD）")
    initial_capital: float = Field(100000.0, description="初始资金")
    params: Dict[str, Any] = Field(default_factory=dict, description="策略参数")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="附加元数据（如 query/rid/cid）")


class BacktestResponse(BaseModel):
    """回测响应"""
    success: bool = Field(..., description="是否成功")
    report: Optional[BacktestReport] = Field(None, description="回测报告")
    error: Optional[str] = Field(None, description="错误信息")
    report_id: Optional[str] = Field(None, description="回测运行 ID")
    artifacts_dir: Optional[str] = Field(None, description="回测产物目录")
    engine: Optional[str] = Field(None, description="执行引擎（vectorized/classic）")

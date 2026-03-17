"""
Backtest Engine - 回测执行引擎

核心流程：
1. 加载历史数据
2. 生成交易信号
3. 模拟成交
4. 计算绩效
"""
import logging
import uuid
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Type
import pandas as pd
import numpy as np

from .models import (
    StrategyConfig, TradingSignal, SignalType, Order, OrderSide, OrderStatus,
    Trade, Position, Portfolio, BacktestReport, PerformanceMetrics, BacktestRequest
)

logger = logging.getLogger(__name__)


class BacktestEngine:
    """
    回测引擎
    
    负责执行回测流程：数据加载 → 信号生成 → 订单执行 → 绩效计算
    """
    
    def __init__(self, config: StrategyConfig):
        """
        初始化回测引擎
        
        Args:
            config: 策略配置
        """
        self.config = config
        self.initial_capital = config.initial_capital
        self.cash = config.initial_capital
        self.positions: Dict[str, Position] = {}  # symbol -> Position
        self.trades: List[Trade] = []
        self.orders: List[Order] = []
        self.equity_curve: Dict[str, float] = {}
        self.signals: List[TradingSignal] = []
        
        # 绩效计算中间变量
        self.daily_returns: List[float] = []
        self.daily_values: List[float] = []
        self.peak_value = self.initial_capital
        self.max_drawdown = 0.0
        self.max_drawdown_duration = 0
        self.current_drawdown_duration = 0
    
    def run(
        self,
        strategy_class: Type,
        data: pd.DataFrame,
        benchmark_data: Optional[pd.DataFrame] = None
    ) -> BacktestReport:
        """
        执行回测
        
        Args:
            strategy_class: 策略类（继承自 BaseStrategy）
            data: 历史数据（包含 open/high/low/close/volume）
            benchmark_data: 基准数据（可选，用于计算 Alpha/Beta）
            
        Returns:
            回测报告
        """
        logger.info(f"开始回测 | strategy={self.config.name} | data_rows={len(data)}")
        
        # 1. 初始化策略
        strategy = strategy_class(self.config)
        strategy.on_init()
        
        # 2. 逐日回测
        dates = data.index if isinstance(data.index, pd.DatetimeIndex) else pd.to_datetime(data.index)
        
        for i, (date, row) in enumerate(data.iterrows()):
            current_date = dates[i] if isinstance(dates[i], str) else dates[i].strftime("%Y-%m-%d")
            
            # 2.1 生成信号
            signals = strategy.generate_signals(row, self._get_portfolio_snapshot(), self.positions)
            
            # 2.2 执行信号
            for signal in signals:
                self._execute_signal(signal, row, current_date)
            
            # 2.3 更新持仓市值
            self._update_positions(row)
            
            # 2.4 记录资金曲线
            total_value = self._get_total_value()
            self.equity_curve[current_date] = total_value
            self.daily_values.append(total_value)
            
            # 2.5 计算回撤
            self._update_drawdown(total_value)
            
            # 2.6 检查止损止盈
            self._check_stop_loss_take_profit(row, current_date)
        
        # 3. 平仓所有未平仓交易
        if len(data) > 0:
            last_row = data.iloc[-1]
            last_date = dates[-1].strftime("%Y-%m-%d") if isinstance(dates[-1], datetime) else str(dates[-1])
            self._close_all_positions(last_row, last_date, "回测结束")
        
        # 4. 计算绩效指标
        metrics = self._calculate_metrics(benchmark_data)
        
        # 5. 生成报告
        report = BacktestReport(
            strategy_name=self.config.name,
            symbol=data.get('symbol', 'UNKNOWN') if hasattr(data, 'get') else 'UNKNOWN',
            start_date=str(dates[0].strftime("%Y-%m-%d")) if isinstance(dates[0], datetime) else str(dates[0]),
            end_date=str(dates[-1].strftime("%Y-%m-%d")) if isinstance(dates[-1], datetime) else str(dates[-1]),
            trading_days=len(data),
            config=self.config,
            metrics=metrics,
            trades=self.trades,
            equity_curve=self.equity_curve,
            monthly_returns=self._calculate_monthly_returns()
        )
        
        logger.info(f"回测完成 | 总收益率={metrics.total_return:+.2f}% | 夏普比率={metrics.sharpe_ratio:.2f}")
        
        return report
    
    def _execute_signal(self, signal: TradingSignal, market_data: pd.Series, date: str):
        """
        执行交易信号
        
        Args:
            signal: 交易信号
            market_data: 市场数据
            date: 日期
        """
        self.signals.append(signal)
        
        # 计算订单数量
        price = signal.price
        position_size = signal.position_size or 1.0
        max_affordable = self.cash / price
        
        if signal.signal_type == SignalType.ENTRY_LONG:
            # 做多入场
            quantity = int(max_affordable * position_size)
            if quantity > 0:
                self._create_order(
                    signal_id=str(uuid.uuid4()),
                    symbol=signal.symbol,
                    side=OrderSide.BUY,
                    price=price,
                    quantity=quantity,
                    timestamp=date
                )
        
        elif signal.signal_type == SignalType.EXIT_LONG:
            # 做多出场
            if signal.symbol in self.positions:
                position = self.positions[signal.symbol]
                self._create_order(
                    signal_id=str(uuid.uuid4()),
                    symbol=signal.symbol,
                    side=OrderSide.SELL,
                    price=price,
                    quantity=position.quantity,
                    timestamp=date
                )
    
    def _create_order(
        self,
        signal_id: str,
        symbol: str,
        side: OrderSide,
        price: float,
        quantity: int,
        timestamp: str,
        order_type: str = "market"
    ):
        """
        创建订单并模拟成交
        
        Args:
            signal_id: 信号 ID
            symbol: 股票代码
            side: 买卖方向
            price: 订单价格
            quantity: 订单数量
            timestamp: 时间戳
            order_type: 订单类型
        """
        # 计算滑点和佣金
        slippage = price * self.config.slippage
        fill_price = price + slippage if side == OrderSide.BUY else price - slippage
        commission = fill_price * quantity * self.config.commission_rate
        
        order = Order(
            order_id=str(uuid.uuid4()),
            signal_id=signal_id,
            symbol=symbol,
            side=side,
            order_type=order_type,
            price=price,
            quantity=quantity,
            timestamp=timestamp,
            status=OrderStatus.FILLED,
            fill_price=fill_price,
            fill_quantity=quantity,
            fill_time=timestamp,
            commission=commission,
            slippage_cost=slippage * quantity
        )
        
        self.orders.append(order)
        
        # 更新持仓
        if side == OrderSide.BUY:
            self._update_position_long(symbol, fill_price, quantity, commission)
        else:
            self._update_position_short(symbol, fill_price, quantity, commission, timestamp)
        
        logger.debug(f"订单成交 | {side.value} {symbol} x{quantity} @ {fill_price:.2f}")
    
    def _update_position_long(self, symbol: str, price: float, quantity: int, commission: float):
        """更新做多持仓"""
        cost = price * quantity + commission
        
        if symbol in self.positions:
            pos = self.positions[symbol]
            total_cost = pos.avg_cost * pos.quantity + cost
            total_quantity = pos.quantity + quantity
            pos.avg_cost = total_cost / total_quantity
            pos.quantity = total_quantity
        else:
            self.positions[symbol] = Position(
                symbol=symbol,
                quantity=quantity,
                avg_cost=price,
                current_price=price,
                market_value=price * quantity,
                unrealized_pnl=0,
                unrealized_pnl_percent=0
            )
        
        self.cash -= cost
    
    def _update_position_short(self, symbol: str, price: float, quantity: int, commission: float, timestamp: str):
        """更新做空持仓（平仓）"""
        if symbol not in self.positions:
            logger.warning(f"尝试平仓不存在的持仓：{symbol}")
            return
        
        pos = self.positions[symbol]
        
        # 创建交易记录
        pnl = (price - pos.avg_cost) * pos.quantity - commission
        pnl_percent = pnl / (pos.avg_cost * pos.quantity)
        
        trade = Trade(
            trade_id=str(uuid.uuid4()),
            symbol=symbol,
            entry_price=pos.avg_cost,
            exit_price=price,
            entry_time=pos.model_dump().get('entry_time', timestamp),  # 简化处理
            exit_time=timestamp,
            quantity=pos.quantity,
            side="long",
            pnl=pnl,
            pnl_percent=pnl_percent,
            commission_total=commission,
            is_open=False,
            exit_reason="signal"
        )
        
        self.trades.append(trade)
        self.cash += price * quantity - commission
        
        # 移除持仓
        del self.positions[symbol]
    
    def _update_positions(self, market_data: pd.Series):
        """更新持仓市值"""
        close_price = market_data.get('close', market_data.get('收盘', 0))
        
        for symbol, pos in self.positions.items():
            pos.current_price = close_price
            pos.market_value = close_price * pos.quantity
            pos.unrealized_pnl = (close_price - pos.avg_cost) * pos.quantity
            pos.unrealized_pnl_percent = pos.unrealized_pnl / (pos.avg_cost * pos.quantity)
    
    def _get_total_value(self) -> float:
        """获取总资产"""
        position_value = sum(pos.market_value for pos in self.positions.values())
        return self.cash + position_value
    
    def _get_portfolio_snapshot(self) -> Portfolio:
        """获取投资组合快照"""
        position_value = sum(pos.market_value for pos in self.positions.values())
        total_value = self.cash + position_value
        
        return Portfolio(
            cash=self.cash,
            total_value=total_value,
            positions=list(self.positions.values()),
            position_value=position_value,
            position_ratio=position_value / total_value if total_value > 0 else 0
        )
    
    def _update_drawdown(self, current_value: float):
        """更新回撤计算"""
        if current_value > self.peak_value:
            self.peak_value = current_value
            self.current_drawdown_duration = 0
        else:
            drawdown = (self.peak_value - current_value) / self.peak_value
            if drawdown > self.max_drawdown:
                self.max_drawdown = drawdown
            self.current_drawdown_duration += 1
            if self.current_drawdown_duration > self.max_drawdown_duration:
                self.max_drawdown_duration = self.current_drawdown_duration
    
    def _check_stop_loss_take_profit(self, market_data: pd.Series, date: str):
        """检查止损止盈"""
        if not self.config.stop_loss and not self.config.take_profit:
            return
        
        close_price = market_data.get('close', market_data.get('收盘', 0))
        
        for symbol, pos in list(self.positions.items()):
            pnl_percent = (close_price - pos.avg_cost) / pos.avg_cost
            
            # 止损
            if self.config.stop_loss and pnl_percent <= -self.config.stop_loss:
                logger.info(f"触发止损 | {symbol} | pnl={pnl_percent:.2%}")
                self._update_position_short(symbol, close_price, pos.quantity, 
                                           close_price * pos.quantity * self.config.commission_rate, date)
            
            # 止盈
            elif self.config.take_profit and pnl_percent >= self.config.take_profit:
                logger.info(f"触发止盈 | {symbol} | pnl={pnl_percent:.2%}")
                self._update_position_short(symbol, close_price, pos.quantity,
                                           close_price * pos.quantity * self.config.commission_rate, date)
    
    def _close_all_positions(self, market_data: pd.Series, date: str, reason: str):
        """平仓所有持仓"""
        close_price = market_data.get('close', market_data.get('收盘', 0))
        
        for symbol in list(self.positions.keys()):
            pos = self.positions[symbol]
            commission = close_price * pos.quantity * self.config.commission_rate
            self._update_position_short(symbol, close_price, pos.quantity, commission, date)
    
    def _calculate_metrics(self, benchmark_data: Optional[pd.DataFrame] = None) -> PerformanceMetrics:
        """计算绩效指标"""
        if len(self.daily_values) < 2:
            return PerformanceMetrics()
        
        # 计算日收益率
        daily_values = np.array(self.daily_values)
        daily_returns = np.diff(daily_values) / daily_values[:-1]
        self.daily_returns = daily_returns.tolist()
        
        # 总收益率
        total_return = (daily_values[-1] - daily_values[0]) / daily_values[0] * 100
        
        # 年化收益率
        trading_days = len(daily_values)
        annual_return = ((daily_values[-1] / daily_values[0]) ** (252 / trading_days) - 1) * 100
        
        # 波动率
        volatility = np.std(daily_returns) * np.sqrt(252) * 100 if len(daily_returns) > 0 else 0
        
        # 夏普比率（假设无风险利率 3%）
        risk_free_rate = 3.0
        excess_return = annual_return - risk_free_rate
        sharpe_ratio = excess_return / volatility if volatility > 0 else 0
        
        # 索提诺比率
        downside_returns = daily_returns[daily_returns < 0]
        downside_std = np.std(downside_returns) * np.sqrt(252) * 100 if len(downside_returns) > 0 else 0
        sortino_ratio = excess_return / downside_std if downside_std > 0 else 0
        
        # 卡玛比率
        calmar_ratio = annual_return / (self.max_drawdown * 100) if self.max_drawdown > 0 else 0
        
        # 交易统计
        total_trades = len(self.trades)
        winning_trades = sum(1 for t in self.trades if t.pnl and t.pnl > 0)
        losing_trades = sum(1 for t in self.trades if t.pnl and t.pnl <= 0)
        win_rate = winning_trades / total_trades * 100 if total_trades > 0 else 0
        
        total_profit = sum(t.pnl for t in self.trades if t.pnl and t.pnl > 0)
        total_loss = abs(sum(t.pnl for t in self.trades if t.pnl and t.pnl < 0))
        profit_factor = total_profit / total_loss if total_loss > 0 else 0
        
        avg_win = total_profit / winning_trades if winning_trades > 0 else 0
        avg_loss = total_loss / losing_trades if losing_trades > 0 else 0
        
        return PerformanceMetrics(
            total_return=total_return,
            annual_return=annual_return,
            volatility=volatility,
            max_drawdown=self.max_drawdown * 100,
            max_drawdown_duration=self.max_drawdown_duration,
            sharpe_ratio=sharpe_ratio,
            sortino_ratio=sortino_ratio,
            calmar_ratio=calmar_ratio,
            total_trades=total_trades,
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            win_rate=win_rate,
            profit_factor=profit_factor,
            avg_win=avg_win,
            avg_loss=avg_loss,
            initial_capital=self.initial_capital,
            final_capital=daily_values[-1],
            total_pnl=daily_values[-1] - self.initial_capital
        )
    
    def _calculate_monthly_returns(self) -> Dict[str, float]:
        """计算月度收益"""
        monthly_returns = {}
        
        if not self.equity_curve:
            return monthly_returns
        
        # 按月份分组
        month_values: Dict[str, List[float]] = {}
        for date_str, value in self.equity_curve.items():
            month = date_str[:7]  # YYYY-MM
            if month not in month_values:
                month_values[month] = []
            month_values[month].append(value)
        
        # 计算月度收益率
        prev_month_end = self.initial_capital
        for month in sorted(month_values.keys()):
            values = month_values[month]
            month_end = values[-1]
            monthly_return = (month_end - prev_month_end) / prev_month_end * 100
            monthly_returns[month] = monthly_return
            prev_month_end = month_end
        
        return monthly_returns


# ==================== 策略基类 ====================

class BaseStrategy:
    """
    策略基类
    
    所有策略需继承此类并实现 generate_signals 方法
    """
    
    def __init__(self, config: StrategyConfig):
        self.config = config
        self.params = config.params
    
    def on_init(self):
        """初始化回调（可选重写）"""
        pass
    
    def generate_signals(
        self,
        row: pd.Series,
        portfolio: Portfolio,
        positions: Dict[str, Position]
    ) -> List[TradingSignal]:
        """
        生成交易信号
        
        Args:
            row: 当前 K 线数据
            portfolio: 投资组合快照
            positions: 当前持仓
            
        Returns:
            交易信号列表
        """
        raise NotImplementedError("策略必须实现 generate_signals 方法")

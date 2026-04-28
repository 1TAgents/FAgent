import math

import pandas as pd

from agents.backtest.trading_cost import TradingCostCalculator
from agents.backtest.vectorized_strategies import run_long_only_backtest


def _market_data(closes, signals):
    dates = pd.date_range("2026-01-01", periods=len(closes), freq="D")
    return pd.DataFrame(
        {
            "symbol": ["TEST"] * len(closes),
            "open": closes,
            "high": closes,
            "low": closes,
            "close": closes,
            "volume": [100000] * len(closes),
            "signal": signals,
        },
        index=dates,
    )


def _zero_cost():
    return TradingCostCalculator(
        stamp_duty=0,
        commission=0,
        min_commission=0,
        transfer_fee=0,
    )


def test_no_signal_keeps_capital_flat():
    data = _market_data([10, 11, 12, 13], [0, 0, 0, 0])

    result = run_long_only_backtest(
        data,
        initial_capital=100000,
        slippage=0,
        cost_calculator=_zero_cost(),
    )

    assert result["trades"] == 0
    assert result["positions"] == [0, 0, 0, 0]
    assert result["equity_curve"] == [100000, 100000, 100000, 100000]
    assert result["total_returns"] == 0


def test_buy_signal_creates_persistent_position_until_exit():
    data = _market_data([10, 11, 12], [1, 0, 0])

    result = run_long_only_backtest(
        data,
        initial_capital=100000,
        max_position=1,
        slippage=0,
        cost_calculator=_zero_cost(),
    )

    assert result["trades"] == 1
    assert result["positions"] == [10000, 10000, 10000]
    assert result["equity_curve"] == [100000, 110000, 120000]
    assert math.isclose(result["total_returns"], 0.2)
    assert result["annual_return"] > result["total_returns"]


def test_sell_signal_closes_position_and_records_trade():
    data = _market_data([10, 11, 12, 13], [1, 0, -1, 0])

    result = run_long_only_backtest(
        data,
        initial_capital=100000,
        max_position=1,
        slippage=0,
        cost_calculator=_zero_cost(),
    )

    assert result["trades"] == 2
    assert result["closed_trades"] == 1
    assert result["winning_trades"] == 1
    assert result["positions"] == [10000, 10000, 0, 0]
    assert result["equity_curve"] == [100000, 110000, 120000, 120000]
    assert result["trade_records"][0]["pnl"] == 20000


def test_cost_and_slippage_reduce_final_equity():
    data = _market_data([10, 10, 10], [1, 0, -1])

    no_cost = run_long_only_backtest(
        data,
        initial_capital=100000,
        max_position=1,
        slippage=0,
        cost_calculator=_zero_cost(),
    )
    with_cost = run_long_only_backtest(
        data,
        initial_capital=100000,
        max_position=1,
    )

    assert no_cost["final_capital"] == 100000
    assert with_cost["final_capital"] < no_cost["final_capital"]
    assert with_cost["total_cost"] > 0

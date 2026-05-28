import math

import pandas as pd

from agents.backtest.trading_cost import TradingCostCalculator
from agents.backtest.vectorized_strategies import run_long_only_backtest, split_vectorized_params


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
    assert math.isclose(result["benchmark_return"], 0.3)
    assert math.isclose(result["alpha"], -0.3)


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
    assert math.isclose(result["benchmark_return"], 0.2)
    assert math.isclose(result["alpha"], 0)
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


def test_lot_size_can_handle_high_adjusted_prices():
    data = _market_data([12000, 13000, 14000], [1, 0, -1])

    default_lot = run_long_only_backtest(
        data,
        initial_capital=100000,
        max_position=1,
        slippage=0,
        cost_calculator=_zero_cost(),
    )
    one_share_lot = run_long_only_backtest(
        data,
        initial_capital=100000,
        max_position=1,
        lot_size=1,
        slippage=0,
        cost_calculator=_zero_cost(),
    )

    assert default_lot["trades"] == 0
    assert one_share_lot["trades"] == 2
    assert one_share_lot["positions"] == [8, 8, 0]
    assert one_share_lot["final_capital"] == 116000


def test_split_vectorized_params_separates_execution_settings():
    strategy_params, execution_params = split_vectorized_params(
        {
            "short_period": 5,
            "long_period": 20,
            "lot_size": "1",
            "max_position": "0.8",
            "slippage": "0.002",
        }
    )

    assert strategy_params == {"short_period": 5, "long_period": 20}
    assert execution_params == {
        "lot_size": 1,
        "max_position": 0.8,
        "slippage": 0.002,
    }


def test_split_vectorized_params_rejects_invalid_execution_settings():
    try:
        split_vectorized_params({"lot_size": 0})
    except ValueError as exc:
        assert "lot_size" in str(exc)
    else:
        raise AssertionError("expected invalid lot_size to fail")

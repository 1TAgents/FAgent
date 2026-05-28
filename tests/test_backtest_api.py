import asyncio

import pandas as pd
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from agents.backtest import api
from agents.backtest.models import BacktestRequest


class _FakeDataLoader:
    def load_klines(self, *args, **kwargs):
        dates = pd.date_range("2024-01-01", periods=3, freq="D")
        return pd.DataFrame(
            {
                "symbol": ["SH600519"] * 3,
                "open": [12000, 13000, 14000],
                "high": [12000, 13000, 14000],
                "low": [12000, 13000, 14000],
                "close": [12000, 13000, 14000],
                "volume": [100000] * 3,
            },
            index=dates,
        )


class _FakeRunStore:
    def persist_run(self, request, report, engine):
        return "test-report", "data/backtests/test-report"


def test_run_backtest_applies_vectorized_execution_params(monkeypatch):
    monkeypatch.setattr(api, "get_data_loader", lambda: _FakeDataLoader())
    monkeypatch.setattr(api, "get_run_store", lambda: _FakeRunStore())

    response = asyncio.run(
        api.run_backtest(
            BacktestRequest(
                strategy_name="momentum",
                symbol="600519",
                start_date="2024-01-01",
                end_date="2024-01-03",
                params={
                    "lookback": 1,
                    "threshold": 0,
                    "lot_size": 1,
                    "slippage": 0,
                    "max_position": 1,
                },
            )
        )
    )

    assert response.success is True
    assert response.engine == "vectorized"
    assert response.report is not None
    assert response.report.metrics.total_trades == 1
    assert response.report.metrics.benchmark_return == pytest.approx(16.6666666667)
    assert response.report.metrics.alpha is not None


def test_list_strategies_includes_vectorized_classic_horizon_metadata():
    response = asyncio.run(api.list_strategies())

    strategies = response["strategies"]
    assert strategies["rsi2"]["horizon"] == "短线"
    assert strategies["donchian_breakout"]["vectorized"] is True
    assert strategies["sma_trend"]["default_params"] == {"ma_period": 200}
    assert strategies["dual_ma"]["classic"] is True


def test_grid_search_accepts_json_body_and_fixed_params(monkeypatch):
    monkeypatch.setattr(api, "get_data_loader", lambda: _FakeDataLoader())
    app = FastAPI()
    app.include_router(api.router)
    client = TestClient(app)

    response = client.post(
        "/backtest/grid_search",
        json={
            "strategy_name": "momentum",
            "symbol": "600519",
            "start_date": "2024-01-01",
            "end_date": "2024-01-03",
            "param_grid": {"lookback": [1], "threshold": [0]},
            "fixed_params": {"lot_size": 1, "slippage": 0, "max_position": 1},
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["total_combinations"] == 1
    assert payload["best_params"]["lot_size"] == 1

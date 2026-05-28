import pandas as pd
import pytest

from agents.backtest.data_loader import BacktestDataLoader


pytest.importorskip("pyarrow")


def _write_snapshot(base_dir, year, rows):
    snapshot_dir = base_dir / "feature_snapshots"
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_parquet(snapshot_dir / f"model_features_{year}.parquet")


def test_load_klines_reads_quantmind_feature_snapshots(tmp_path):
    _write_snapshot(
        tmp_path,
        2024,
        [
            {
                "symbol": "SH600519",
                "trade_date": "2024-01-02",
                "open": 100.0,
                "high": 101.0,
                "low": 99.0,
                "close": 100.5,
                "volume": 1000,
                "liq_amount": 100500.0,
            },
            {
                "symbol": "SZ000001",
                "trade_date": "2024-01-02",
                "open": 10.0,
                "high": 11.0,
                "low": 9.0,
                "close": 10.5,
                "volume": 2000,
                "liq_amount": 21000.0,
            },
            {
                "symbol": "SH600519",
                "trade_date": "2024-01-03",
                "open": 101.0,
                "high": 102.0,
                "low": 100.0,
                "close": 101.5,
                "volume": 1100,
                "liq_amount": 111650.0,
            },
        ],
    )
    loader = BacktestDataLoader(quantmind_dir=tmp_path)

    data = loader.load_klines("600519", "2024-01-01", "2024-01-04")

    assert list(data.index.strftime("%Y-%m-%d")) == ["2024-01-02", "2024-01-03"]
    assert data["symbol"].tolist() == ["SH600519", "SH600519"]
    assert data["close"].tolist() == [100.5, 101.5]
    assert data["turnover"].tolist() == [100500.0, 111650.0]


def test_quantmind_loader_reads_cross_year_range(tmp_path):
    _write_snapshot(
        tmp_path,
        2024,
        [
            {
                "symbol": "SH600519",
                "trade_date": "2024-12-31",
                "open": 100.0,
                "high": 105.0,
                "low": 99.0,
                "close": 104.0,
                "volume": 1000,
            }
        ],
    )
    _write_snapshot(
        tmp_path,
        2025,
        [
            {
                "symbol": "SH600519",
                "trade_date": "2025-01-02",
                "open": 104.0,
                "high": 106.0,
                "low": 103.0,
                "close": 105.0,
                "volume": 1200,
            }
        ],
    )
    loader = BacktestDataLoader(quantmind_dir=tmp_path / "feature_snapshots")

    data = loader.load_klines("SH600519", "2024-12-30", "2025-01-03")

    assert list(data.index.strftime("%Y-%m-%d")) == ["2024-12-31", "2025-01-02"]
    assert data["close"].tolist() == [104.0, 105.0]

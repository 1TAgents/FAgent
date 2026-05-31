#!/usr/bin/env python3
"""Import local QuantMInd daily data into FAgent's stock_data SQLite DB."""

from __future__ import annotations

import argparse
import math
import os
import sqlite3
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROJECT_QUANTMIND_SOURCE = PROJECT_ROOT / "data" / "QuantMInd"
EXTERNAL_QUANTMIND_SOURCE = Path("~/Learning/quant_repos/data/QuantMInd").expanduser()
DEFAULT_DB = PROJECT_ROOT / "data" / "stock_data.db"

SYMBOL_NAMES = {
    "000001": "平安银行",
    "000002": "万科A",
    "000300": "沪深300",
    "000333": "美的集团",
    "000651": "格力电器",
    "002415": "海康威视",
    "300750": "宁德时代",
    "600000": "浦发银行",
    "600030": "中信证券",
    "600036": "招商银行",
    "600519": "贵州茅台",
    "601318": "中国平安",
    "601398": "工商银行",
    "601857": "中国石油",
}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", default=str(default_source()), help="QuantMInd root or qlib_data directory")
    parser.add_argument("--db", default=str(DEFAULT_DB), help="target SQLite DB path")
    parser.add_argument("--as-of-date", default=None, help="only import rows up to this date, e.g. 2026-04-24")
    parser.add_argument("--symbols", nargs="*", default=None, help="optional symbol filter, e.g. 600519 000001")
    parser.add_argument("--limit-symbols", type=int, default=None, help="import first N instruments for smoke testing")
    parser.add_argument("--replace", action="store_true", help="replace existing A-share stocks and daily klines")
    parser.add_argument("--batch-size", type=int, default=50000)
    args = parser.parse_args()

    source = resolve_qlib_dir(Path(args.source).expanduser())
    db_path = Path(args.db)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    as_of_date = normalize_date(args.as_of_date)
    wanted = {normalize_symbol(s) for s in args.symbols} if args.symbols else None

    calendars = pd.to_datetime((source / "calendars" / "day.txt").read_text().splitlines())
    instruments = load_instruments(source / "instruments" / "all.txt", wanted, args.limit_symbols)

    conn = sqlite3.connect(db_path)
    try:
        init_tables(conn)
        tune_sqlite(conn)
        if args.replace:
            conn.execute("DELETE FROM klines WHERE period = 'daily'")
            conn.execute("DELETE FROM stocks WHERE market = 'A'")
            conn.commit()

        import_stocks(conn, instruments)

        total_rows = 0
        for idx, qlib_symbol in enumerate(instruments, start=1):
            rows = load_symbol_rows(source, qlib_symbol, calendars, as_of_date)
            if not rows:
                continue
            code = normalize_symbol(qlib_symbol)
            for batch in chunks(rows, args.batch_size):
                conn.executemany(
                    """
                    INSERT OR REPLACE INTO klines
                    (symbol, period, date, open, high, low, close, volume, turnover, change_percent)
                    VALUES (?, 'daily', ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    [(code, *row) for row in batch],
                )
            total_rows += len(rows)
            if idx % 200 == 0:
                conn.commit()
                print(f"imported symbols={idx}/{len(instruments)} rows={total_rows}")

        conn.execute(
            """
            INSERT OR REPLACE INTO sync_meta (key, value, updated_at)
            VALUES ('quantmind_import_source', ?, CURRENT_TIMESTAMP)
            """,
            (str(source),),
        )
        if as_of_date:
            conn.execute(
                """
                INSERT OR REPLACE INTO sync_meta (key, value, updated_at)
                VALUES ('quantmind_import_as_of_date', ?, CURRENT_TIMESTAMP)
                """,
                (as_of_date,),
            )
        conn.execute(
            """
            INSERT INTO sync_log (sync_type, records_count, status)
            VALUES ('quantmind_import', ?, 'success')
            """,
            (total_rows,),
        )
        conn.commit()
    finally:
        conn.close()

    print(f"done db={db_path} symbols={len(instruments)} rows={total_rows}")
    return 0


def default_source() -> Path:
    env_source = os.getenv("QUANTMIND_DATA_DIR")
    if env_source:
        return Path(env_source).expanduser()
    if PROJECT_QUANTMIND_SOURCE.exists():
        return PROJECT_QUANTMIND_SOURCE
    return EXTERNAL_QUANTMIND_SOURCE


def resolve_qlib_dir(path: Path) -> Path:
    if (path / "qlib_data").is_dir():
        path = path / "qlib_data"
    required = [path / "calendars" / "day.txt", path / "instruments" / "all.txt", path / "features"]
    missing = [str(p) for p in required if not p.exists()]
    if missing:
        raise SystemExit(f"Invalid QuantMInd qlib_data path. Missing: {', '.join(missing)}")
    return path


def init_tables(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS stocks (
            symbol TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            market TEXT NOT NULL,
            list_date TEXT,
            industry TEXT,
            area TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_stocks_market ON stocks(market);

        CREATE TABLE IF NOT EXISTS klines (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            period TEXT NOT NULL DEFAULT 'daily',
            date TEXT NOT NULL,
            open REAL,
            high REAL,
            low REAL,
            close REAL,
            volume INTEGER,
            turnover REAL,
            change_percent REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(symbol, period, date)
        );
        CREATE INDEX IF NOT EXISTS idx_klines_symbol_date ON klines(symbol, period, date);

        CREATE TABLE IF NOT EXISTS sync_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sync_type TEXT NOT NULL,
            symbol TEXT,
            records_count INTEGER,
            status TEXT,
            error TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS sync_meta (
            key TEXT PRIMARY KEY,
            value TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
    )


def tune_sqlite(conn: sqlite3.Connection) -> None:
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA temp_store=MEMORY")


def load_instruments(path: Path, wanted: set[str] | None, limit: int | None) -> list[str]:
    instruments: list[str] = []
    for line in path.read_text().splitlines():
        parts = line.split()
        if not parts:
            continue
        qlib_symbol = parts[0].lower()
        code = normalize_symbol(qlib_symbol)
        if wanted and code not in wanted:
            continue
        instruments.append(qlib_symbol)
        if limit and len(instruments) >= limit:
            break
    return instruments


def import_stocks(conn: sqlite3.Connection, instruments: Iterable[str]) -> None:
    rows = []
    for qlib_symbol in instruments:
        code = normalize_symbol(qlib_symbol)
        rows.append((code, SYMBOL_NAMES.get(code, code), "A"))
    conn.executemany(
        """
        INSERT OR REPLACE INTO stocks (symbol, name, market, updated_at)
        VALUES (?, ?, ?, CURRENT_TIMESTAMP)
        """,
        rows,
    )
    conn.commit()


def load_symbol_rows(
    qlib_dir: Path,
    qlib_symbol: str,
    calendars: pd.DatetimeIndex,
    as_of_date: str | None,
) -> list[tuple]:
    feature_dir = qlib_dir / "features" / qlib_symbol
    if not feature_dir.is_dir():
        return []

    fields = {}
    for field in ("open", "high", "low", "close", "volume", "amount", "factor", "change"):
        path = feature_dir / f"{field}.day.bin"
        if path.exists():
            fields[field] = read_qlib_bin(path)

    required = {"open", "high", "low", "close", "volume"}
    if not required.issubset(fields):
        return []

    length = min(len(fields[field]["values"]) for field in required)
    start_idx = max(fields[field]["start"] for field in required)
    if length <= 0 or start_idx >= len(calendars):
        return []

    end_idx = min(start_idx + length, len(calendars))
    dates = calendars[start_idx:end_idx]
    if as_of_date:
        mask = dates <= pd.Timestamp(as_of_date)
        dates = dates[mask]
        length = len(dates)
    else:
        length = len(dates)

    values = {field: align_values(data, start_idx, length) for field, data in fields.items()}
    factor = values.get("factor")
    if factor is None:
        factor = np.ones(length)
    factor = np.where(np.isfinite(factor) & (factor != 0), factor, 1.0)

    rows = []
    for i in range(length):
        open_price = safe_float(values["open"][i] / factor[i])
        high_price = safe_float(values["high"][i] / factor[i])
        low_price = safe_float(values["low"][i] / factor[i])
        close_price = safe_float(values["close"][i] / factor[i])
        volume = int(safe_float(values["volume"][i]))
        turnover = safe_float(values["amount"][i]) if "amount" in values else None
        change_percent = safe_float(values["change"][i] * 100) if "change" in values else None
        if not all(math.isfinite(v) for v in (open_price, high_price, low_price, close_price)):
            continue
        rows.append(
            (
                dates[i].strftime("%Y-%m-%d"),
                open_price,
                high_price,
                low_price,
                close_price,
                volume,
                turnover,
                change_percent,
            )
        )
    return rows


def read_qlib_bin(path: Path) -> dict:
    raw = np.fromfile(path, dtype="<f4")
    if raw.size == 0:
        return {"start": 0, "values": np.array([], dtype=float)}
    return {"start": int(raw[0]), "values": raw[1:].astype(float)}


def align_values(data: dict, start_idx: int, length: int) -> np.ndarray:
    offset = start_idx - data["start"]
    if offset < 0:
        prefix = np.full(abs(offset), np.nan)
        arr = np.concatenate([prefix, data["values"]])
        offset = 0
    else:
        arr = data["values"]
    out = arr[offset : offset + length]
    if len(out) < length:
        out = np.concatenate([out, np.full(length - len(out), np.nan)])
    return out


def chunks(rows: list[tuple], size: int):
    for i in range(0, len(rows), size):
        yield rows[i : i + size]


def normalize_symbol(symbol: str) -> str:
    raw = str(symbol).strip().upper()
    raw = raw.replace(".XSHG", "").replace(".XSHE", "")
    if raw.startswith(("SH", "SZ", "BJ")):
        raw = raw[2:]
    if raw.endswith((".SH", ".SZ", ".BJ")):
        raw = raw[:-3]
    return raw


def normalize_date(value: str | None) -> str | None:
    if not value:
        return None
    text = str(value).strip()
    if len(text) == 8 and text.isdigit():
        return f"{text[:4]}-{text[4:6]}-{text[6:]}"
    return text[:10]


def safe_float(value) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return 0.0
    return result if math.isfinite(result) else 0.0


if __name__ == "__main__":
    raise SystemExit(main())

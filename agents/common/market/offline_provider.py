"""Offline market data provider backed by the local stock_data SQLite DB."""

from __future__ import annotations

import os
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional, List

from .models import KLineData, KLinePeriod, Market, StockInfo, StockQuote

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_DB_PATH = PROJECT_ROOT / "data" / "stock_data.db"


class OfflineMarketDataProvider:
    """Read A-share daily market data from the local project database."""

    def __init__(self, db_path: str | Path | None = None, as_of_date: str | None = None):
        self.db_path = _resolve_db_path(db_path or os.getenv("FAGENT_MARKET_DB_PATH") or DEFAULT_DB_PATH)
        self.as_of_date = _normalize_date(as_of_date or os.getenv("FAGENT_MARKET_AS_OF_DATE"))

    @property
    def enabled(self) -> bool:
        return self.db_path.exists()

    def get_last_trade_date(self) -> Optional[str]:
        if not self.enabled:
            return None

        where = ""
        params: list = []
        if self.as_of_date:
            where = "WHERE date <= ?"
            params.append(self.as_of_date)

        with self._connect() as conn:
            row = conn.execute(f"SELECT MAX(date) AS date FROM klines {where}", params).fetchone()
            return str(row["date"]) if row and row["date"] else None

    def get_quote(self, symbol: str) -> Optional[StockQuote]:
        code = normalize_symbol(symbol)
        if not code or not self.enabled:
            return None

        rows = self._latest_rows(code, limit=2)
        if not rows:
            return None

        latest = rows[0]
        prev = rows[1] if len(rows) > 1 else None
        prev_close = _float(prev["close"]) if prev else _float(latest["open"])
        price = _float(latest["close"])
        change = price - prev_close if prev_close else 0.0
        change_pct = _float(latest["change_percent"])
        if not change_pct and prev_close:
            change_pct = change / prev_close * 100

        return StockQuote(
            symbol=code,
            name=self._stock_name(code),
            price=price,
            change=change,
            change_pct=change_pct,
            open=_float(latest["open"]),
            high=_float(latest["high"]),
            low=_float(latest["low"]),
            prev_close=prev_close,
            volume=int(_float(latest["volume"])),
            amount=_float(latest["turnover"]),
            timestamp=datetime.fromisoformat(f"{latest['date']}T15:00:00"),
            market=Market.A_SHARE,
            trade_date=datetime.strptime(str(latest["date"]), "%Y-%m-%d").date(),
            source="local:stock_data.db",
            is_realtime=False,
            note="这是本地离线日线快照，不是实时行情。",
        )

    def get_kline(
        self,
        symbol: str,
        period: KLinePeriod = KLinePeriod.DAILY,
        count: int = 100,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> Optional[KLineData]:
        code = normalize_symbol(symbol)
        if not code or not self.enabled or period != KLinePeriod.DAILY:
            return None

        requested_end = _normalize_date(end_date)
        end = self._effective_end_date(end_date)
        start = _normalize_date(start_date)

        with self._connect() as conn:
            if start or requested_end:
                query = """
                    SELECT date, open, high, low, close, volume, turnover, change_percent
                    FROM klines
                    WHERE symbol = ? AND period = 'daily'
                """
                params: list = [code]
                if start:
                    query += " AND date >= ?"
                    params.append(start)
                if end:
                    query += " AND date <= ?"
                    params.append(end)
                query += " ORDER BY date ASC"
                rows = conn.execute(query, params).fetchall()
            else:
                rows = conn.execute(
                    """
                    SELECT * FROM (
                        SELECT date, open, high, low, close, volume, turnover, change_percent
                        FROM klines
                        WHERE symbol = ? AND period = 'daily'
                          AND (? IS NULL OR date <= ?)
                        ORDER BY date DESC
                        LIMIT ?
                    ) ORDER BY date ASC
                    """,
                    (code, end, end, count),
                ).fetchall()

        if not rows:
            return None

        data = [
            {
                "date": str(row["date"]),
                "open": _float(row["open"]),
                "high": _float(row["high"]),
                "low": _float(row["low"]),
                "close": _float(row["close"]),
                "volume": int(_float(row["volume"])),
                "amount": _float(row["turnover"]),
                "change_percent": _float(row["change_percent"]),
            }
            for row in rows
        ]
        latest_date = data[-1]["date"]
        return KLineData(
            symbol=code,
            period=period,
            data=data,
            source="local:stock_data.db",
            as_of_date=latest_date,
            note="本地离线日线数据，不是实时行情。",
        )

    def search(self, keyword: str, limit: int = 10) -> List[StockInfo]:
        if not self.enabled:
            return []

        term = keyword.strip()
        if not term:
            return []

        like = f"%{term}%"
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT symbol, name, market, industry
                FROM stocks
                WHERE market = 'A' AND (symbol LIKE ? OR name LIKE ?)
                ORDER BY
                    CASE WHEN symbol = ? THEN 0 WHEN name = ? THEN 1 ELSE 2 END,
                    symbol
                LIMIT ?
                """,
                (like, like, normalize_symbol(term), term, limit),
            ).fetchall()

        return [
            StockInfo(
                symbol=str(row["symbol"]),
                name=str(row["name"]),
                market=Market.A_SHARE,
                industry=str(row["industry"]) if row["industry"] else None,
            )
            for row in rows
        ]

    def _latest_rows(self, symbol: str, limit: int = 2) -> list[sqlite3.Row]:
        end = self._effective_end_date(None)
        query = """
            SELECT date, open, high, low, close, volume, turnover, change_percent
            FROM klines
            WHERE symbol = ? AND period = 'daily'
        """
        params: list = [symbol]
        if end:
            query += " AND date <= ?"
            params.append(end)
        query += " ORDER BY date DESC LIMIT ?"
        params.append(limit)

        with self._connect() as conn:
            return conn.execute(query, params).fetchall()

    def _stock_name(self, symbol: str) -> str:
        with self._connect() as conn:
            row = conn.execute("SELECT name FROM stocks WHERE symbol = ? LIMIT 1", (symbol,)).fetchone()
        return str(row["name"]) if row and row["name"] else symbol

    def _effective_end_date(self, requested: str | None) -> Optional[str]:
        requested_date = _normalize_date(requested)
        if requested_date and self.as_of_date:
            return min(requested_date, self.as_of_date)
        return requested_date or self.as_of_date

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn


def normalize_symbol(symbol: str) -> str:
    raw = str(symbol or "").strip().upper()
    raw = raw.replace(".XSHG", "").replace(".XSHE", "")
    if raw.startswith(("SH", "SZ", "BJ")) and len(raw) >= 8:
        raw = raw[2:]
    if raw.endswith((".SH", ".SZ", ".BJ")):
        raw = raw[:-3]
    return raw


def _resolve_db_path(value: str | Path) -> Path:
    path = Path(value).expanduser()
    if path.is_absolute():
        return path
    return PROJECT_ROOT / path


def _normalize_date(value: str | None) -> Optional[str]:
    if not value:
        return None
    text = str(value).strip()
    if not text:
        return None
    if len(text) == 8 and text.isdigit():
        return f"{text[:4]}-{text[4:6]}-{text[6:]}"
    return text[:10]


def _float(value) -> float:
    if value is None:
        return 0.0
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0

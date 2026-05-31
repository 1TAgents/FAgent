import sqlite3
from datetime import date

from agents.common.market import KLinePeriod
from agents.common.market.offline_provider import OfflineMarketDataProvider


def _init_db(path):
    conn = sqlite3.connect(path)
    conn.executescript(
        """
        CREATE TABLE stocks (
            symbol TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            market TEXT NOT NULL,
            list_date TEXT,
            industry TEXT,
            area TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE klines (
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
        """
    )
    conn.execute("INSERT INTO stocks (symbol, name, market) VALUES ('600519', '贵州茅台', 'A')")
    conn.executemany(
        """
        INSERT INTO klines
        (symbol, period, date, open, high, low, close, volume, turnover, change_percent)
        VALUES ('600519', 'daily', ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            ("2026-04-23", 1408.0, 1420.0, 1400.0, 1418.0, 1000, 1.0e8, 0.2),
            ("2026-04-24", 1413.1, 1458.88, 1413.1, 1458.49, 2000, 2.0e8, 2.86),
            ("2026-04-25", 1500.0, 1510.0, 1490.0, 1505.0, 3000, 3.0e8, 3.19),
        ],
    )
    conn.commit()
    conn.close()


def test_provider_respects_fixed_as_of_date(tmp_path):
    db_path = tmp_path / "stock_data.db"
    _init_db(db_path)
    provider = OfflineMarketDataProvider(db_path=db_path, as_of_date="2026-04-24")

    quote = provider.get_quote("SH600519")
    kline = provider.get_kline("600519", KLinePeriod.DAILY, count=10)

    assert quote is not None
    assert quote.trade_date == date(2026, 4, 24)
    assert quote.price == 1458.49
    assert quote.name == "贵州茅台"
    assert quote.is_realtime is False
    assert "离线历史数据" in quote.summary()

    assert kline is not None
    assert [row["date"] for row in kline.data] == ["2026-04-23", "2026-04-24"]
    assert kline.as_of_date == "2026-04-24"

    limited = provider.get_kline("600519", KLinePeriod.DAILY, count=1)
    assert limited is not None
    assert [row["date"] for row in limited.data] == ["2026-04-24"]


def test_provider_searches_local_stock_names(tmp_path):
    db_path = tmp_path / "stock_data.db"
    _init_db(db_path)
    provider = OfflineMarketDataProvider(db_path=db_path, as_of_date="2026-04-24")

    results = provider.search("茅台")

    assert len(results) == 1
    assert results[0].symbol == "600519"
    assert results[0].name == "贵州茅台"

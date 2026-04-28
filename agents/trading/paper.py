"""
Paper Trading Service

本模块只做本地模拟交易，不连接任何真实券商或交易网关。
"""
from __future__ import annotations

import os
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from agents.backtest.trading_cost import TradingCostCalculator


DEFAULT_ACCOUNT_ID = "default"
DEFAULT_INITIAL_CASH = 1_000_000.0


class PaperTradingService:
    """SQLite-backed paper broker for local simulation."""

    def __init__(self, db_path: str = "data/paper_trading.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.cost_calculator = TradingCostCalculator()
        self._init_database()
        self.ensure_account(DEFAULT_ACCOUNT_ID)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_database(self) -> None:
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS paper_accounts (
                    account_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    initial_cash REAL NOT NULL,
                    cash REAL NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS paper_positions (
                    account_id TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    quantity INTEGER NOT NULL,
                    avg_cost REAL NOT NULL,
                    last_price REAL NOT NULL,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY (account_id, symbol)
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS paper_orders (
                    order_id TEXT PRIMARY KEY,
                    account_id TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    side TEXT NOT NULL,
                    quantity INTEGER NOT NULL,
                    price REAL NOT NULL,
                    order_type TEXT NOT NULL,
                    status TEXT NOT NULL,
                    reason TEXT,
                    error TEXT,
                    cost REAL NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_paper_orders_account ON paper_orders(account_id, created_at)")
            conn.commit()

    def ensure_account(
        self,
        account_id: str = DEFAULT_ACCOUNT_ID,
        *,
        name: str = "默认模拟账户",
        initial_cash: float = DEFAULT_INITIAL_CASH,
    ) -> Dict[str, Any]:
        now = datetime.now().isoformat()
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM paper_accounts WHERE account_id = ?",
                (account_id,),
            ).fetchone()
            if row:
                return dict(row)

            conn.execute(
                """
                INSERT INTO paper_accounts (account_id, name, initial_cash, cash, status, created_at, updated_at)
                VALUES (?, ?, ?, ?, 'active', ?, ?)
                """,
                (account_id, name, initial_cash, initial_cash, now, now),
            )
            conn.commit()

        return self.get_account(account_id)

    def get_account(self, account_id: str = DEFAULT_ACCOUNT_ID) -> Dict[str, Any]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM paper_accounts WHERE account_id = ?",
                (account_id,),
            ).fetchone()
            if row is None:
                raise ValueError(f"模拟账户不存在：{account_id}")
            return dict(row)

    def place_order(
        self,
        *,
        symbol: str,
        side: str,
        quantity: int,
        price: float,
        account_id: str = DEFAULT_ACCOUNT_ID,
        order_type: str = "market",
        reason: str = "",
    ) -> Dict[str, Any]:
        """Place and immediately fill a paper market order."""
        self.ensure_account(account_id)
        side = side.lower().strip()
        symbol = symbol.strip()
        quantity = int(quantity)
        price = float(price)
        order_id = f"po_{uuid.uuid4().hex[:12]}"
        now = datetime.now().isoformat()

        error = self._validate_order(symbol, side, quantity, price)
        if error:
            return self._persist_rejected_order(order_id, account_id, symbol, side, quantity, price, order_type, reason, error, now)

        with self._connect() as conn:
            account = dict(conn.execute(
                "SELECT * FROM paper_accounts WHERE account_id = ?",
                (account_id,),
            ).fetchone())
            position_row = conn.execute(
                "SELECT * FROM paper_positions WHERE account_id = ? AND symbol = ?",
                (account_id, symbol),
            ).fetchone()
            position = dict(position_row) if position_row else None

            if side == "buy":
                if quantity % 100 != 0:
                    return self._persist_rejected_order(
                        order_id, account_id, symbol, side, quantity, price, order_type, reason,
                        "A 股模拟买入数量必须是 100 股整数倍", now,
                    )
                cost = self.cost_calculator.calculate_cost(price, quantity, "buy")
                total_cash_needed = price * quantity + cost
                if total_cash_needed > account["cash"]:
                    return self._persist_rejected_order(
                        order_id, account_id, symbol, side, quantity, price, order_type, reason,
                        "模拟账户现金不足", now,
                    )
                self._fill_buy(conn, account_id, symbol, quantity, price, cost, account["cash"], now)

            elif side == "sell":
                held_quantity = int(position["quantity"]) if position else 0
                if quantity > held_quantity:
                    return self._persist_rejected_order(
                        order_id, account_id, symbol, side, quantity, price, order_type, reason,
                        "模拟持仓不足", now,
                    )
                cost = self.cost_calculator.calculate_cost(price, quantity, "sell")
                self._fill_sell(conn, account_id, symbol, quantity, price, cost, account["cash"], position, now)

            else:
                return self._persist_rejected_order(
                    order_id, account_id, symbol, side, quantity, price, order_type, reason,
                    "side 仅支持 buy/sell", now,
                )

            conn.execute(
                """
                INSERT INTO paper_orders
                (order_id, account_id, symbol, side, quantity, price, order_type, status, reason, error, cost, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, 'filled', ?, NULL, ?, ?, ?)
                """,
                (order_id, account_id, symbol, side, quantity, price, order_type, reason, cost, now, now),
            )
            conn.commit()

        return {"success": True, "order": self.get_order(order_id), "snapshot": self.get_snapshot(account_id)}

    def cancel_order(self, order_id: str) -> Dict[str, Any]:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM paper_orders WHERE order_id = ?", (order_id,)).fetchone()
            if row is None:
                return {"success": False, "error": f"模拟订单不存在：{order_id}"}
            order = dict(row)
            if order["status"] != "pending":
                return {
                    "success": False,
                    "error": f"模拟订单 `{order_id}` 当前状态为 `{order['status']}`，不能撤单",
                    "order": order,
                }

            now = datetime.now().isoformat()
            conn.execute(
                "UPDATE paper_orders SET status = 'cancelled', updated_at = ? WHERE order_id = ?",
                (now, order_id),
            )
            conn.commit()

        return {"success": True, "order": self.get_order(order_id)}

    def get_order(self, order_id: str) -> Dict[str, Any]:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM paper_orders WHERE order_id = ?", (order_id,)).fetchone()
            if row is None:
                raise ValueError(f"模拟订单不存在：{order_id}")
            return dict(row)

    def get_snapshot(self, account_id: str = DEFAULT_ACCOUNT_ID) -> Dict[str, Any]:
        account = self.ensure_account(account_id)
        positions = self.get_positions(account_id)
        position_value = sum(item["market_value"] for item in positions)
        total_value = float(account["cash"]) + position_value
        return {
            "account_id": account_id,
            "cash": float(account["cash"]),
            "initial_cash": float(account["initial_cash"]),
            "position_value": position_value,
            "total_value": total_value,
            "total_pnl": total_value - float(account["initial_cash"]),
            "position_ratio": position_value / total_value if total_value else 0.0,
            "positions": positions,
        }

    def get_positions(self, account_id: str = DEFAULT_ACCOUNT_ID) -> list[Dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT account_id, symbol, quantity, avg_cost, last_price, updated_at
                FROM paper_positions
                WHERE account_id = ? AND quantity > 0
                ORDER BY symbol
                """,
                (account_id,),
            ).fetchall()

        positions = []
        for row in rows:
            item = dict(row)
            item["market_value"] = float(item["quantity"]) * float(item["last_price"])
            item["unrealized_pnl"] = (float(item["last_price"]) - float(item["avg_cost"])) * int(item["quantity"])
            item["unrealized_pnl_percent"] = (
                item["unrealized_pnl"] / (float(item["avg_cost"]) * int(item["quantity"]))
                if item["avg_cost"] and item["quantity"] else 0.0
            )
            positions.append(item)
        return positions

    def _fill_buy(
        self,
        conn: sqlite3.Connection,
        account_id: str,
        symbol: str,
        quantity: int,
        price: float,
        cost: float,
        cash: float,
        now: str,
    ) -> None:
        row = conn.execute(
            "SELECT * FROM paper_positions WHERE account_id = ? AND symbol = ?",
            (account_id, symbol),
        ).fetchone()
        if row:
            position = dict(row)
            old_quantity = int(position["quantity"])
            new_quantity = old_quantity + quantity
            total_cost = float(position["avg_cost"]) * old_quantity + price * quantity
            avg_cost = total_cost / new_quantity
            conn.execute(
                """
                UPDATE paper_positions
                SET quantity = ?, avg_cost = ?, last_price = ?, updated_at = ?
                WHERE account_id = ? AND symbol = ?
                """,
                (new_quantity, avg_cost, price, now, account_id, symbol),
            )
        else:
            conn.execute(
                """
                INSERT INTO paper_positions (account_id, symbol, quantity, avg_cost, last_price, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (account_id, symbol, quantity, price, price, now),
            )

        conn.execute(
            "UPDATE paper_accounts SET cash = ?, updated_at = ? WHERE account_id = ?",
            (cash - price * quantity - cost, now, account_id),
        )

    def _fill_sell(
        self,
        conn: sqlite3.Connection,
        account_id: str,
        symbol: str,
        quantity: int,
        price: float,
        cost: float,
        cash: float,
        position: Dict[str, Any],
        now: str,
    ) -> None:
        remaining = int(position["quantity"]) - quantity
        if remaining > 0:
            conn.execute(
                """
                UPDATE paper_positions
                SET quantity = ?, last_price = ?, updated_at = ?
                WHERE account_id = ? AND symbol = ?
                """,
                (remaining, price, now, account_id, symbol),
            )
        else:
            conn.execute(
                "DELETE FROM paper_positions WHERE account_id = ? AND symbol = ?",
                (account_id, symbol),
            )

        conn.execute(
            "UPDATE paper_accounts SET cash = ?, updated_at = ? WHERE account_id = ?",
            (cash + price * quantity - cost, now, account_id),
        )

    def _validate_order(self, symbol: str, side: str, quantity: int, price: float) -> Optional[str]:
        if not symbol:
            return "缺少 symbol"
        if side not in {"buy", "sell"}:
            return "side 仅支持 buy/sell"
        if quantity <= 0:
            return "quantity 必须大于 0"
        if price <= 0:
            return "price 必须大于 0"
        return None

    def _persist_rejected_order(
        self,
        order_id: str,
        account_id: str,
        symbol: str,
        side: str,
        quantity: int,
        price: float,
        order_type: str,
        reason: str,
        error: str,
        now: str,
    ) -> Dict[str, Any]:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO paper_orders
                (order_id, account_id, symbol, side, quantity, price, order_type, status, reason, error, cost, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, 'rejected', ?, ?, 0, ?, ?)
                """,
                (order_id, account_id, symbol, side, quantity, price, order_type, reason, error, now, now),
            )
            conn.commit()
        return {"success": False, "error": error, "order": self.get_order(order_id)}


_paper_service: Optional[PaperTradingService] = None


def get_paper_trading_service(db_path: Optional[str] = None) -> PaperTradingService:
    global _paper_service
    resolved_path = db_path or os.getenv("PAPER_TRADING_DB_PATH", "data/paper_trading.db")
    if _paper_service is None or str(_paper_service.db_path) != resolved_path:
        _paper_service = PaperTradingService(resolved_path)
    return _paper_service

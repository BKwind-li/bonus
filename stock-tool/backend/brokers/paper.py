"""PaperBrokerAdapter — in-memory/SQLite paper trading engine.

Implements the :class:`~brokers.base.BrokerAdapter` Protocol using the
project's aiosqlite-backed database.  All mutating methods wrap their DB
work in an explicit ``BEGIN … COMMIT`` transaction and roll back on error.

Out-of-scope items (deferred to later tasks):
- Market-hours checking and closed-market queuing (Task 4 / Task 5)
- Limit-order matching / triggering (Task 5)
- NAV snapshot recording (Task 6)
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Callable

from brokers.base import (
    BrokerError,
    InsufficientFundsError,
    InsufficientPositionError,
    InvalidOrderError,
    OrderNotFoundError,
)
from config import settings
from data.universe import is_forex
from database import get_db
from models import AccountInfo, Order, OrderRequest, Position


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _row_to_order(row) -> Order:
    """Convert an aiosqlite Row to an :class:`~models.Order` Pydantic model."""
    return Order(
        id=row["id"],
        account_id=row["account_id"],
        ticker=row["ticker"],
        side=row["side"],
        order_type=row["order_type"],
        qty=row["qty"],
        limit_price=row["limit_price"],
        status=row["status"],
        fill_price=row["fill_price"],
        fill_qty=row["fill_qty"],
        fee=row["fee"],
        signal_label_short=row["signal_label_short"],
        signal_score_short=row["signal_score_short"],
        signal_label_long=row["signal_label_long"],
        signal_score_long=row["signal_score_long"],
        triggered_by=row["triggered_by"],
        created_at=row["created_at"],
        filled_at=row["filled_at"],
        cancelled_at=row["cancelled_at"],
    )


class PaperBrokerAdapter:
    """Synchronous-price, async-IO paper trading adapter.

    Parameters
    ----------
    price_fetcher:
        A *synchronous* callable ``(ticker: str) -> float | None``.
        Defaults to :func:`~services.data_fetcher.fetch_current_price`.
        Inject a lambda / mock in tests so no real network calls are made.
    """

    name = "paper"

    def __init__(self, price_fetcher: Callable[[str], float | None] | None = None):
        if price_fetcher is None:
            from services.data_fetcher import fetch_current_price
            price_fetcher = fetch_current_price
        self._price_fetcher = price_fetcher

    # ------------------------------------------------------------------ #
    # Read-only queries                                                    #
    # ------------------------------------------------------------------ #

    async def get_account(self, account_id: str) -> AccountInfo:
        async with get_db() as db:
            async with db.execute(
                "SELECT * FROM accounts WHERE id = ?", (account_id,)
            ) as cursor:
                row = await cursor.fetchone()
        if row is None:
            raise BrokerError(f"Account '{account_id}' not found")
        return AccountInfo(
            id=row["id"],
            type=row["type"],
            broker_adapter=row["broker_adapter"],
            display_name=row["display_name"],
            initial_cash=row["initial_cash"],
            cash_balance=row["cash_balance"],
            created_at=row["created_at"],
        )

    async def get_positions(self, account_id: str) -> list[Position]:
        async with get_db() as db:
            async with db.execute(
                "SELECT * FROM positions WHERE account_id = ?", (account_id,)
            ) as cursor:
                rows = await cursor.fetchall()
        return [
            Position(
                account_id=r["account_id"],
                ticker=r["ticker"],
                qty=r["qty"],
                avg_cost=r["avg_cost"],
                opened_at=r["opened_at"],
            )
            for r in rows
        ]

    async def get_orders(
        self, account_id: str, status: str | None = None
    ) -> list[Order]:
        async with get_db() as db:
            if status is None:
                async with db.execute(
                    "SELECT * FROM orders WHERE account_id = ? ORDER BY created_at DESC",
                    (account_id,),
                ) as cursor:
                    rows = await cursor.fetchall()
            else:
                async with db.execute(
                    "SELECT * FROM orders WHERE account_id = ? AND status = ? "
                    "ORDER BY created_at DESC",
                    (account_id, status),
                ) as cursor:
                    rows = await cursor.fetchall()
        return [_row_to_order(r) for r in rows]

    # ------------------------------------------------------------------ #
    # place_order                                                          #
    # ------------------------------------------------------------------ #

    async def place_order(
        self,
        account_id: str,
        request: OrderRequest,
        signal_snapshot: dict | None = None,
    ) -> Order:
        """Place a market or limit order.

        Market orders fill immediately against the current price (TODO: Task 4
        will add closed-market detection; Task 5 will queue them instead of
        filling when the market is closed).

        Limit orders are inserted with status=``pending`` and NO cash/position
        mutation; Task 5's matcher triggers them when the price crosses the
        limit.
        """
        # ── input validation ────────────────────────────────────────────
        if request.order_type not in ("market", "limit"):
            raise InvalidOrderError(
                f"order_type must be 'market' or 'limit', got '{request.order_type}'"
            )
        if request.side not in ("buy", "sell"):
            raise InvalidOrderError(
                f"side must be 'buy' or 'sell', got '{request.side}'"
            )
        # qty is already validated (gt=0) by Pydantic but be explicit:
        if request.qty <= 0:
            raise InvalidOrderError("qty must be > 0")

        if request.order_type == "limit":
            if request.limit_price is None or request.limit_price <= 0:
                raise InvalidOrderError(
                    "limit orders require a limit_price > 0"
                )
            return await self._place_limit_order(account_id, request, signal_snapshot)

        # market order
        return await self._place_market_order(account_id, request, signal_snapshot)

    # ------------------------------------------------------------------ #
    # Internal helpers — market orders                                     #
    # ------------------------------------------------------------------ #

    async def _place_market_order(
        self,
        account_id: str,
        request: OrderRequest,
        signal_snapshot: dict | None,
    ) -> Order:
        ticker = request.ticker
        qty = request.qty
        side = request.side

        # ── price lookup ────────────────────────────────────────────────
        mid_price = self._price_fetcher(ticker)
        if mid_price is None:
            raise BrokerError(f"price unavailable for {ticker}")

        # ── spread / fill_price calculation ─────────────────────────────
        # For FX pairs: adjust fill_price by the configured spread.
        # BUY  → effective price is slightly ABOVE mid (you pay more).
        # SELL → effective price is slightly BELOW mid (you receive less).
        # For stocks: no spread; fill_price == mid_price; fee == 0.
        if is_forex(ticker):
            spread_pct = settings.paper_fx_spread_pips / 10000.0
            if side == "buy":
                fill_price = mid_price * (1.0 + spread_pct)
            else:
                fill_price = mid_price * (1.0 - spread_pct)
            fee = abs(fill_price - mid_price) * qty
        else:
            fill_price = mid_price
            fee = 0.0

        total_cost = fill_price * qty

        if side == "buy":
            return await self._execute_market_buy(
                account_id, request, signal_snapshot, fill_price, fee, total_cost
            )
        else:
            return await self._execute_market_sell(
                account_id, request, signal_snapshot, fill_price, fee, total_cost
            )

    async def _execute_market_buy(
        self,
        account_id: str,
        request: OrderRequest,
        signal_snapshot: dict | None,
        fill_price: float,
        fee: float,
        total_cost: float,
    ) -> Order:
        ticker = request.ticker
        qty = request.qty

        # ── pre-check (outside transaction — read-only) ─────────────────
        async with get_db() as db:
            async with db.execute(
                "SELECT cash_balance FROM accounts WHERE id = ?", (account_id,)
            ) as cursor:
                acc_row = await cursor.fetchone()
        if acc_row is None:
            raise BrokerError(f"Account '{account_id}' not found")
        if acc_row["cash_balance"] < total_cost:
            raise InsufficientFundsError(
                f"Need {total_cost:.4f} but only {acc_row['cash_balance']:.4f} available"
            )

        # ── mutating transaction ─────────────────────────────────────────
        now = _now_iso()
        order_id = uuid.uuid4().hex
        snap = signal_snapshot or {}

        async with get_db() as db:
            await db.execute("BEGIN")
            try:
                # 1. Decrement cash
                await db.execute(
                    "UPDATE accounts SET cash_balance = cash_balance - ? WHERE id = ?",
                    (total_cost, account_id),
                )

                # 2. Upsert position (weighted-average cost)
                async with db.execute(
                    "SELECT qty, avg_cost FROM positions WHERE account_id = ? AND ticker = ?",
                    (account_id, ticker),
                ) as cur:
                    pos_row = await cur.fetchone()

                if pos_row is None:
                    # New position
                    await db.execute(
                        """
                        INSERT INTO positions (account_id, ticker, qty, avg_cost, opened_at)
                        VALUES (?, ?, ?, ?, ?)
                        """,
                        (account_id, ticker, qty, fill_price, now),
                    )
                else:
                    old_qty = pos_row["qty"]
                    old_avg = pos_row["avg_cost"]
                    new_qty = old_qty + qty
                    new_avg = (old_qty * old_avg + qty * fill_price) / new_qty
                    await db.execute(
                        "UPDATE positions SET qty = ?, avg_cost = ? "
                        "WHERE account_id = ? AND ticker = ?",
                        (new_qty, new_avg, account_id, ticker),
                    )

                # 3. Insert order record
                await db.execute(
                    """
                    INSERT INTO orders (
                        id, account_id, ticker, side, order_type, qty,
                        limit_price, status, fill_price, fill_qty, fee,
                        signal_label_short, signal_score_short,
                        signal_label_long, signal_score_long,
                        triggered_by, created_at, filled_at, cancelled_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        order_id, account_id, ticker, "buy", "market", qty,
                        None, "filled", fill_price, qty, fee,
                        snap.get("label_short"), snap.get("score_short"),
                        snap.get("label_long"), snap.get("score_long"),
                        request.triggered_by, now, now, None,
                    ),
                )

                await db.commit()
            except Exception:
                await db.rollback()
                raise

        return await self._fetch_order(account_id, order_id)

    async def _execute_market_sell(
        self,
        account_id: str,
        request: OrderRequest,
        signal_snapshot: dict | None,
        fill_price: float,
        fee: float,
        total_proceeds: float,
    ) -> Order:
        ticker = request.ticker
        qty = request.qty

        # ── pre-check (outside transaction — read-only) ─────────────────
        async with get_db() as db:
            async with db.execute(
                "SELECT qty FROM positions WHERE account_id = ? AND ticker = ?",
                (account_id, ticker),
            ) as cursor:
                pos_row = await cursor.fetchone()

        if pos_row is None or pos_row["qty"] < qty - 1e-9:
            held = pos_row["qty"] if pos_row else 0.0
            raise InsufficientPositionError(
                f"Need {qty} of {ticker} but only {held} held"
            )

        # ── mutating transaction ─────────────────────────────────────────
        now = _now_iso()
        order_id = uuid.uuid4().hex
        snap = signal_snapshot or {}

        async with get_db() as db:
            await db.execute("BEGIN")
            try:
                # 1. Increment cash
                await db.execute(
                    "UPDATE accounts SET cash_balance = cash_balance + ? WHERE id = ?",
                    (total_proceeds, account_id),
                )

                # 2. Decrement (or delete) position
                new_qty = pos_row["qty"] - qty
                if new_qty < 1e-9:
                    # Full sell — remove the row
                    await db.execute(
                        "DELETE FROM positions WHERE account_id = ? AND ticker = ?",
                        (account_id, ticker),
                    )
                else:
                    await db.execute(
                        "UPDATE positions SET qty = ? WHERE account_id = ? AND ticker = ?",
                        (new_qty, account_id, ticker),
                    )

                # 3. Insert order record
                await db.execute(
                    """
                    INSERT INTO orders (
                        id, account_id, ticker, side, order_type, qty,
                        limit_price, status, fill_price, fill_qty, fee,
                        signal_label_short, signal_score_short,
                        signal_label_long, signal_score_long,
                        triggered_by, created_at, filled_at, cancelled_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        order_id, account_id, ticker, "sell", "market", qty,
                        None, "filled", fill_price, qty, fee,
                        snap.get("label_short"), snap.get("score_short"),
                        snap.get("label_long"), snap.get("score_long"),
                        request.triggered_by, now, now, None,
                    ),
                )

                await db.commit()
            except Exception:
                await db.rollback()
                raise

        return await self._fetch_order(account_id, order_id)

    # ------------------------------------------------------------------ #
    # Internal helpers — limit orders                                      #
    # ------------------------------------------------------------------ #

    async def _place_limit_order(
        self,
        account_id: str,
        request: OrderRequest,
        signal_snapshot: dict | None,
    ) -> Order:
        """Insert a pending limit order.  Cash and positions are NOT mutated.

        Task 5 (limit-order matcher) will fill these when the price crosses
        the limit.
        """
        now = _now_iso()
        order_id = uuid.uuid4().hex
        snap = signal_snapshot or {}

        async with get_db() as db:
            await db.execute("BEGIN")
            try:
                await db.execute(
                    """
                    INSERT INTO orders (
                        id, account_id, ticker, side, order_type, qty,
                        limit_price, status, fill_price, fill_qty, fee,
                        signal_label_short, signal_score_short,
                        signal_label_long, signal_score_long,
                        triggered_by, created_at, filled_at, cancelled_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        order_id, account_id, request.ticker,
                        request.side, "limit", request.qty,
                        request.limit_price, "pending", None, None, 0.0,
                        snap.get("label_short"), snap.get("score_short"),
                        snap.get("label_long"), snap.get("score_long"),
                        request.triggered_by, now, None, None,
                    ),
                )
                await db.commit()
            except Exception:
                await db.rollback()
                raise

        return await self._fetch_order(account_id, order_id)

    # ------------------------------------------------------------------ #
    # cancel_order                                                         #
    # ------------------------------------------------------------------ #

    async def cancel_order(self, account_id: str, order_id: str) -> Order:
        """Cancel a queued or pending order.

        Raises
        ------
        OrderNotFoundError
            If no order with *order_id* exists for *account_id*.
        InvalidOrderError
            If the order is not in a cancellable state (queued / pending).
        """
        async with get_db() as db:
            async with db.execute(
                "SELECT * FROM orders WHERE id = ? AND account_id = ?",
                (order_id, account_id),
            ) as cursor:
                row = await cursor.fetchone()

        if row is None:
            raise OrderNotFoundError(
                f"Order '{order_id}' not found for account '{account_id}'"
            )

        if row["status"] not in ("queued", "pending"):
            raise InvalidOrderError(
                f"Cannot cancel order with status='{row['status']}'; "
                "only 'queued' or 'pending' orders may be cancelled"
            )

        now = _now_iso()
        async with get_db() as db:
            await db.execute("BEGIN")
            try:
                await db.execute(
                    "UPDATE orders SET status = 'cancelled', cancelled_at = ? "
                    "WHERE id = ? AND account_id = ?",
                    (now, order_id, account_id),
                )
                await db.commit()
            except Exception:
                await db.rollback()
                raise

        return await self._fetch_order(account_id, order_id)

    # ------------------------------------------------------------------ #
    # Utility                                                              #
    # ------------------------------------------------------------------ #

    async def _fetch_order(self, account_id: str, order_id: str) -> Order:
        async with get_db() as db:
            async with db.execute(
                "SELECT * FROM orders WHERE id = ? AND account_id = ?",
                (order_id, account_id),
            ) as cursor:
                row = await cursor.fetchone()
        if row is None:
            raise BrokerError(f"Order '{order_id}' not found after insert — DB error?")
        return _row_to_order(row)

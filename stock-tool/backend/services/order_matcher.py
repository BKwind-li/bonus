"""Order matcher — fills queued and pending limit orders.

Called periodically (Task 8 wiring) with a fresh price snapshot.  Processes
every open order and returns the list of orders that newly transitioned to
``filled`` or ``rejected`` during this invocation.

Design decisions
----------------
* **One transaction per order.**  Partial progress on a multi-order batch is
  acceptable for MVP; atomicity across the whole batch is not attempted.
* **Per-ticker serialisation.**  Orders on the same ticker are processed in
  ``created_at ASC`` order so the first fill can consume cash / position
  before later orders are evaluated.
* **``current_prices`` is required for release.**  If the ticker is not in
  ``current_prices`` we skip the order this cycle and retry on the next
  scheduler tick — we never guess or use a stale price.
* **Fill at limit_price for limit orders.**  Spread is the user's
  responsibility when they set the limit; we apply no additional spread or
  fee (``fee=0``).
"""

from __future__ import annotations

from datetime import datetime, timezone

from brokers.paper import _apply_fill_buy, _apply_fill_sell
from database import get_db
from models import Order
from services.market_hours import should_queue_order

# Re-use the same row-to-model converter from paper.py without importing the
# whole class — import the private helper via the module reference so tests
# can still patch it if needed.
from brokers.paper import _row_to_order


async def match_open_orders(
    adapter,
    current_prices: dict[str, float],
    now: datetime,
) -> list[Order]:
    """Process every queued and pending order against *current_prices*.

    Parameters
    ----------
    adapter:
        A ``PaperBrokerAdapter`` instance (or any compatible adapter that
        exposes ``get_db``-backed orders).  Currently only the DB connection
        path is used; ``adapter`` itself is not called.
    current_prices:
        Mapping of ``ticker → most recent price`` gathered by the caller
        before invoking this function.
    now:
        Current time (timezone-aware), injected so callers (and tests) control
        the market-hours evaluation.

    Returns
    -------
    list[Order]
        Orders that **newly** transitioned to ``filled`` or ``rejected`` during
        this call.  Pre-existing filled/cancelled orders are never included.
    """
    # ── 1. Fetch all open orders, serialised per ticker ──────────────────
    async with get_db() as db:
        async with db.execute(
            """
            SELECT * FROM orders
            WHERE status IN ('queued', 'pending')
            ORDER BY ticker, created_at ASC
            """,
        ) as cursor:
            rows = await cursor.fetchall()

    if not rows:
        return []

    newly_changed: list[Order] = []

    for row in rows:
        order_id = row["id"]
        account_id = row["account_id"]
        ticker = row["ticker"]
        side = row["side"]
        qty = row["qty"]
        status = row["status"]
        limit_price = row["limit_price"]

        if status == "queued":
            # Was a closed-market market order.  Release it if market is now open.
            result = await _process_queued(
                order_id, account_id, ticker, side, qty, current_prices, now
            )
        else:
            # status == 'pending' — a limit order.
            result = await _process_pending_limit(
                order_id, account_id, ticker, side, qty, limit_price, current_prices, now
            )

        if result is not None:
            newly_changed.append(result)

    return newly_changed


# ---------------------------------------------------------------------------
# Per-order processing helpers
# ---------------------------------------------------------------------------

async def _process_queued(
    order_id: str,
    account_id: str,
    ticker: str,
    side: str,
    qty: float,
    current_prices: dict[str, float],
    now: datetime,
) -> Order | None:
    """Try to release a queued market order.

    Returns the updated Order if it was filled or rejected; None if it was
    left as queued (market still closed or price unavailable).
    """
    # Still closed? Leave it queued.
    if should_queue_order(ticker, now):
        return None

    # Need a fresh price to fill at.
    if ticker not in current_prices:
        return None

    fill_price = current_prices[ticker]
    now_iso = now.isoformat()
    fee = 0.0  # stock market orders: no fee

    if side == "buy":
        # Pre-check cash
        async with get_db() as db:
            async with db.execute(
                "SELECT cash_balance FROM accounts WHERE id = ?", (account_id,)
            ) as cur:
                acc_row = await cur.fetchone()
        if acc_row is None or acc_row["cash_balance"] < fill_price * qty:
            return await _mark_rejected(order_id, account_id, now_iso)

        async with get_db() as db:
            await db.execute("BEGIN")
            try:
                await _apply_fill_buy(db, account_id, ticker, qty, fill_price, now_iso)
                await db.execute(
                    """
                    UPDATE orders
                    SET status='filled', fill_price=?, fill_qty=?, fee=?, filled_at=?
                    WHERE id=?
                    """,
                    (fill_price, qty, fee, now_iso, order_id),
                )
                await db.commit()
            except Exception:
                await db.rollback()
                raise

    else:  # sell
        # Pre-check position
        async with get_db() as db:
            async with db.execute(
                "SELECT qty FROM positions WHERE account_id=? AND ticker=?",
                (account_id, ticker),
            ) as cur:
                pos_row = await cur.fetchone()
        if pos_row is None or pos_row["qty"] < qty - 1e-9:
            return await _mark_rejected(order_id, account_id, now_iso)

        total_proceeds = fill_price * qty
        async with get_db() as db:
            await db.execute("BEGIN")
            try:
                await _apply_fill_sell(
                    db, account_id, ticker, qty, pos_row["qty"], total_proceeds, now_iso
                )
                await db.execute(
                    """
                    UPDATE orders
                    SET status='filled', fill_price=?, fill_qty=?, fee=?, filled_at=?
                    WHERE id=?
                    """,
                    (fill_price, qty, fee, now_iso, order_id),
                )
                await db.commit()
            except Exception:
                await db.rollback()
                raise

    return await _fetch_order_by_id(order_id)


async def _process_pending_limit(
    order_id: str,
    account_id: str,
    ticker: str,
    side: str,
    qty: float,
    limit_price: float,
    current_prices: dict[str, float],
    now: datetime,
) -> Order | None:
    """Try to trigger a pending limit order.

    Returns the updated Order if it was filled or rejected; None if the
    trigger condition is not met or the price is unavailable.
    """
    if ticker not in current_prices:
        return None

    current_price = current_prices[ticker]

    # Trigger conditions:
    # BUY  → current_price <= limit_price  (market fell to / below the limit)
    # SELL → current_price >= limit_price  (market rose to / above the limit)
    if side == "buy" and current_price > limit_price:
        return None
    if side == "sell" and current_price < limit_price:
        return None

    # Triggered — fill at limit_price, fee=0
    fill_price = limit_price
    fee = 0.0
    now_iso = now.isoformat()

    if side == "buy":
        total_cost = fill_price * qty
        # Pre-check cash
        async with get_db() as db:
            async with db.execute(
                "SELECT cash_balance FROM accounts WHERE id = ?", (account_id,)
            ) as cur:
                acc_row = await cur.fetchone()
        if acc_row is None or acc_row["cash_balance"] < total_cost:
            return await _mark_rejected(order_id, account_id, now_iso)

        async with get_db() as db:
            await db.execute("BEGIN")
            try:
                await _apply_fill_buy(db, account_id, ticker, qty, fill_price, now_iso)
                await db.execute(
                    """
                    UPDATE orders
                    SET status='filled', fill_price=?, fill_qty=?, fee=?, filled_at=?
                    WHERE id=?
                    """,
                    (fill_price, qty, fee, now_iso, order_id),
                )
                await db.commit()
            except Exception:
                await db.rollback()
                raise

    else:  # sell
        # Pre-check position
        async with get_db() as db:
            async with db.execute(
                "SELECT qty FROM positions WHERE account_id=? AND ticker=?",
                (account_id, ticker),
            ) as cur:
                pos_row = await cur.fetchone()
        if pos_row is None or pos_row["qty"] < qty - 1e-9:
            return await _mark_rejected(order_id, account_id, now_iso)

        total_proceeds = fill_price * qty
        async with get_db() as db:
            await db.execute("BEGIN")
            try:
                await _apply_fill_sell(
                    db, account_id, ticker, qty, pos_row["qty"], total_proceeds, now_iso
                )
                await db.execute(
                    """
                    UPDATE orders
                    SET status='filled', fill_price=?, fill_qty=?, fee=?, filled_at=?
                    WHERE id=?
                    """,
                    (fill_price, qty, fee, now_iso, order_id),
                )
                await db.commit()
            except Exception:
                await db.rollback()
                raise

    return await _fetch_order_by_id(order_id)


# ---------------------------------------------------------------------------
# Shared utilities
# ---------------------------------------------------------------------------

async def _mark_rejected(order_id: str, account_id: str, now_iso: str) -> Order:  # noqa: ARG001
    """Set an order to ``rejected`` with ``cancelled_at=now_iso``."""
    async with get_db() as db:
        await db.execute("BEGIN")
        try:
            await db.execute(
                "UPDATE orders SET status='rejected', cancelled_at=? WHERE id=?",
                (now_iso, order_id),
            )
            await db.commit()
        except Exception:
            await db.rollback()
            raise
    return await _fetch_order_by_id(order_id)


async def _fetch_order_by_id(order_id: str) -> Order:
    async with get_db() as db:
        async with db.execute(
            "SELECT * FROM orders WHERE id = ?", (order_id,)
        ) as cursor:
            row = await cursor.fetchone()
    if row is None:
        raise RuntimeError(f"Order '{order_id}' disappeared from DB unexpectedly")
    return _row_to_order(row)

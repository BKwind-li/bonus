"""Schema-level tests for the paper-trading accounts table (Task 1)
and PaperBrokerAdapter behaviour tests (Task 3).
"""
import pytest
from database import init_db, get_db
from config import settings


# ---------------------------------------------------------------------------
# Helpers shared by both Task-1 schema tests and Task-3 adapter tests
# ---------------------------------------------------------------------------

async def _fetch_default_account(db):
    async with db.execute(
        "SELECT * FROM accounts WHERE id = 'default'"
    ) as cursor:
        return await cursor.fetchone()


async def _count_accounts(db):
    async with db.execute("SELECT COUNT(*) FROM accounts") as cursor:
        row = await cursor.fetchone()
        return row[0]


# ---------------------------------------------------------------------------
# Task 1 — schema / seed tests (unchanged)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_default_account_seeded_after_init_db():
    """After init_db(), accounts table has exactly one row with id='default'."""
    async with get_db() as db:
        count = await _count_accounts(db)
        assert count == 1

        row = await _fetch_default_account(db)
        assert row is not None
        assert row["id"] == "default"
        assert row["type"] == "paper"
        assert row["broker_adapter"] == "paper"
        assert row["display_name"] == "默认虚拟账户"
        assert row["initial_cash"] == settings.paper_initial_cash
        assert row["cash_balance"] == settings.paper_initial_cash
        assert row["created_at"] is not None


@pytest.mark.asyncio
async def test_default_account_cash_balance_equals_initial_cash():
    """cash_balance equals paper_initial_cash after init."""
    async with get_db() as db:
        row = await _fetch_default_account(db)
        assert row is not None
        assert row["cash_balance"] == settings.paper_initial_cash
        assert row["cash_balance"] == row["initial_cash"]


@pytest.mark.asyncio
async def test_init_db_twice_does_not_reset_cash_balance():
    """INSERT OR IGNORE: calling init_db() again must not overwrite a mutated cash_balance."""
    mutated_balance = settings.paper_initial_cash - 5000.0

    # Mutate cash_balance to a different value
    async with get_db() as db:
        await db.execute(
            "UPDATE accounts SET cash_balance = ? WHERE id = 'default'",
            (mutated_balance,),
        )
        await db.commit()

    # Call init_db() a second time
    await init_db()

    # The mutated value must be preserved
    async with get_db() as db:
        row = await _fetch_default_account(db)
        assert row is not None
        assert row["cash_balance"] == mutated_balance


# ---------------------------------------------------------------------------
# Task 3 — PaperBrokerAdapter tests
# ---------------------------------------------------------------------------

from brokers.paper import PaperBrokerAdapter
from brokers.base import (
    InsufficientFundsError,
    InsufficientPositionError,
    InvalidOrderError,
    OrderNotFoundError,
    BrokerError,
)
from models import OrderRequest


# ── 1. buy_market_with_sufficient_cash ───────────────────────────────────────

@pytest.mark.asyncio
async def test_buy_market_with_sufficient_cash():
    """After a market buy, cash decremented exactly, positions row created, order=filled."""
    adapter = PaperBrokerAdapter(price_fetcher=lambda t: 150.0)
    order = await adapter.place_order(
        "default",
        OrderRequest(ticker="AAPL", side="buy", order_type="market", qty=10),
        signal_snapshot=None,
    )

    assert order.status == "filled"
    assert order.fill_price == 150.0
    assert order.fill_qty == 10
    assert order.fee == 0.0
    assert order.ticker == "AAPL"
    assert order.side == "buy"

    account = await adapter.get_account("default")
    assert abs(account.cash_balance - (settings.paper_initial_cash - 150.0 * 10)) < 1e-6

    positions = await adapter.get_positions("default")
    assert len(positions) == 1
    pos = positions[0]
    assert pos.ticker == "AAPL"
    assert abs(pos.qty - 10) < 1e-9
    assert abs(pos.avg_cost - 150.0) < 1e-9


# ── 2. buy_market_insufficient_cash ──────────────────────────────────────────

@pytest.mark.asyncio
async def test_buy_market_insufficient_cash():
    """Buying more than cash allows raises InsufficientFundsError; DB unchanged."""
    adapter = PaperBrokerAdapter(price_fetcher=lambda t: 200.0)

    # 200.0 * 600 = 120_000 > 100_000
    with pytest.raises(InsufficientFundsError):
        await adapter.place_order(
            "default",
            OrderRequest(ticker="AAPL", side="buy", order_type="market", qty=600),
            signal_snapshot=None,
        )

    account = await adapter.get_account("default")
    assert account.cash_balance == settings.paper_initial_cash

    positions = await adapter.get_positions("default")
    assert len(positions) == 0


# ── 3. sell_market_with_sufficient_position ───────────────────────────────────

@pytest.mark.asyncio
async def test_sell_market_with_sufficient_position():
    """After sell, cash increases, position qty decreases, order=filled."""
    adapter = PaperBrokerAdapter(price_fetcher=lambda t: 100.0)

    # First buy 20 shares
    await adapter.place_order(
        "default",
        OrderRequest(ticker="AAPL", side="buy", order_type="market", qty=20),
        signal_snapshot=None,
    )

    cash_after_buy = (await adapter.get_account("default")).cash_balance

    # Now sell 5 shares
    sell_order = await adapter.place_order(
        "default",
        OrderRequest(ticker="AAPL", side="sell", order_type="market", qty=5),
        signal_snapshot=None,
    )

    assert sell_order.status == "filled"
    assert sell_order.side == "sell"
    assert sell_order.fill_price == 100.0
    assert sell_order.fill_qty == 5

    account = await adapter.get_account("default")
    assert abs(account.cash_balance - (cash_after_buy + 100.0 * 5)) < 1e-6

    positions = await adapter.get_positions("default")
    assert len(positions) == 1
    assert abs(positions[0].qty - 15) < 1e-9


# ── 4. sell_market_insufficient_position ─────────────────────────────────────

@pytest.mark.asyncio
async def test_sell_market_insufficient_position():
    """Selling more than held raises InsufficientPositionError; DB unchanged."""
    adapter = PaperBrokerAdapter(price_fetcher=lambda t: 100.0)

    # Buy 10 shares first
    await adapter.place_order(
        "default",
        OrderRequest(ticker="AAPL", side="buy", order_type="market", qty=10),
        signal_snapshot=None,
    )

    cash_after_buy = (await adapter.get_account("default")).cash_balance

    with pytest.raises(InsufficientPositionError):
        await adapter.place_order(
            "default",
            OrderRequest(ticker="AAPL", side="sell", order_type="market", qty=20),
            signal_snapshot=None,
        )

    # Positions unchanged
    account = await adapter.get_account("default")
    assert abs(account.cash_balance - cash_after_buy) < 1e-6
    positions = await adapter.get_positions("default")
    assert abs(positions[0].qty - 10) < 1e-9


# ── 5. buy_twice_avg_cost_weighted ────────────────────────────────────────────

@pytest.mark.asyncio
async def test_buy_twice_avg_cost_weighted():
    """Two buys at different prices; avg_cost = (q1*p1 + q2*p2) / (q1+q2)."""
    prices = iter([100.0, 200.0])
    adapter = PaperBrokerAdapter(price_fetcher=lambda t: next(prices))

    await adapter.place_order(
        "default",
        OrderRequest(ticker="AAPL", side="buy", order_type="market", qty=10),
        signal_snapshot=None,
    )
    await adapter.place_order(
        "default",
        OrderRequest(ticker="AAPL", side="buy", order_type="market", qty=10),
        signal_snapshot=None,
    )

    positions = await adapter.get_positions("default")
    assert len(positions) == 1
    pos = positions[0]
    assert abs(pos.qty - 20) < 1e-9
    expected_avg = (10 * 100.0 + 10 * 200.0) / 20
    assert abs(pos.avg_cost - expected_avg) < 1e-9


# ── 6. sell_all_position_deletes_row ─────────────────────────────────────────

@pytest.mark.asyncio
async def test_sell_all_position_deletes_row():
    """After selling the entire position, the positions row is removed."""
    adapter = PaperBrokerAdapter(price_fetcher=lambda t: 50.0)

    await adapter.place_order(
        "default",
        OrderRequest(ticker="AAPL", side="buy", order_type="market", qty=10),
        signal_snapshot=None,
    )

    await adapter.place_order(
        "default",
        OrderRequest(ticker="AAPL", side="sell", order_type="market", qty=10),
        signal_snapshot=None,
    )

    positions = await adapter.get_positions("default")
    tickers = [p.ticker for p in positions]
    assert "AAPL" not in tickers


# ── 7. forex_buy_applies_spread ───────────────────────────────────────────────

@pytest.mark.asyncio
async def test_forex_buy_applies_spread():
    """For a forex pair, fill_price > current_price (spread applied); fee > 0."""
    from data.universe import is_forex
    fx_ticker = "EURUSD=X"
    assert is_forex(fx_ticker)

    mid_price = 1.1000
    adapter = PaperBrokerAdapter(price_fetcher=lambda t: mid_price)

    order = await adapter.place_order(
        "default",
        OrderRequest(ticker=fx_ticker, side="buy", order_type="market", qty=1000),
        signal_snapshot=None,
    )

    assert order.fill_price > mid_price, "BUY fill_price should be above mid for FX"
    assert order.fee > 0, "FX fee should be positive"

    # fee == |fill_price - mid_price| * qty
    expected_spread_pct = settings.paper_fx_spread_pips / 10000.0
    expected_fill = mid_price * (1 + expected_spread_pct)
    assert abs(order.fill_price - expected_fill) < 1e-9
    expected_fee = abs(expected_fill - mid_price) * 1000
    assert abs(order.fee - expected_fee) < 1e-9


# ── 8. stock_buy_no_spread ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_stock_buy_no_spread():
    """For a stock, fill_price == current_price (no spread); fee == 0."""
    adapter = PaperBrokerAdapter(price_fetcher=lambda t: 150.0)

    order = await adapter.place_order(
        "default",
        OrderRequest(ticker="AAPL", side="buy", order_type="market", qty=5),
        signal_snapshot=None,
    )

    assert order.fill_price == 150.0
    assert order.fee == 0.0


# ── 9. invariant_cash_plus_positions_equals_initial ──────────────────────────

@pytest.mark.asyncio
async def test_invariant_cash_plus_positions_equals_initial():
    """cash + Σ(qty * avg_cost) == initial_cash - total_fx_fees (within 1e-6).

    For stocks: fee=0, so cash + Σ(qty * avg_cost) == initial_cash.
    This test uses only stocks to keep the invariant clean.
    """
    price_map = {"AAPL": 150.0, "MSFT": 400.0}
    adapter = PaperBrokerAdapter(price_fetcher=lambda t: price_map[t])

    await adapter.place_order(
        "default",
        OrderRequest(ticker="AAPL", side="buy", order_type="market", qty=10),
        signal_snapshot=None,
    )
    await adapter.place_order(
        "default",
        OrderRequest(ticker="MSFT", side="buy", order_type="market", qty=5),
        signal_snapshot=None,
    )
    # Sell some AAPL back
    await adapter.place_order(
        "default",
        OrderRequest(ticker="AAPL", side="sell", order_type="market", qty=3),
        signal_snapshot=None,
    )

    account = await adapter.get_account("default")
    positions = await adapter.get_positions("default")

    position_value = sum(p.qty * p.avg_cost for p in positions)
    total = account.cash_balance + position_value

    assert abs(total - settings.paper_initial_cash) < 1e-6, (
        f"Invariant broken: cash={account.cash_balance}, position_value={position_value}, "
        f"total={total}, expected={settings.paper_initial_cash}"
    )


# ── 10. place_limit_order_does_not_mutate_cash_or_positions ──────────────────

@pytest.mark.asyncio
async def test_place_limit_order_does_not_mutate_cash_or_positions():
    """Limit order creates a pending row but does NOT change cash or positions."""
    # price_fetcher should NOT be called for limit orders
    adapter = PaperBrokerAdapter(price_fetcher=lambda t: (_ for _ in ()).throw(
        AssertionError("price_fetcher must not be called for limit orders")
    ))

    order = await adapter.place_order(
        "default",
        OrderRequest(
            ticker="AAPL", side="buy", order_type="limit", qty=5, limit_price=140.0
        ),
        signal_snapshot=None,
    )

    assert order.status == "pending"
    assert order.fill_price is None
    assert order.fill_qty is None
    assert order.limit_price == 140.0

    account = await adapter.get_account("default")
    assert account.cash_balance == settings.paper_initial_cash

    positions = await adapter.get_positions("default")
    assert len(positions) == 0

    orders = await adapter.get_orders("default")
    assert len(orders) == 1
    assert orders[0].status == "pending"


# ── 11. cancel_pending_limit ──────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_cancel_pending_limit():
    """Cancelling a pending limit order sets status=cancelled and sets cancelled_at."""
    adapter = PaperBrokerAdapter(price_fetcher=lambda t: 100.0)

    order = await adapter.place_order(
        "default",
        OrderRequest(
            ticker="AAPL", side="buy", order_type="limit", qty=5, limit_price=95.0
        ),
        signal_snapshot=None,
    )
    assert order.status == "pending"

    cancelled = await adapter.cancel_order("default", order.id)

    assert cancelled.status == "cancelled"
    assert cancelled.cancelled_at is not None
    assert cancelled.id == order.id


# ── 12. cancel_filled_order_raises ───────────────────────────────────────────

@pytest.mark.asyncio
async def test_cancel_filled_order_raises():
    """Trying to cancel a filled order raises InvalidOrderError."""
    adapter = PaperBrokerAdapter(price_fetcher=lambda t: 100.0)

    order = await adapter.place_order(
        "default",
        OrderRequest(ticker="AAPL", side="buy", order_type="market", qty=5),
        signal_snapshot=None,
    )
    assert order.status == "filled"

    with pytest.raises(InvalidOrderError):
        await adapter.cancel_order("default", order.id)


# ── 13. cancel_unknown_order_raises ──────────────────────────────────────────

@pytest.mark.asyncio
async def test_cancel_unknown_order_raises():
    """cancel_order with unknown order_id raises OrderNotFoundError."""
    adapter = PaperBrokerAdapter(price_fetcher=lambda t: 100.0)

    with pytest.raises(OrderNotFoundError):
        await adapter.cancel_order("default", "nonexistent-order-id-xyz")


# ── 14. invalid_order_request ─────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_invalid_order_qty_zero_raises():
    """qty <= 0 is rejected by pydantic Field(gt=0) before adapter sees it."""
    with pytest.raises(Exception):
        # Pydantic Field(gt=0) will reject this
        OrderRequest(ticker="AAPL", side="buy", order_type="market", qty=0)


@pytest.mark.asyncio
async def test_invalid_limit_order_missing_limit_price():
    """limit order without limit_price raises InvalidOrderError from adapter."""
    adapter = PaperBrokerAdapter(price_fetcher=lambda t: 100.0)

    with pytest.raises(InvalidOrderError):
        await adapter.place_order(
            "default",
            OrderRequest(
                ticker="AAPL", side="buy", order_type="limit", qty=5, limit_price=None
            ),
            signal_snapshot=None,
        )


@pytest.mark.asyncio
async def test_invalid_order_type_raises():
    """Unknown order_type raises InvalidOrderError."""
    adapter = PaperBrokerAdapter(price_fetcher=lambda t: 100.0)

    with pytest.raises(InvalidOrderError):
        await adapter.place_order(
            "default",
            OrderRequest(
                ticker="AAPL", side="buy", order_type="stop", qty=5  # type: ignore[arg-type]
            ),
            signal_snapshot=None,
        )


# ── 15. signal_snapshot_persisted ────────────────────────────────────────────

@pytest.mark.asyncio
async def test_signal_snapshot_persisted():
    """signal_snapshot fields are written to the order record."""
    adapter = PaperBrokerAdapter(price_fetcher=lambda t: 100.0)

    snapshot = {
        "label_short": "强看涨",
        "score_short": 4,
        "label_long": "中性",
        "score_long": 0,
    }

    order = await adapter.place_order(
        "default",
        OrderRequest(ticker="AAPL", side="buy", order_type="market", qty=1),
        signal_snapshot=snapshot,
    )

    assert order.signal_label_short == "强看涨"
    assert order.signal_score_short == 4
    assert order.signal_label_long == "中性"
    assert order.signal_score_long == 0

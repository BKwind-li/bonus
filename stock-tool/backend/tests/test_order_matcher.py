"""Tests for services/order_matcher.py — limit-order and queued-order matching.

All tests use mock prices; no real network calls are made.
"""
from __future__ import annotations

import pytest
from datetime import datetime
from zoneinfo import ZoneInfo

from brokers.paper import PaperBrokerAdapter
from config import settings
from database import get_db
from models import OrderRequest
from services.order_matcher import match_open_orders

_ET = ZoneInfo("America/New_York")

# Canonical "market open" time: Wednesday 2026-06-03 14:00 ET
_OPEN_NOW = datetime(2026, 6, 3, 14, 0, tzinfo=_ET)
# Canonical "market closed" time: Wednesday 2026-06-03 03:00 ET (pre-market)
_CLOSED_NOW = datetime(2026, 6, 3, 3, 0, tzinfo=_ET)
# Weekend: Saturday 2026-06-06 12:00 ET
_WEEKEND_NOW = datetime(2026, 6, 6, 12, 0, tzinfo=_ET)


def _open_adapter(price=None):
    """Return an adapter whose now_provider returns market-open time."""
    fetcher = (lambda t: price) if price is not None else (lambda t: None)
    return PaperBrokerAdapter(price_fetcher=fetcher, now_provider=lambda: _OPEN_NOW)


def _closed_adapter(price=None):
    """Return an adapter whose now_provider returns market-closed time."""
    fetcher = (lambda t: price) if price is not None else (lambda t: None)
    return PaperBrokerAdapter(price_fetcher=fetcher, now_provider=lambda: _CLOSED_NOW)


# ---------------------------------------------------------------------------
# 1. limit_buy_triggers_when_price_at_or_below
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_limit_buy_triggers_when_price_at_or_below():
    """Pending BUY limit @100; current price 99 → fills at 100, cash decreases by 100*qty."""
    adapter = _open_adapter()
    order = await adapter.place_order(
        "default",
        OrderRequest(ticker="AAPL", side="buy", order_type="limit", qty=5, limit_price=100.0),
    )
    assert order.status == "pending"

    initial_cash = (await adapter.get_account("default")).cash_balance

    results = await match_open_orders(adapter, {"AAPL": 99.0}, _OPEN_NOW)

    assert len(results) == 1
    filled = results[0]
    assert filled.id == order.id
    assert filled.status == "filled"
    assert abs(filled.fill_price - 100.0) < 1e-9  # fills at limit, not current
    assert abs(filled.fill_qty - 5) < 1e-9

    account = await adapter.get_account("default")
    assert abs(account.cash_balance - (initial_cash - 100.0 * 5)) < 1e-6

    positions = await adapter.get_positions("default")
    aapl = next((p for p in positions if p.ticker == "AAPL"), None)
    assert aapl is not None
    assert abs(aapl.qty - 5) < 1e-9


# ---------------------------------------------------------------------------
# 2. limit_buy_no_trigger_when_price_above
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_limit_buy_no_trigger_when_price_above():
    """Pending BUY limit @100; current price 101 → still pending."""
    adapter = _open_adapter()
    order = await adapter.place_order(
        "default",
        OrderRequest(ticker="AAPL", side="buy", order_type="limit", qty=5, limit_price=100.0),
    )
    assert order.status == "pending"

    results = await match_open_orders(adapter, {"AAPL": 101.0}, _OPEN_NOW)

    assert results == []

    orders = await adapter.get_orders("default")
    assert orders[0].status == "pending"


# ---------------------------------------------------------------------------
# 3. limit_sell_triggers_when_price_at_or_above
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_limit_sell_triggers_when_price_at_or_above():
    """Pending SELL limit @100; current price 100 → fills at 100, cash increases by 100*qty."""
    # First buy 10 shares to have a position
    buy_adapter = _open_adapter(price=90.0)
    await buy_adapter.place_order(
        "default",
        OrderRequest(ticker="AAPL", side="buy", order_type="market", qty=10),
    )

    cash_after_buy = (await buy_adapter.get_account("default")).cash_balance

    # Place a pending limit sell
    adapter = _open_adapter()
    order = await adapter.place_order(
        "default",
        OrderRequest(ticker="AAPL", side="sell", order_type="limit", qty=10, limit_price=100.0),
    )
    assert order.status == "pending"

    results = await match_open_orders(adapter, {"AAPL": 100.0}, _OPEN_NOW)

    assert len(results) == 1
    filled = results[0]
    assert filled.id == order.id
    assert filled.status == "filled"
    assert abs(filled.fill_price - 100.0) < 1e-9

    account = await adapter.get_account("default")
    assert abs(account.cash_balance - (cash_after_buy + 100.0 * 10)) < 1e-6

    positions = await adapter.get_positions("default")
    aapl = next((p for p in positions if p.ticker == "AAPL"), None)
    assert aapl is None  # position fully closed


# ---------------------------------------------------------------------------
# 4. limit_sell_no_trigger_when_price_below
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_limit_sell_no_trigger_when_price_below():
    """Pending SELL limit @100; current price 99 → still pending."""
    buy_adapter = _open_adapter(price=90.0)
    await buy_adapter.place_order(
        "default",
        OrderRequest(ticker="AAPL", side="buy", order_type="market", qty=10),
    )

    adapter = _open_adapter()
    order = await adapter.place_order(
        "default",
        OrderRequest(ticker="AAPL", side="sell", order_type="limit", qty=10, limit_price=100.0),
    )
    assert order.status == "pending"

    results = await match_open_orders(adapter, {"AAPL": 99.0}, _OPEN_NOW)

    assert results == []

    orders = await adapter.get_orders("default", status="pending")
    assert any(o.id == order.id for o in orders)


# ---------------------------------------------------------------------------
# 5. queued_market_buy_releases_when_market_opens
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_queued_market_buy_releases_when_market_opens():
    """Place stock buy when market closed (queued) → matcher with open time fills it."""
    # Place order during closed market
    adapter = _closed_adapter()
    order = await adapter.place_order(
        "default",
        OrderRequest(ticker="AAPL", side="buy", order_type="market", qty=10),
    )
    assert order.status == "queued"

    initial_cash = (await adapter.get_account("default")).cash_balance
    assert abs(initial_cash - settings.paper_initial_cash) < 1e-6

    # Now market is open — call matcher with a fresh price
    results = await match_open_orders(adapter, {"AAPL": 150.0}, _OPEN_NOW)

    assert len(results) == 1
    filled = results[0]
    assert filled.id == order.id
    assert filled.status == "filled"
    assert abs(filled.fill_price - 150.0) < 1e-9
    assert abs(filled.fill_qty - 10) < 1e-9

    account = await adapter.get_account("default")
    assert abs(account.cash_balance - (initial_cash - 150.0 * 10)) < 1e-6

    positions = await adapter.get_positions("default")
    aapl = next((p for p in positions if p.ticker == "AAPL"), None)
    assert aapl is not None
    assert abs(aapl.qty - 10) < 1e-9


# ---------------------------------------------------------------------------
# 6. queued_market_buy_stays_when_market_still_closed
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_queued_market_buy_stays_when_market_still_closed():
    """Queued order remains queued when matcher is called with a still-closed time."""
    adapter = _closed_adapter()
    order = await adapter.place_order(
        "default",
        OrderRequest(ticker="AAPL", side="buy", order_type="market", qty=10),
    )
    assert order.status == "queued"

    # Call matcher at weekend (still closed)
    results = await match_open_orders(adapter, {"AAPL": 150.0}, _WEEKEND_NOW)

    assert results == []

    orders = await adapter.get_orders("default", status="queued")
    assert any(o.id == order.id for o in orders)

    # Cash and positions unchanged
    account = await adapter.get_account("default")
    assert abs(account.cash_balance - settings.paper_initial_cash) < 1e-6
    assert await adapter.get_positions("default") == []


# ---------------------------------------------------------------------------
# 7. queued_market_buy_skips_when_no_price
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_queued_market_buy_skips_when_no_price():
    """Market is open but AAPL not in current_prices → order stays queued (retry next cycle)."""
    adapter = _closed_adapter()
    order = await adapter.place_order(
        "default",
        OrderRequest(ticker="AAPL", side="buy", order_type="market", qty=10),
    )
    assert order.status == "queued"

    # current_prices does not include AAPL
    results = await match_open_orders(adapter, {"MSFT": 400.0}, _OPEN_NOW)

    assert results == []

    orders = await adapter.get_orders("default", status="queued")
    assert any(o.id == order.id for o in orders)


# ---------------------------------------------------------------------------
# 8. limit_buy_fails_with_rejected_when_insufficient_funds
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_limit_buy_fails_with_rejected_when_insufficient_funds():
    """Pre-set cash to a tiny amount; pending limit triggers → status=rejected, cash unchanged."""
    adapter = _open_adapter()

    # Drain most of the cash so the account can't afford 5 * 100 = 500
    async with get_db() as db:
        await db.execute(
            "UPDATE accounts SET cash_balance = 50.0 WHERE id = 'default'"
        )
        await db.commit()

    order = await adapter.place_order(
        "default",
        OrderRequest(ticker="AAPL", side="buy", order_type="limit", qty=5, limit_price=100.0),
    )
    assert order.status == "pending"

    results = await match_open_orders(adapter, {"AAPL": 99.0}, _OPEN_NOW)

    assert len(results) == 1
    rejected = results[0]
    assert rejected.id == order.id
    assert rejected.status == "rejected"
    assert rejected.cancelled_at is not None

    # Cash must still be 50 — no mutation happened
    account = await adapter.get_account("default")
    assert abs(account.cash_balance - 50.0) < 1e-6


# ---------------------------------------------------------------------------
# 9. limit_sell_fails_with_rejected_when_position_missing
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_limit_sell_fails_with_rejected_when_position_missing():
    """Pending limit sell, position manually deleted → matcher marks order rejected."""
    # Buy 10 shares first
    buy_adapter = _open_adapter(price=90.0)
    await buy_adapter.place_order(
        "default",
        OrderRequest(ticker="AAPL", side="buy", order_type="market", qty=10),
    )

    # Place a pending limit sell
    adapter = _open_adapter()
    order = await adapter.place_order(
        "default",
        OrderRequest(ticker="AAPL", side="sell", order_type="limit", qty=10, limit_price=100.0),
    )
    assert order.status == "pending"

    # Manually delete the position (simulates an external scenario)
    async with get_db() as db:
        await db.execute(
            "DELETE FROM positions WHERE account_id='default' AND ticker='AAPL'"
        )
        await db.commit()

    results = await match_open_orders(adapter, {"AAPL": 100.0}, _OPEN_NOW)

    assert len(results) == 1
    rejected = results[0]
    assert rejected.id == order.id
    assert rejected.status == "rejected"
    assert rejected.cancelled_at is not None


# ---------------------------------------------------------------------------
# 10. multiple_pending_on_same_ticker_serialised
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_multiple_pending_on_same_ticker_serialised():
    """Two BUY limits on AAPL: limit @100 and @99, both triggered by current=98.
    Both should fill; position avg_cost reflects both fills (100 and 99).
    """
    adapter = _open_adapter()

    # Place two limit buy orders
    order1 = await adapter.place_order(
        "default",
        OrderRequest(ticker="AAPL", side="buy", order_type="limit", qty=5, limit_price=100.0),
    )
    order2 = await adapter.place_order(
        "default",
        OrderRequest(ticker="AAPL", side="buy", order_type="limit", qty=5, limit_price=99.0),
    )
    assert order1.status == "pending"
    assert order2.status == "pending"

    initial_cash = (await adapter.get_account("default")).cash_balance

    # Current price 98 triggers both (98 <= 100 and 98 <= 99)
    results = await match_open_orders(adapter, {"AAPL": 98.0}, _OPEN_NOW)

    assert len(results) == 2
    ids_changed = {r.id for r in results}
    assert order1.id in ids_changed
    assert order2.id in ids_changed
    assert all(r.status == "filled" for r in results)

    # Cash decremented by 100*5 + 99*5 = 995
    account = await adapter.get_account("default")
    expected_cash = initial_cash - 100.0 * 5 - 99.0 * 5
    assert abs(account.cash_balance - expected_cash) < 1e-6

    # Position: 10 total; avg_cost = (5*100 + 5*99) / 10 = 99.5
    positions = await adapter.get_positions("default")
    aapl = next((p for p in positions if p.ticker == "AAPL"), None)
    assert aapl is not None
    assert abs(aapl.qty - 10) < 1e-9
    expected_avg = (5 * 100.0 + 5 * 99.0) / 10
    assert abs(aapl.avg_cost - expected_avg) < 1e-9


# ---------------------------------------------------------------------------
# 11. invariant_cash_plus_positions_after_matcher
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_invariant_cash_plus_positions_after_matcher():
    """After several matcher cycles, cash + Σ(qty*avg_cost) == initial_cash (stocks only)."""
    adapter = _open_adapter()

    # Place three limit buy orders at different prices
    await adapter.place_order(
        "default",
        OrderRequest(ticker="AAPL", side="buy", order_type="limit", qty=3, limit_price=100.0),
    )
    await adapter.place_order(
        "default",
        OrderRequest(ticker="MSFT", side="buy", order_type="limit", qty=2, limit_price=300.0),
    )
    await adapter.place_order(
        "default",
        OrderRequest(ticker="AAPL", side="buy", order_type="limit", qty=2, limit_price=95.0),
    )

    # Cycle 1: trigger AAPL @100 and MSFT @300 (current AAPL=99, MSFT=295)
    await match_open_orders(adapter, {"AAPL": 99.0, "MSFT": 295.0}, _OPEN_NOW)

    # Cycle 2: trigger AAPL @95 (current AAPL=94)
    await match_open_orders(adapter, {"AAPL": 94.0}, _OPEN_NOW)

    account = await adapter.get_account("default")
    positions = await adapter.get_positions("default")

    position_value = sum(p.qty * p.avg_cost for p in positions)
    total = account.cash_balance + position_value

    assert abs(total - settings.paper_initial_cash) < 1e-6, (
        f"Invariant broken: cash={account.cash_balance}, "
        f"positions_value={position_value}, total={total}"
    )


# ---------------------------------------------------------------------------
# 12. matcher_returns_only_newly_changed
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_matcher_returns_only_newly_changed():
    """Pre-existing filled orders are NOT in the returned list; only newly changed ones."""
    adapter = _open_adapter(price=100.0)

    # Fill one order immediately (market buy during open)
    await adapter.place_order(
        "default",
        OrderRequest(ticker="AAPL", side="buy", order_type="market", qty=5),
    )

    # Place a pending limit that will be triggered
    limit_order = await adapter.place_order(
        "default",
        OrderRequest(ticker="MSFT", side="buy", order_type="limit", qty=3, limit_price=200.0),
    )
    assert limit_order.status == "pending"

    # Call matcher; only the MSFT limit should appear in results (not the already-filled AAPL)
    results = await match_open_orders(
        adapter,
        {"AAPL": 100.0, "MSFT": 199.0},  # MSFT 199 <= 200 triggers it
        _OPEN_NOW,
    )

    assert len(results) == 1
    assert results[0].id == limit_order.id
    assert results[0].status == "filled"

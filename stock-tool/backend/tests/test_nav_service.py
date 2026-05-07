"""Tests for services/nav_service.py (Task 6)."""

import pytest
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from database import get_db
from models import NavPoint
from brokers.paper import PaperBrokerAdapter
from models import OrderRequest

# A market-open datetime: Wednesday 2026-06-03 14:00 ET
_ET = ZoneInfo("America/New_York")
_MARKET_OPEN_NOW = datetime(2026, 6, 3, 14, 0, tzinfo=_ET)

# A fixed "now" for NAV snapshots (UTC)
_SNAP_NOW = datetime(2026, 6, 3, 21, 30, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _nav_rows_for_account(account_id: str) -> list:
    async with get_db() as db:
        async with db.execute(
            "SELECT * FROM nav_history WHERE account_id = ?", (account_id,)
        ) as cursor:
            return await cursor.fetchall()


# ---------------------------------------------------------------------------
# Test 1: snapshot_nav with positions
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_snapshot_nav_with_positions():
    """Buy 10 AAPL@150, snapshot at price 160 → market_value=1600, cash=98500, total=100100."""
    from services.nav_service import snapshot_nav

    adapter = PaperBrokerAdapter(
        price_fetcher=lambda t: 150.0,
        now_provider=lambda: _MARKET_OPEN_NOW,
    )
    await adapter.place_order(
        "default",
        OrderRequest(ticker="AAPL", side="buy", order_type="market", qty=10),
        signal_snapshot=None,
    )

    nav = await snapshot_nav("default", {"AAPL": 160.0}, _SNAP_NOW)

    assert abs(nav.market_value - 1600.0) < 1e-6
    assert abs(nav.cash - 98500.0) < 1e-6
    assert abs(nav.total_value - 100100.0) < 1e-6

    rows = await _nav_rows_for_account("default")
    assert len(rows) == 1
    row = rows[0]
    assert row["account_id"] == "default"
    assert abs(row["market_value"] - 1600.0) < 1e-6
    assert abs(row["cash"] - 98500.0) < 1e-6
    assert abs(row["total_value"] - 100100.0) < 1e-6


# ---------------------------------------------------------------------------
# Test 2: idempotent on same day (INSERT OR REPLACE)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_snapshot_nav_idempotent_same_day():
    """Calling snapshot_nav twice on same date keeps only one row (last write wins)."""
    from services.nav_service import snapshot_nav

    # First call: price 100
    first_snap = datetime(2026, 6, 3, 20, 0, tzinfo=timezone.utc)
    await snapshot_nav("default", {}, first_snap)

    # Second call: same date, different hypothetical values (insert a position first)
    adapter = PaperBrokerAdapter(
        price_fetcher=lambda t: 200.0,
        now_provider=lambda: _MARKET_OPEN_NOW,
    )
    await adapter.place_order(
        "default",
        OrderRequest(ticker="AAPL", side="buy", order_type="market", qty=5),
        signal_snapshot=None,
    )

    second_snap = datetime(2026, 6, 3, 21, 30, tzinfo=timezone.utc)
    nav2 = await snapshot_nav("default", {"AAPL": 250.0}, second_snap)

    rows = await _nav_rows_for_account("default")
    assert len(rows) == 1, "INSERT OR REPLACE should keep exactly one row per (account, date)"

    # Values must match the second call
    assert abs(rows[0]["market_value"] - nav2.market_value) < 1e-6
    assert abs(rows[0]["total_value"] - nav2.total_value) < 1e-6


# ---------------------------------------------------------------------------
# Test 3: no positions
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_snapshot_nav_no_positions():
    """Brand-new account with no positions → market_value=0, total=cash."""
    from services.nav_service import snapshot_nav
    from config import settings

    nav = await snapshot_nav("default", {}, _SNAP_NOW)

    assert abs(nav.market_value - 0.0) < 1e-6
    assert abs(nav.cash - settings.paper_initial_cash) < 1e-6
    assert abs(nav.total_value - settings.paper_initial_cash) < 1e-6

    rows = await _nav_rows_for_account("default")
    assert len(rows) == 1
    assert rows[0]["date"] == _SNAP_NOW.date().isoformat()


# ---------------------------------------------------------------------------
# Test 4: avg_cost fallback when price missing
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_snapshot_nav_uses_avg_cost_fallback_when_price_missing():
    """If ticker is absent from current_prices, avg_cost is used as price."""
    from services.nav_service import snapshot_nav

    adapter = PaperBrokerAdapter(
        price_fetcher=lambda t: 150.0,
        now_provider=lambda: _MARKET_OPEN_NOW,
    )
    await adapter.place_order(
        "default",
        OrderRequest(ticker="AAPL", side="buy", order_type="market", qty=10),
        signal_snapshot=None,
    )

    # current_prices is empty → fallback to avg_cost=150 → market_value=1500
    nav = await snapshot_nav("default", {}, _SNAP_NOW)

    assert abs(nav.market_value - 1500.0) < 1e-6
    # cash = 100000 - 1500 = 98500; total = 98500 + 1500 = 100000
    assert abs(nav.total_value - 100000.0) < 1e-6


# ---------------------------------------------------------------------------
# Test 5: two accounts independent
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_snapshot_nav_two_accounts_independent():
    """Snapshots for two accounts produce two distinct rows."""
    from services.nav_service import snapshot_nav

    # Insert a second account
    async with get_db() as db:
        await db.execute(
            """
            INSERT OR IGNORE INTO accounts
              (id, type, broker_adapter, display_name, initial_cash, cash_balance, created_at)
            VALUES ('alt', 'paper', 'paper', 'Alt Account', 50000.0, 50000.0, '2026-01-01T00:00:00+00:00')
            """
        )
        await db.commit()

    nav_default = await snapshot_nav("default", {}, _SNAP_NOW)
    nav_alt = await snapshot_nav("alt", {}, _SNAP_NOW)

    rows = await _nav_rows_for_account("default")
    assert len(rows) == 1
    assert rows[0]["account_id"] == "default"

    alt_rows = await _nav_rows_for_account("alt")
    assert len(alt_rows) == 1
    assert alt_rows[0]["account_id"] == "alt"

    # Values differ (different cash balances)
    assert abs(nav_default.cash - nav_alt.cash) > 1e-6


# ---------------------------------------------------------------------------
# Test 6: return value is NavPoint
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_snapshot_nav_returns_navpoint():
    """snapshot_nav returns a NavPoint with correct field values."""
    from services.nav_service import snapshot_nav

    nav = await snapshot_nav("default", {}, _SNAP_NOW)

    assert isinstance(nav, NavPoint)
    assert nav.date == _SNAP_NOW.date().isoformat()
    assert isinstance(nav.cash, float)
    assert isinstance(nav.market_value, float)
    assert isinstance(nav.total_value, float)
    assert abs(nav.total_value - (nav.cash + nav.market_value)) < 1e-9

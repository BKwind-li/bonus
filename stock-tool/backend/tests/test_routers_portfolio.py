"""Tests for /portfolio router (Task 7).

Uses httpx AsyncClient + ASGITransport (same pattern as test_routers.py).
The adapter is injected via FastAPI dependency_overrides so no real network or
DB-external adapter code runs.
"""

import pytest
from datetime import datetime
from zoneinfo import ZoneInfo
from httpx import AsyncClient, ASGITransport

from main import app
from database import get_db
from brokers.paper import PaperBrokerAdapter
import routers.portfolio as portfolio

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_ET = ZoneInfo("America/New_York")
# Wednesday 2026-06-03 14:00 ET — US market open
_MARKET_OPEN_NOW = datetime(2026, 6, 3, 14, 0, tzinfo=_ET)

FAKE_PRICE = 150.0


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_adapter() -> PaperBrokerAdapter:
    """Return a PaperBrokerAdapter that never touches the network."""
    return PaperBrokerAdapter(
        price_fetcher=lambda t: FAKE_PRICE,
        now_provider=lambda: _MARKET_OPEN_NOW,
    )


async def _get_token(client: AsyncClient) -> str:
    r = await client.post("/auth/login", json={"password": "test"})
    return r.json()["access_token"]


async def _auth_headers(client: AsyncClient) -> dict:
    token = await _get_token(client)
    return {"Authorization": f"Bearer {token}"}


async def _insert_scan_result(ticker: str, short_label: str, short_score: int,
                               long_label: str, long_score: int) -> None:
    """Insert a row into scan_results so signal snapshot injection has data."""
    async with get_db() as db:
        await db.execute(
            """
            INSERT OR REPLACE INTO scan_results
              (ticker, name, sector, market, price, change_pct,
               short_score, short_label, short_color,
               long_score, long_label, long_color,
               short_indicators, long_indicators, scanned_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                ticker, ticker, "IT", "stock", FAKE_PRICE, 0.0,
                short_score, short_label, "green",
                long_score, long_label, "green",
                "[]", "[]", "2026-06-03T14:00:00",
            ),
        )
        await db.commit()


# ---------------------------------------------------------------------------
# Fixture: override adapter + price_fetcher for every test in this module
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def inject_fake_adapter():
    """Replace the adapter and price_fetcher dependencies for all tests here."""
    fake = _make_adapter()
    app.dependency_overrides[portfolio.get_adapter] = lambda: fake
    app.dependency_overrides[portfolio.get_price_fetcher] = lambda: (lambda t: FAKE_PRICE)
    yield
    app.dependency_overrides.pop(portfolio.get_adapter, None)
    app.dependency_overrides.pop(portfolio.get_price_fetcher, None)


# ===========================================================================
# 1. Unauthorized returns 401
# ===========================================================================

@pytest.mark.asyncio
async def test_unauthorized_returns_401():
    """GET /portfolio/accounts without token → 401."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r = await client.get("/portfolio/accounts")
    assert r.status_code == 401


# ===========================================================================
# 2. GET /accounts → default account in list
# ===========================================================================

@pytest.mark.asyncio
async def test_get_accounts_returns_default():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        headers = await _auth_headers(client)
        r = await client.get("/portfolio/accounts", headers=headers)
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["id"] == "default"


# ===========================================================================
# 3. GET /accounts/nonexistent → 404
# ===========================================================================

@pytest.mark.asyncio
async def test_get_account_404_for_unknown():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        headers = await _auth_headers(client)
        r = await client.get("/portfolio/accounts/nonexistent", headers=headers)
    assert r.status_code == 404


# ===========================================================================
# 4. GET /accounts/default → AccountInfo
# ===========================================================================

@pytest.mark.asyncio
async def test_get_account_returns_default():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        headers = await _auth_headers(client)
        r = await client.get("/portfolio/accounts/default", headers=headers)
    assert r.status_code == 200
    data = r.json()
    assert data["id"] == "default"
    assert "cash_balance" in data
    assert "initial_cash" in data


# ===========================================================================
# 5. POST market buy → 201, status=filled
# ===========================================================================

@pytest.mark.asyncio
async def test_post_market_buy_success():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        headers = await _auth_headers(client)
        r = await client.post(
            "/portfolio/accounts/default/orders",
            json={"ticker": "AAPL", "side": "buy", "order_type": "market", "qty": 1},
            headers=headers,
        )
    assert r.status_code == 201
    data = r.json()
    assert data["status"] == "filled"
    assert data["ticker"] == "AAPL"
    assert data["side"] == "buy"


# ===========================================================================
# 6. POST buy with insufficient funds → 400 with 现金不足
# ===========================================================================

@pytest.mark.asyncio
async def test_post_buy_insufficient_funds_returns_400():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        headers = await _auth_headers(client)
        # 10000 shares * 150 = 1_500_000 >> initial_cash (100_000)
        r = await client.post(
            "/portfolio/accounts/default/orders",
            json={"ticker": "AAPL", "side": "buy", "order_type": "market", "qty": 10000},
            headers=headers,
        )
    assert r.status_code == 400
    assert "现金不足" in r.json()["detail"]


# ===========================================================================
# 7. POST buy AAPL with scan_results row → signal snapshot persisted
# ===========================================================================

@pytest.mark.asyncio
async def test_post_with_signal_snapshot_persisted():
    await _insert_scan_result("AAPL", "🟢 强烈看涨", 3, "看涨信号", 2)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        headers = await _auth_headers(client)
        r = await client.post(
            "/portfolio/accounts/default/orders",
            json={"ticker": "AAPL", "side": "buy", "order_type": "market", "qty": 1},
            headers=headers,
        )
    assert r.status_code == 201
    data = r.json()
    assert data["signal_score_short"] == 3
    assert data["signal_label_short"] == "🟢 强烈看涨"


# ===========================================================================
# 8. POST order with no scan_results row → signal fields all None
# ===========================================================================

@pytest.mark.asyncio
async def test_post_no_scan_results_signal_snapshot_null():
    # No scan_results row inserted for MSFT
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        headers = await _auth_headers(client)
        r = await client.post(
            "/portfolio/accounts/default/orders",
            json={"ticker": "MSFT", "side": "buy", "order_type": "market", "qty": 1},
            headers=headers,
        )
    assert r.status_code == 201
    data = r.json()
    assert data["signal_score_short"] is None
    assert data["signal_label_short"] is None
    assert data["signal_score_long"] is None
    assert data["signal_label_long"] is None


# ===========================================================================
# 9. POST limit order → status=pending, cash unchanged
# ===========================================================================

@pytest.mark.asyncio
async def test_post_limit_order_pending_status():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        headers = await _auth_headers(client)

        # Record initial cash
        acct_r = await client.get("/portfolio/accounts/default", headers=headers)
        initial_cash = acct_r.json()["cash_balance"]

        r = await client.post(
            "/portfolio/accounts/default/orders",
            json={"ticker": "AAPL", "side": "buy", "order_type": "limit",
                  "qty": 5, "limit_price": 140.0},
            headers=headers,
        )
        assert r.status_code == 201
        data = r.json()
        assert data["status"] == "pending"

        # Cash should be unchanged
        acct_r2 = await client.get("/portfolio/accounts/default", headers=headers)
        assert acct_r2.json()["cash_balance"] == initial_cash


# ===========================================================================
# 10. GET positions enriched with P&L
# ===========================================================================

@pytest.mark.asyncio
async def test_get_positions_enriched_with_pnl():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        headers = await _auth_headers(client)
        # Buy 10 AAPL @ 150 (mocked price)
        await client.post(
            "/portfolio/accounts/default/orders",
            json={"ticker": "AAPL", "side": "buy", "order_type": "market", "qty": 10},
            headers=headers,
        )

        r = await client.get("/portfolio/accounts/default/positions", headers=headers)

    assert r.status_code == 200
    positions = r.json()
    assert len(positions) == 1
    pos = positions[0]
    assert pos["ticker"] == "AAPL"
    assert pos["current_price"] == FAKE_PRICE
    assert abs(pos["market_value"] - 1500.0) < 1e-6
    assert abs(pos["unrealized_pnl"] - 0.0) < 1e-6


# ===========================================================================
# 11. GET orders filtered by status
# ===========================================================================

@pytest.mark.asyncio
async def test_get_orders_filter_by_status():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        headers = await _auth_headers(client)

        # Place 2 market orders (filled) + 1 limit order (pending, then cancel it)
        await client.post(
            "/portfolio/accounts/default/orders",
            json={"ticker": "AAPL", "side": "buy", "order_type": "market", "qty": 1},
            headers=headers,
        )
        await client.post(
            "/portfolio/accounts/default/orders",
            json={"ticker": "AAPL", "side": "buy", "order_type": "market", "qty": 1},
            headers=headers,
        )
        limit_r = await client.post(
            "/portfolio/accounts/default/orders",
            json={"ticker": "AAPL", "side": "buy", "order_type": "limit",
                  "qty": 1, "limit_price": 100.0},
            headers=headers,
        )
        limit_id = limit_r.json()["id"]
        await client.delete(
            f"/portfolio/accounts/default/orders/{limit_id}", headers=headers
        )

        r = await client.get(
            "/portfolio/accounts/default/orders?status=filled", headers=headers
        )

    assert r.status_code == 200
    orders = r.json()
    assert len(orders) == 2
    assert all(o["status"] == "filled" for o in orders)


# ===========================================================================
# 12. DELETE pending limit order → 200, returns cancelled order
# ===========================================================================

@pytest.mark.asyncio
async def test_delete_pending_limit_succeeds():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        headers = await _auth_headers(client)
        post_r = await client.post(
            "/portfolio/accounts/default/orders",
            json={"ticker": "AAPL", "side": "buy", "order_type": "limit",
                  "qty": 5, "limit_price": 100.0},
            headers=headers,
        )
        assert post_r.status_code == 201
        order_id = post_r.json()["id"]

        del_r = await client.delete(
            f"/portfolio/accounts/default/orders/{order_id}", headers=headers
        )
    assert del_r.status_code == 200
    data = del_r.json()
    assert data["status"] == "cancelled"
    assert data["id"] == order_id


# ===========================================================================
# 13. DELETE filled order → 400
# ===========================================================================

@pytest.mark.asyncio
async def test_delete_filled_order_returns_400():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        headers = await _auth_headers(client)
        post_r = await client.post(
            "/portfolio/accounts/default/orders",
            json={"ticker": "AAPL", "side": "buy", "order_type": "market", "qty": 1},
            headers=headers,
        )
        order_id = post_r.json()["id"]

        del_r = await client.delete(
            f"/portfolio/accounts/default/orders/{order_id}", headers=headers
        )
    assert del_r.status_code == 400


# ===========================================================================
# 14. DELETE nonexistent order → 404
# ===========================================================================

@pytest.mark.asyncio
async def test_delete_nonexistent_order_returns_404():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        headers = await _auth_headers(client)
        r = await client.delete(
            "/portfolio/accounts/default/orders/fake-order-id-does-not-exist",
            headers=headers,
        )
    assert r.status_code == 404


# ===========================================================================
# 15. GET nav-history → empty list when no snapshots
# ===========================================================================

@pytest.mark.asyncio
async def test_nav_history_empty_when_no_snapshots():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        headers = await _auth_headers(client)
        r = await client.get(
            "/portfolio/accounts/default/nav-history", headers=headers
        )
    assert r.status_code == 200
    assert r.json() == []


# ===========================================================================
# 16. GET nav-history → returns 3 inserted rows
# ===========================================================================

@pytest.mark.asyncio
async def test_nav_history_returns_recent():
    dates = ["2026-05-01", "2026-05-02", "2026-05-03"]
    async with get_db() as db:
        for d in dates:
            await db.execute(
                "INSERT INTO nav_history (account_id, date, cash, market_value, total_value) "
                "VALUES (?, ?, ?, ?, ?)",
                ("default", d, 100000.0, 0.0, 100000.0),
            )
        await db.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        headers = await _auth_headers(client)
        r = await client.get(
            "/portfolio/accounts/default/nav-history?days=90", headers=headers
        )
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 3
    assert data[0]["date"] == "2026-05-01"
    assert data[2]["date"] == "2026-05-03"


# ===========================================================================
# 17. GET performance with zero trades → no crash, all counts zero
# ===========================================================================

@pytest.mark.asyncio
async def test_performance_zero_trades_does_not_crash():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        headers = await _auth_headers(client)
        r = await client.get(
            "/portfolio/accounts/default/performance", headers=headers
        )
    assert r.status_code == 200
    data = r.json()
    assert data["total_trades"] == 0
    assert data["total_buys"] == 0
    assert data["total_sells"] == 0


# ===========================================================================
# 18. GET performance counts filled orders correctly
# ===========================================================================

@pytest.mark.asyncio
async def test_performance_counts_filled_orders():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        headers = await _auth_headers(client)

        # Buy 10 shares twice
        await client.post(
            "/portfolio/accounts/default/orders",
            json={"ticker": "AAPL", "side": "buy", "order_type": "market", "qty": 10},
            headers=headers,
        )
        await client.post(
            "/portfolio/accounts/default/orders",
            json={"ticker": "AAPL", "side": "buy", "order_type": "market", "qty": 10},
            headers=headers,
        )
        # Sell 5 shares
        await client.post(
            "/portfolio/accounts/default/orders",
            json={"ticker": "AAPL", "side": "sell", "order_type": "market", "qty": 5},
            headers=headers,
        )

        r = await client.get(
            "/portfolio/accounts/default/performance", headers=headers
        )

    assert r.status_code == 200
    data = r.json()
    assert data["total_trades"] == 3
    assert data["total_buys"] == 2
    assert data["total_sells"] == 1

import pytest
from httpx import AsyncClient, ASGITransport
from main import app
from database import init_db, get_db


@pytest.fixture(autouse=True)
async def setup_db():
    await init_db()
    async with get_db() as db:
        await db.execute("DELETE FROM watchlist")
        await db.execute("DELETE FROM scan_results")
        await db.execute("DELETE FROM price_alerts")
        await db.execute("DELETE FROM signal_alerts")
        await db.execute("DELETE FROM alert_history")
        await db.execute("DELETE FROM previous_signals")
        await db.commit()
    yield


async def _get_token(client):
    r = await client.post("/auth/login", json={"password": "test"})
    return r.json()["access_token"]


@pytest.mark.asyncio
async def test_create_price_alert():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        token = await _get_token(client)
        headers = {"Authorization": f"Bearer {token}"}
        r = await client.post("/alerts/price", json={
            "ticker": "AAPL", "condition": "above", "threshold": 200.0,
        }, headers=headers)
        assert r.status_code == 200
        assert "id" in r.json()


@pytest.mark.asyncio
async def test_get_price_alerts():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        token = await _get_token(client)
        headers = {"Authorization": f"Bearer {token}"}
        await client.post("/alerts/price", json={
            "ticker": "AAPL", "condition": "above", "threshold": 200.0,
        }, headers=headers)
        r = await client.get("/alerts/price", headers=headers)
        assert r.status_code == 200
        assert len(r.json()) == 1
        assert r.json()[0]["ticker"] == "AAPL"


@pytest.mark.asyncio
async def test_delete_price_alert():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        token = await _get_token(client)
        headers = {"Authorization": f"Bearer {token}"}
        cr = await client.post("/alerts/price", json={
            "ticker": "AAPL", "condition": "above", "threshold": 200.0,
        }, headers=headers)
        alert_id = cr.json()["id"]
        r = await client.delete(f"/alerts/price/{alert_id}", headers=headers)
        assert r.status_code == 200
        gr = await client.get("/alerts/price", headers=headers)
        assert len(gr.json()) == 0


@pytest.mark.asyncio
async def test_create_signal_alert():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        token = await _get_token(client)
        headers = {"Authorization": f"Bearer {token}"}
        r = await client.post("/alerts/signal", json={
            "ticker": "NVDA", "condition": "any_change",
        }, headers=headers)
        assert r.status_code == 200


@pytest.mark.asyncio
async def test_get_alert_history_empty():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        token = await _get_token(client)
        headers = {"Authorization": f"Bearer {token}"}
        r = await client.get("/alerts/history", headers=headers)
        assert r.status_code == 200
        assert isinstance(r.json(), list)
        assert len(r.json()) == 0


@pytest.mark.asyncio
async def test_unread_count_zero_initially():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        token = await _get_token(client)
        headers = {"Authorization": f"Bearer {token}"}
        r = await client.get("/alerts/unread-count", headers=headers)
        assert r.status_code == 200
        assert r.json()["count"] == 0


@pytest.mark.asyncio
async def test_check_price_alerts_triggers_above():
    """When current price exceeds 'above' threshold, alert is recorded."""
    from services.notifier import check_price_alerts

    async with get_db() as db:
        await db.execute(
            "INSERT INTO price_alerts (ticker, condition, threshold) VALUES (?,?,?)",
            ("AAPL", "above", 100.0),
        )
        await db.commit()

    # Price 150 > threshold 100, should trigger
    await check_price_alerts("AAPL", 150.0)

    async with get_db() as db:
        cur = await db.execute("SELECT COUNT(*) FROM alert_history WHERE ticker='AAPL'")
        row = await cur.fetchone()
    assert row[0] >= 1


@pytest.mark.asyncio
async def test_check_signal_alerts_strong_only():
    """When new short_score is ±3 or ±4, 'strong_only' alert triggers."""
    from services.notifier import check_signal_alerts

    async with get_db() as db:
        await db.execute(
            "INSERT INTO signal_alerts (ticker, condition) VALUES (?,?)",
            ("NVDA", "strong_only"),
        )
        await db.commit()

    # short_score=4 should trigger strong_only
    await check_signal_alerts("NVDA", 4, 2, 60.0)

    async with get_db() as db:
        cur = await db.execute("SELECT COUNT(*) FROM alert_history WHERE ticker='NVDA'")
        row = await cur.fetchone()
    assert row[0] >= 1


@pytest.mark.asyncio
async def test_check_signal_alerts_rsi_extreme():
    """When daily RSI <30 or >70, 'rsi_extreme' alert triggers."""
    from services.notifier import check_signal_alerts

    async with get_db() as db:
        await db.execute(
            "INSERT INTO signal_alerts (ticker, condition) VALUES (?,?)",
            ("TSLA", "rsi_extreme"),
        )
        await db.commit()

    # RSI 25 < 30, should trigger
    await check_signal_alerts("TSLA", 0, 0, 25.0)

    async with get_db() as db:
        cur = await db.execute("SELECT COUNT(*) FROM alert_history WHERE ticker='TSLA'")
        row = await cur.fetchone()
    assert row[0] >= 1

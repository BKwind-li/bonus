import pytest
from httpx import AsyncClient, ASGITransport
from main import app
from database import get_db


async def _get_token(client):
    r = await client.post("/auth/login", json={"password": "test"})
    return r.json()["access_token"]


@pytest.mark.asyncio
async def test_watchlist_add_and_get():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        token = await _get_token(client)
        headers = {"Authorization": f"Bearer {token}"}
        r = await client.post("/watchlist", json={
            "ticker": "AAPL", "name": "苹果",
            "market": "stock", "sector": "信息技术·消费电子",
        }, headers=headers)
        assert r.status_code == 200
        r2 = await client.get("/watchlist", headers=headers)
        assert r2.status_code == 200
        tickers = [item["ticker"] for item in r2.json()]
        assert "AAPL" in tickers


@pytest.mark.asyncio
async def test_watchlist_delete():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        token = await _get_token(client)
        headers = {"Authorization": f"Bearer {token}"}
        await client.post("/watchlist", json={
            "ticker": "TSLA", "name": "特斯拉",
            "market": "stock", "sector": "非必需消费·电动车",
        }, headers=headers)
        r = await client.delete("/watchlist/TSLA", headers=headers)
        assert r.status_code == 200
        r2 = await client.get("/watchlist", headers=headers)
        tickers = [item["ticker"] for item in r2.json()]
        assert "TSLA" not in tickers


@pytest.mark.asyncio
async def test_scanner_results_returns_list():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        token = await _get_token(client)
        headers = {"Authorization": f"Bearer {token}"}
        r = await client.get("/scanner/results", headers=headers)
        assert r.status_code == 200
        assert isinstance(r.json(), list)


@pytest.mark.asyncio
async def test_scanner_results_filtering():
    """Verify filter actually selects matching rows."""
    async with get_db() as db:
        # Insert one bullish stock and one bearish forex
        await db.execute("""
            INSERT INTO scan_results
            (ticker, name, sector, market, price, change_pct,
             short_score, short_label, short_color,
             long_score, long_label, long_color,
             short_indicators, long_indicators, scanned_at)
            VALUES
            ('AAPL', '苹果', 'IT', 'stock', 100, 1.0, 3, '强烈看涨', 'green', 2, '看涨信号', 'green', '[]', '[]', '2026-04-27T00:00:00'),
            ('EURUSD=X', '欧美', 'FX', 'forex', 1.1, -0.1, -3, '强烈看跌', 'red', -2, '看跌信号', 'red', '[]', '[]', '2026-04-27T00:00:00')
        """)
        await db.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        token = await _get_token(client)
        headers = {"Authorization": f"Bearer {token}"}

        # Filter by market=stock should return only AAPL
        r = await client.get("/scanner/results?market=stock", headers=headers)
        tickers = [x["ticker"] for x in r.json()]
        assert "AAPL" in tickers
        assert "EURUSD=X" not in tickers

        # Filter by signal_type=bullish should return only AAPL (positive scores)
        r = await client.get("/scanner/results?signal_type=bullish", headers=headers)
        tickers = [x["ticker"] for x in r.json()]
        assert "AAPL" in tickers
        assert "EURUSD=X" not in tickers

        # Filter by signal_type=bearish should return only EURUSD=X
        r = await client.get("/scanner/results?signal_type=bearish", headers=headers)
        tickers = [x["ticker"] for x in r.json()]
        assert "EURUSD=X" in tickers
        assert "AAPL" not in tickers


@pytest.mark.asyncio
async def test_scanner_last_scan_time():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        token = await _get_token(client)
        headers = {"Authorization": f"Bearer {token}"}
        r = await client.get("/scanner/last-scan-time", headers=headers)
        assert r.status_code == 200
        assert "last_scan" in r.json()


@pytest.mark.asyncio
async def test_analysis_unknown_ticker_404():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        token = await _get_token(client)
        headers = {"Authorization": f"Bearer {token}"}
        r = await client.get("/analysis/UNKNOWN_XYZ_999", headers=headers)
        assert r.status_code == 404


@pytest.mark.asyncio
async def test_analysis_deep_without_api_key_returns_501():
    """When CLAUDE_API_KEY is empty, deep analysis should return 501 Not Implemented."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        token = await _get_token(client)
        headers = {"Authorization": f"Bearer {token}"}
        # AAPL is in our universe; no Claude key in test env → 501
        r = await client.post("/analysis/AAPL/deep", headers=headers)
        assert r.status_code == 501

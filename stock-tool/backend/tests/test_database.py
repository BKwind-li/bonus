import pytest
import aiosqlite
from database import init_db, get_db


@pytest.mark.asyncio
async def test_init_db_creates_tables():
    await init_db()
    async with get_db() as db:
        cursor = await db.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
        tables = {row[0] for row in await cursor.fetchall()}
    assert "watchlist" in tables
    assert "scan_results" in tables
    assert "price_alerts" in tables
    assert "signal_alerts" in tables
    assert "alert_history" in tables
    assert "previous_signals" in tables

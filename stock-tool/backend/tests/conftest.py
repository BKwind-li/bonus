import os
import atexit
import tempfile

# Set env vars BEFORE config/database modules are imported
os.environ.setdefault("APP_PASSWORD", "test")
os.environ.setdefault(
    "SECRET_KEY",
    "test-secret-key-for-testing-only-64chars-padded-padding-padding-pad",
)

_TEST_DB = tempfile.NamedTemporaryFile(delete=False, suffix=".db").name
os.environ.setdefault("DATABASE_URL", _TEST_DB)
os.environ.setdefault("SMTP_HOST", "localhost")
os.environ.setdefault("SMTP_USER", "")
os.environ.setdefault("NOTIFY_EMAIL", "")


@atexit.register
def _cleanup_test_db():
    """Remove the temp DB file at session exit so it doesn't accumulate in %TEMP%."""
    try:
        os.unlink(_TEST_DB)
    except OSError:
        pass


import pytest


@pytest.fixture(autouse=True)
async def clean_db():
    """Initialize DB and clear all tables before each test."""
    from database import init_db, get_db
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

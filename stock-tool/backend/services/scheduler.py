import asyncio
import logging
from datetime import datetime, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from database import get_db
from services.scanner_service import run_full_scan

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


async def _scheduled_scan():
    async with get_db() as db:
        count = await run_full_scan(db)
    print(f"[Scheduler] Scan complete: {count} assets processed")


async def _scheduled_nav_snapshot():
    """Daily NAV snapshot for all accounts.

    1. Fetch all account ids from the accounts table.
    2. For each account, gather its positions and look up current prices
       concurrently via fetch_current_price (wrapped in asyncio.to_thread).
    3. Call snapshot_nav for each account and log the result.
    """
    from services.data_fetcher import fetch_current_price
    from services.nav_service import snapshot_nav

    # 1. Fetch all account ids
    async with get_db() as db:
        async with db.execute("SELECT id FROM accounts") as cursor:
            account_rows = await cursor.fetchall()

    account_ids = [row["id"] for row in account_rows]
    if not account_ids:
        logger.info("[Scheduler] NAV snapshot: no accounts found, skipping")
        return

    now = datetime.now(timezone.utc)

    for account_id in account_ids:
        # 2. Gather tickers for this account
        async with get_db() as db:
            async with db.execute(
                "SELECT ticker FROM positions WHERE account_id = ?", (account_id,)
            ) as cursor:
                pos_rows = await cursor.fetchall()

        tickers = [row["ticker"] for row in pos_rows]

        # Fetch prices concurrently
        if tickers:
            prices_list = await asyncio.gather(
                *[asyncio.to_thread(fetch_current_price, t) for t in tickers]
            )
            current_prices = {
                t: p for t, p in zip(tickers, prices_list) if p is not None
            }
        else:
            current_prices = {}

        # 3. Snapshot and log
        nav = await snapshot_nav(account_id, current_prices, now)
        logger.info(
            "[Scheduler] NAV snapshot account=%s date=%s total=%.2f",
            account_id,
            nav.date,
            nav.total_value,
        )


def start_scheduler():
    """Schedule scans:
    - US stocks: every weekday at 21:05 UTC (16:05 ET, after market close)
    - FX market: every 4 hours (24-hour market)
    - NAV snapshot: every weekday at 21:30 UTC (after the 21:05 stock scan)
    Note: both scan triggers fire run_full_scan; scanning is universe-wide.
    """
    scheduler.add_job(
        _scheduled_scan,
        CronTrigger(day_of_week="mon-fri", hour=21, minute=5),
        id="stock_scan",
        replace_existing=True,
    )
    scheduler.add_job(_scheduled_scan, CronTrigger(hour="0,4,8,12,16,20"), id="fx_scan", replace_existing=True)
    scheduler.add_job(
        _scheduled_nav_snapshot,
        CronTrigger(day_of_week="mon-fri", hour=21, minute=30),
        id="nav_snapshot",
        replace_existing=True,
    )
    scheduler.start()


def stop_scheduler():
    """Shutdown scheduler. Safe to call when scheduler is not running."""
    if scheduler.running:
        scheduler.shutdown()

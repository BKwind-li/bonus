from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from database import get_db
from services.scanner_service import run_full_scan

scheduler = AsyncIOScheduler()


async def _scheduled_scan():
    async with get_db() as db:
        count = await run_full_scan(db)
    print(f"[Scheduler] Scan complete: {count} assets processed")


def start_scheduler():
    """Schedule scans:
    - US stocks: every weekday at 21:05 UTC (16:05 ET, after market close)
    - FX market: every 4 hours (24-hour market)
    Note: both triggers fire run_full_scan; scanning is universe-wide.
    """
    scheduler.add_job(_scheduled_scan, CronTrigger(hour=21, minute=5), id="stock_scan", replace_existing=True)
    scheduler.add_job(_scheduled_scan, CronTrigger(hour="0,4,8,12,16,20"), id="fx_scan", replace_existing=True)
    scheduler.start()


def stop_scheduler():
    """Shutdown scheduler. Safe to call when scheduler is not running."""
    if scheduler.running:
        scheduler.shutdown()

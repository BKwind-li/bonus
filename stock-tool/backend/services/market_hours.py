"""Market-hours helpers for US equities and forex.

Pure functions — no DB access, no side effects.
Caller injects `now` so tests remain deterministic.
"""
from datetime import datetime, time
from zoneinfo import ZoneInfo

from data.universe import is_forex

ET = ZoneInfo("America/New_York")
_UTC = ZoneInfo("UTC")

_OPEN = time(9, 30)
_CLOSE = time(16, 0)


def is_us_market_open(now: datetime) -> bool:
    """True if *now* falls inside US equity regular-session hours.

    Rules (MVP — no holiday calendar):
    - Monday–Friday only (US Eastern Time)
    - 09:30 (inclusive) to 16:00 (exclusive) ET
    - Naive datetimes are treated as UTC.

    Holidays (Thanksgiving, Christmas, etc.) are NOT handled in MVP — accepted
    risk; can be addressed later by integrating pandas_market_calendars.
    """
    # Attach UTC to naive datetimes so astimezone() converts correctly.
    if now.tzinfo is None:
        now = now.replace(tzinfo=_UTC)

    et_now = now.astimezone(ET)

    # Weekends (Monday=0 … Sunday=6)
    if et_now.weekday() >= 5:
        return False

    t = et_now.time()
    return _OPEN <= t < _CLOSE


def is_forex_market_open(now: datetime) -> bool:  # noqa: ARG001
    """True for FX (24/5 simplification: always True).

    The real FX market closes weekends, but for MVP we accept 24/7 paper FX
    fills.  This function exists for future tightening (e.g. closing
    Sat 00:00 UTC – Sun 22:00 UTC) without changing callers.
    """
    return True


def should_queue_order(ticker: str, now: datetime) -> bool:
    """True if a market order on *ticker* should be queued (closed market).

    - Forex: never queue (always open in MVP).
    - Stocks: queue when US equity market is closed.
    """
    if is_forex(ticker):
        return False
    return not is_us_market_open(now)

"""Tests for services/market_hours.py — all synchronous, no asyncio."""
from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from services.market_hours import (
    is_forex_market_open,
    is_us_market_open,
    should_queue_order,
)

ET = ZoneInfo("America/New_York")


# ---------------------------------------------------------------------------
# is_us_market_open — parametrized
# ---------------------------------------------------------------------------

# Helper: build a tz-aware ET datetime
def _et(year, month, day, hour, minute=0, second=0):
    return datetime(year, month, day, hour, minute, second, tzinfo=ET)


@pytest.mark.parametrize(
    "dt, expected",
    [
        # 1. Wednesday 14:00 ET — inside regular session
        (_et(2026, 6, 3, 14, 0), True),
        # 2. Wednesday 03:00 ET — pre-market
        (_et(2026, 6, 3, 3, 0), False),
        # 3. Wednesday 16:30 ET — after-hours
        (_et(2026, 6, 3, 16, 30), False),
        # 4. Saturday
        (_et(2026, 6, 6, 12, 0), False),
        # 5. Sunday
        (_et(2026, 6, 7, 12, 0), False),
        # 6. Friday 16:00 ET — exclusive upper boundary
        (_et(2026, 6, 5, 16, 0), False),
        # 7. Friday 15:59:59 ET — still open
        (_et(2026, 6, 5, 15, 59, 59), True),
        # 8. Monday 09:30 ET — inclusive lower boundary
        (_et(2026, 6, 1, 9, 30), True),
        # 9. Monday 09:29 ET — pre-open
        (_et(2026, 6, 1, 9, 29), False),
        # 10. Naive UTC: 2026-06-03 18:00 UTC = 14:00 EDT (DST active)
        (datetime(2026, 6, 3, 18, 0), True),
        # 11. DST boundary: Wednesday just after spring-forward 2026 (Mar 8)
        #     09:30 ET on 2026-03-11 (the first Wednesday after DST starts 2026-03-08)
        (_et(2026, 3, 11, 9, 30), True),
    ],
)
def test_is_us_market_open(dt, expected):
    assert is_us_market_open(dt) == expected


# ---------------------------------------------------------------------------
# is_forex_market_open — always True
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "dt",
    [
        _et(2026, 6, 3, 14, 0),   # weekday, market hours
        _et(2026, 6, 6, 12, 0),   # Saturday
        datetime(2026, 1, 1, 0, 0),  # New Year's Day (naive)
    ],
)
def test_is_forex_market_open_always_true(dt):
    assert is_forex_market_open(dt) is True


# ---------------------------------------------------------------------------
# should_queue_order — parametrized
# ---------------------------------------------------------------------------

_WEEKDAY_OPEN = _et(2026, 6, 3, 14, 0)    # Wednesday 14:00 ET — market open
_WEEKEND = _et(2026, 6, 6, 12, 0)         # Saturday — market closed
_AFTER_HOURS = _et(2026, 6, 3, 17, 0)     # Wednesday 17:00 ET — after close


@pytest.mark.parametrize(
    "ticker, dt, expected",
    [
        # 1. Forex — never queue
        ("EURUSD=X", _WEEKDAY_OPEN, False),
        # 1b. Forex on weekend — still never queue
        ("EURUSD=X", _WEEKEND, False),
        # 2. Stock during market hours — do not queue
        ("AAPL", _WEEKDAY_OPEN, False),
        # 3. Stock on weekend — queue
        ("AAPL", _WEEKEND, True),
        # 4. Stock after hours — queue
        ("AAPL", _AFTER_HOURS, True),
    ],
)
def test_should_queue_order(ticker, dt, expected):
    assert should_queue_order(ticker, dt) == expected

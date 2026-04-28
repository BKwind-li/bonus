import pytest
import json
from unittest.mock import patch, AsyncMock
from services.scanner_service import scan_single, build_signal_result
from services.data_fetcher import OHLCVData
import pandas as pd
import numpy as np


def _mock_ohlcv() -> OHLCVData:
    n = 60
    np.random.seed(1)
    close = 100 + np.cumsum(np.random.randn(n) * 0.5)
    df_daily = pd.DataFrame({
        "Open": close * 0.999,
        "High": close * 1.005,
        "Low": close * 0.995,
        "Close": close,
        "Volume": np.random.randint(1_000_000, 5_000_000, n).astype(float),
    })
    df_weekly = df_daily.copy()
    return OHLCVData("AAPL", df_daily, df_weekly, float(close[-1]), 1.5)


def test_build_signal_result():
    data = _mock_ohlcv()
    result = build_signal_result(
        ticker="AAPL",
        name="苹果",
        sector="信息技术·消费电子",
        market="stock",
        ohlcv=data,
    )
    assert result.ticker == "AAPL"
    assert result.name == "苹果"
    assert result.market == "stock"
    assert result.short_term.score in range(-4, 5)
    assert result.long_term.score in range(-4, 5)
    assert result.price > 0
    assert len(result.short_term.indicators) == 4
    assert len(result.long_term.indicators) == 4


def test_scan_single_returns_none_on_bad_ticker():
    with patch("services.scanner_service.fetch_ohlcv", return_value=None):
        result = scan_single("INVALID_XYZ", "无效", "无", "stock")
    assert result is None


def test_scan_single_returns_signal_on_valid():
    with patch("services.scanner_service.fetch_ohlcv", return_value=_mock_ohlcv()):
        result = scan_single("AAPL", "苹果", "信息技术·消费电子", "stock")
    assert result is not None
    assert result.ticker == "AAPL"


@pytest.mark.asyncio
async def test_run_full_scan_skips_invalid_tickers():
    """run_full_scan should silently skip tickers that fail to fetch."""
    from services.scanner_service import run_full_scan
    from database import get_db, init_db

    await init_db()

    # Mock fetch_ohlcv to return None for all tickers
    with patch("services.scanner_service.fetch_ohlcv", return_value=None):
        async with get_db() as db:
            count = await run_full_scan(db)

    assert count == 0  # all tickers failed → 0 successful scans

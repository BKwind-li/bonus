import pytest
from services.data_fetcher import fetch_ohlcv, OHLCVData


@pytest.mark.network
def test_fetch_daily_stock():
    data = fetch_ohlcv("AAPL")
    assert isinstance(data, OHLCVData)
    assert len(data.daily) >= 15
    assert all(col in data.daily.columns for col in ["Open", "High", "Low", "Close", "Volume"])
    assert data.current_price > 0


@pytest.mark.network
def test_fetch_daily_forex():
    data = fetch_ohlcv("EURUSD=X")
    assert isinstance(data, OHLCVData)
    assert len(data.daily) >= 15


@pytest.mark.network
def test_fetch_returns_weekly():
    data = fetch_ohlcv("AAPL")
    assert len(data.weekly) >= 30


@pytest.mark.network
def test_fetch_invalid_ticker_returns_none():
    data = fetch_ohlcv("INVALID_TICKER_XYZ_NONEXISTENT")
    assert data is None

import pytest
import pandas as pd
import numpy as np
from services.indicator_engine import calculate_indicators, IndicatorValues

def _make_ohlcv(n=60) -> pd.DataFrame:
    np.random.seed(42)
    close = 100 + np.cumsum(np.random.randn(n) * 0.5)
    volume = np.random.randint(1_000_000, 5_000_000, n).astype(float)
    return pd.DataFrame({
        "Open": close * 0.999,
        "High": close * 1.005,
        "Low": close * 0.995,
        "Close": close,
        "Volume": volume,
    })

def test_calculate_returns_indicator_values():
    df = _make_ohlcv(60)
    vals = calculate_indicators(df)
    assert isinstance(vals, IndicatorValues)

def test_ema_values_present():
    df = _make_ohlcv(60)
    vals = calculate_indicators(df)
    assert vals.ema_20 is not None
    assert vals.ema_50 is not None
    # ema_200 may be None when n=60 (insufficient data) — that's expected

def test_ema_200_present_with_sufficient_data():
    df = _make_ohlcv(250)
    vals = calculate_indicators(df)
    assert vals.ema_200 is not None

def test_rsi_in_range():
    df = _make_ohlcv(60)
    vals = calculate_indicators(df)
    assert 0 <= vals.rsi_daily <= 100

def test_macd_present():
    df = _make_ohlcv(60)
    vals = calculate_indicators(df)
    assert vals.macd_line is not None
    assert vals.macd_signal is not None

def test_volume_ratio():
    df = _make_ohlcv(60)
    vals = calculate_indicators(df)
    assert vals.volume_ratio > 0

def test_weekly_rsi_present():
    df = _make_ohlcv(60)
    vals = calculate_indicators(df, is_weekly=True)
    assert 0 <= vals.rsi_weekly <= 100

def test_returns_none_for_long_emas_on_short_data():
    df = _make_ohlcv(10)  # not enough for EMA 50
    vals = calculate_indicators(df)
    assert vals.ema_50 is None
    assert vals.ema_200 is None

def test_current_price_is_last_close():
    df = _make_ohlcv(60)
    vals = calculate_indicators(df)
    assert vals.current_price == pytest.approx(df["Close"].iloc[-1])

import pandas as pd
import pandas_ta_classic as ta
from dataclasses import dataclass


@dataclass
class IndicatorValues:
    # EMA
    ema_20: float | None
    ema_50: float | None
    ema_200: float | None
    ema_200_slope: float | None  # EMA200 slope over last 20 bars (positive = uptrend)
    # RSI
    rsi_daily: float
    rsi_weekly: float
    # MACD
    macd_line: float | None
    macd_signal: float | None
    # Volume
    volume_ratio: float  # current / 20-bar avg
    # Price
    current_price: float


def calculate_indicators(df: pd.DataFrame, is_weekly: bool = False) -> IndicatorValues:
    """Calculate technical indicators on an OHLCV DataFrame.

    is_weekly: if True, the input is weekly bars; rsi is stored in rsi_weekly,
               and rsi_daily defaults to 50. If False (default), rsi is stored
               in rsi_daily and rsi_weekly defaults to 50.
    """
    close = df["Close"]
    volume = df.get("Volume", pd.Series(dtype=float))
    n = len(close)

    def _ema(period: int) -> float | None:
        if n < period:
            return None
        result = ta.ema(close, length=period)
        if result is None or result.empty:
            return None
        val = result.iloc[-1]
        return float(val) if not pd.isna(val) else None

    ema_20 = _ema(20)
    ema_50 = _ema(50)
    ema_200 = _ema(200)

    # EMA200 slope: compare current EMA200 to EMA200 from 20 bars ago
    ema_200_slope: float | None = None
    if ema_200 is not None and n >= 220:
        ema200_series = ta.ema(close, length=200)
        if ema200_series is not None and len(ema200_series) >= 20:
            prev = ema200_series.iloc[-20]
            curr = ema200_series.iloc[-1]
            if not pd.isna(prev) and not pd.isna(curr):
                ema_200_slope = float(curr - prev)

    # RSI
    rsi_series = ta.rsi(close, length=14)
    rsi_val = 50.0
    if rsi_series is not None and not rsi_series.empty:
        v = rsi_series.iloc[-1]
        if not pd.isna(v):
            rsi_val = float(v)

    rsi_daily = rsi_val if not is_weekly else 50.0
    rsi_weekly = rsi_val if is_weekly else 50.0

    # MACD (12, 26, 9)
    macd_line: float | None = None
    macd_signal: float | None = None
    if n >= 26:
        macd_df = ta.macd(close, fast=12, slow=26, signal=9)
        if macd_df is not None and not macd_df.empty:
            ml = macd_df.iloc[-1].get("MACD_12_26_9")
            ms = macd_df.iloc[-1].get("MACDs_12_26_9")
            if ml is not None and not pd.isna(ml):
                macd_line = float(ml)
            if ms is not None and not pd.isna(ms):
                macd_signal = float(ms)

    # Volume ratio: current / 20-bar avg
    volume_ratio = 1.0
    if not volume.empty and len(volume) >= 20:
        avg = volume.iloc[-20:].mean()
        if avg > 0:
            volume_ratio = float(volume.iloc[-1] / avg)

    return IndicatorValues(
        ema_20=ema_20,
        ema_50=ema_50,
        ema_200=ema_200,
        ema_200_slope=ema_200_slope,
        rsi_daily=rsi_daily,
        rsi_weekly=rsi_weekly,
        macd_line=macd_line,
        macd_signal=macd_signal,
        volume_ratio=volume_ratio,
        current_price=float(close.iloc[-1]),
    )

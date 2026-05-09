import yfinance as yf
import pandas as pd
import requests
from dataclasses import dataclass


@dataclass
class OHLCVData:
    ticker: str
    daily: pd.DataFrame
    weekly: pd.DataFrame
    current_price: float
    change_pct: float


def _fetch_via_query2(ticker: str, interval: str, range_: str) -> pd.DataFrame:
    """Fetch OHLCV from Yahoo Finance query2 API directly (no crumb required)."""
    session = requests.Session()
    session.headers.update({
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
    })
    url = f"https://query2.finance.yahoo.com/v8/finance/chart/{ticker}"
    params = {"interval": interval, "range": range_}
    try:
        r = session.get(url, params=params, timeout=30)
        if r.status_code != 200:
            return pd.DataFrame()
        data = r.json()
    except Exception:
        return pd.DataFrame()

    result = data.get("chart", {}).get("result")
    if not result:
        return pd.DataFrame()

    result = result[0]
    timestamps = result.get("timestamp", [])
    if not timestamps:
        return pd.DataFrame()

    quote = result["indicators"]["quote"][0]
    df = pd.DataFrame(
        {
            "Open": quote.get("open", []),
            "High": quote.get("high", []),
            "Low": quote.get("low", []),
            "Close": quote.get("close", []),
            "Volume": quote.get("volume", []),
        },
        index=pd.to_datetime(timestamps, unit="s", utc=True),
    )
    df.index.name = "Date"
    return df.dropna(subset=["Close"])


def _fetch_via_yfinance(ticker: str, period_daily: str, period_weekly: str):
    """Fetch via yfinance library (requires crumb; may fail if rate-limited)."""
    tk = yf.Ticker(ticker)
    daily = tk.history(period=period_daily, interval="1d")
    weekly = tk.history(period=period_weekly, interval="1wk")
    return daily, weekly


def _to_utc(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize a DataFrame's DatetimeIndex to UTC, regardless of source timezone."""
    if df.empty:
        return df
    if df.index.tz is None:
        df.index = df.index.tz_localize("UTC")
    else:
        df.index = df.index.tz_convert("UTC")
    return df


def fetch_ohlcv(ticker: str) -> "OHLCVData | None":
    """Fetch 2 years of daily and 2 years of weekly OHLCV for a ticker.

    The daily window must be ≥ ~220 trading days for the long-term signal
    indicators to compute (EMA200 needs 200 bars; EMA200-slope reads back
    20 bars further). 2 years (~504 trading days) gives ample headroom.

    Tries direct Yahoo Finance API first; falls back to yfinance library.
    Returns None if ticker is invalid or insufficient data.
    """
    try:
        daily = _fetch_via_query2(ticker, "1d", "2y")
        weekly = _fetch_via_query2(ticker, "1wk", "2y")

        # Fallback to yfinance if either frame is missing (partial rate-limit / transient error)
        if daily.empty or weekly.empty:
            try:
                daily_fb, weekly_fb = _fetch_via_yfinance(ticker, "2y", "2y")
                if daily.empty:
                    daily = daily_fb
                if weekly.empty:
                    weekly = weekly_fb
            except Exception:
                pass

        # Normalize both indexes to UTC so pandas-ta operations align correctly
        daily = _to_utc(daily)
        weekly = _to_utc(weekly)

        if daily.empty or len(daily) < 5:
            return None

        current_price = float(daily["Close"].iloc[-1])
        prev_price = float(daily["Close"].iloc[-2]) if len(daily) >= 2 else current_price
        change_pct = (current_price - prev_price) / prev_price * 100 if prev_price else 0.0

        return OHLCVData(
            ticker=ticker,
            daily=daily,
            weekly=weekly,
            current_price=round(current_price, 4),
            change_pct=round(change_pct, 2),
        )
    except Exception:
        return None


def fetch_current_price(ticker: str) -> float | None:
    """Return the most recent closing price for *ticker*, or None on failure.

    Thin wrapper around :func:`fetch_ohlcv` for use by the broker adapter
    and any other caller that only needs a single float rather than the full
    OHLCV frame.  The result is injected into :class:`~brokers.paper.PaperBrokerAdapter`
    as ``price_fetcher`` so tests can monkeypatch without touching the network.
    """
    data = fetch_ohlcv(ticker)
    if data is None:
        return None
    return data.current_price

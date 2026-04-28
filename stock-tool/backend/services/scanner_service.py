import asyncio
import json
from datetime import datetime, timezone
from models import SignalResult
from services.data_fetcher import fetch_ohlcv, OHLCVData
from services.indicator_engine import calculate_indicators
from services.signal_engine import compute_short_term, compute_long_term
from data.universe import get_all_tickers, is_forex


def build_signal_result(
    ticker: str, name: str, sector: str, market: str, ohlcv: OHLCVData
) -> SignalResult:
    """Compute short and long term signals from OHLCV data."""
    daily_vals = calculate_indicators(ohlcv.daily)
    weekly_vals = calculate_indicators(ohlcv.weekly, is_weekly=True)

    # Merge weekly RSI into daily IndicatorValues for the long-term signal
    daily_vals.rsi_weekly = weekly_vals.rsi_weekly

    short_term = compute_short_term(daily_vals)
    long_term = compute_long_term(daily_vals)

    return SignalResult(
        ticker=ticker,
        name=name,
        sector=sector,
        market=market,
        price=ohlcv.current_price,
        change_pct=ohlcv.change_pct,
        short_term=short_term,
        long_term=long_term,
        scanned_at=datetime.now(timezone.utc),
    )


def scan_single(ticker: str, name: str, sector: str, market: str) -> SignalResult | None:
    """Fetch and analyze one ticker. Returns None if data unavailable."""
    ohlcv = fetch_ohlcv(ticker)
    if ohlcv is None:
        return None
    return build_signal_result(ticker, name, sector, market, ohlcv)


async def run_full_scan(db) -> int:
    """Scan all universe assets, persist results to DB. Returns count of successful scans.

    Also triggers price + signal alert checks per ticker (handled by services/notifier).
    """
    # Lazy imports to avoid circular import issues with notifier
    from services.notifier import check_price_alerts, check_signal_alerts

    tickers = get_all_tickers()
    count = 0
    for item in tickers:
        ticker = item["ticker"]
        try:
            market = "forex" if is_forex(ticker) else "stock"
            result = await asyncio.to_thread(
                scan_single, ticker, item["name"], item["sector"], market
            )
            if result is None:
                continue
            await db.execute(
                """
                INSERT OR REPLACE INTO scan_results
                (ticker, name, sector, market, price, change_pct,
                 short_score, short_label, short_color,
                 long_score, long_label, long_color,
                 short_indicators, long_indicators, scanned_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    result.ticker, result.name, result.sector, result.market,
                    result.price, result.change_pct,
                    result.short_term.score, result.short_term.label, result.short_term.color,
                    result.long_term.score, result.long_term.label, result.long_term.color,
                    json.dumps([i.model_dump() for i in result.short_term.indicators]),
                    json.dumps([i.model_dump() for i in result.long_term.indicators]),
                    result.scanned_at.isoformat(),
                ),
            )
            rsi_raw = next(
                (float(ind.raw_value) for ind in result.short_term.indicators if ind.name == "RSI(14)"),
                50.0,
            )
            await check_price_alerts(ticker, result.price)
            await check_signal_alerts(
                ticker, result.short_term.score, result.long_term.score, rsi_raw
            )
            count += 1
        except Exception as exc:
            print(f"[Scanner] {ticker} failed: {exc}")
            continue
    await db.commit()
    return count

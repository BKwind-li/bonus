from models import SignalScore, IndicatorResult
from services.indicator_engine import IndicatorValues
from services import templates


def score_to_label(score: int) -> tuple[str, str]:
    """Map a numeric score (-4 to +4) to (label, color)."""
    if score >= 3:
        return "强烈看涨", "green"
    if score >= 1:
        return "看涨信号", "green"
    if score == 0:
        return "中性观望", "yellow"
    if score >= -2:
        return "看跌信号", "red"
    return "强烈看跌", "red"


def compute_short_term(vals: IndicatorValues) -> SignalScore:
    """Build short-term signal: 4 indicators, each contributing +1 or -1."""
    indicators: list[IndicatorResult] = []

    # 1. EMA 20/50
    if vals.ema_20 is not None and vals.ema_50 is not None:
        c = 1 if vals.ema_20 > vals.ema_50 else -1
        indicators.append(IndicatorResult(
            name="EMA趋势",
            raw_value=f"EMA20={vals.ema_20:.2f} / EMA50={vals.ema_50:.2f}",
            description=templates.ema_short_description(vals, c),
            contribution=c,
        ))
    else:
        indicators.append(IndicatorResult(
            name="EMA趋势", raw_value="N/A", description="数据不足", contribution=-1,
        ))

    # 2. RSI daily
    rsi = vals.rsi_daily
    c = 1 if rsi >= 50 else -1
    indicators.append(IndicatorResult(
        name="RSI(14)",
        raw_value=f"{rsi:.1f}",
        description=templates.rsi_short_description(rsi, c),
        contribution=c,
    ))

    # 3. MACD
    if vals.macd_line is not None and vals.macd_signal is not None:
        c = 1 if vals.macd_line > vals.macd_signal else -1
        indicators.append(IndicatorResult(
            name="MACD",
            raw_value=f"MACD={vals.macd_line:.3f} / Signal={vals.macd_signal:.3f}",
            description=templates.macd_description(vals.macd_line, vals.macd_signal, c),
            contribution=c,
        ))
    else:
        indicators.append(IndicatorResult(
            name="MACD", raw_value="N/A", description="数据不足", contribution=-1,
        ))

    # 4. Volume
    c = 1 if vals.volume_ratio >= 1.0 else -1
    indicators.append(IndicatorResult(
        name="成交量",
        raw_value=f"{vals.volume_ratio:.2f}x均值",
        description=templates.volume_description(vals.volume_ratio, c),
        contribution=c,
    ))

    score = sum(ind.contribution for ind in indicators)
    label, color = score_to_label(score)
    return SignalScore(score=score, label=label, color=color, indicators=indicators)


def compute_long_term(vals: IndicatorValues) -> SignalScore:
    """Build long-term signal: 4 indicators, each contributing +1 or -1."""
    indicators: list[IndicatorResult] = []

    # 1. EMA 50/200 cross
    if vals.ema_50 is not None and vals.ema_200 is not None:
        c = 1 if vals.ema_50 > vals.ema_200 else -1
        indicators.append(IndicatorResult(
            name="EMA金/死叉",
            raw_value=f"EMA50={vals.ema_50:.2f} / EMA200={vals.ema_200:.2f}",
            description=templates.ema_long_description(vals, c),
            contribution=c,
        ))
    else:
        indicators.append(IndicatorResult(
            name="EMA金/死叉", raw_value="N/A", description="数据不足", contribution=-1,
        ))

    # 2. Price vs EMA200
    if vals.ema_200 is not None:
        c = 1 if vals.current_price > vals.ema_200 else -1
        indicators.append(IndicatorResult(
            name="价格vs长期均线",
            raw_value=f"价格={vals.current_price:.2f} / EMA200={vals.ema_200:.2f}",
            description=templates.price_vs_ema200_description(vals.current_price, vals.ema_200, c),
            contribution=c,
        ))
    else:
        indicators.append(IndicatorResult(
            name="价格vs长期均线", raw_value="N/A", description="数据不足", contribution=-1,
        ))

    # 3. RSI weekly
    rsi_w = vals.rsi_weekly
    c = 1 if rsi_w >= 50 else -1
    indicators.append(IndicatorResult(
        name="周线RSI",
        raw_value=f"{rsi_w:.1f}",
        description=templates.rsi_weekly_description(rsi_w, c),
        contribution=c,
    ))

    # 4. EMA200 slope
    if vals.ema_200_slope is not None:
        c = 1 if vals.ema_200_slope > 0 else -1
        indicators.append(IndicatorResult(
            name="长期趋势斜率",
            raw_value=f"{vals.ema_200_slope:+.2f}",
            description=templates.ema200_slope_description(vals.ema_200_slope, c),
            contribution=c,
        ))
    else:
        indicators.append(IndicatorResult(
            name="长期趋势斜率", raw_value="N/A", description="数据不足", contribution=-1,
        ))

    score = sum(ind.contribution for ind in indicators)
    label, color = score_to_label(score)
    return SignalScore(score=score, label=label, color=color, indicators=indicators)

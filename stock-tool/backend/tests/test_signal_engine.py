import pytest
from services.indicator_engine import IndicatorValues
from services.signal_engine import compute_short_term, compute_long_term, score_to_label

def _make_vals(**kwargs) -> IndicatorValues:
    defaults = dict(
        ema_20=105.0, ema_50=100.0, ema_200=90.0, ema_200_slope=0.5,
        rsi_daily=60.0, rsi_weekly=55.0,
        macd_line=0.5, macd_signal=0.3,
        volume_ratio=1.4, current_price=110.0,
    )
    defaults.update(kwargs)
    return IndicatorValues(**defaults)

def test_score_to_label_strong_bullish():
    label, color = score_to_label(4)
    assert label == "强烈看涨"
    assert color == "green"

def test_score_to_label_bullish():
    label, color = score_to_label(2)
    assert label == "看涨信号"
    assert color == "green"

def test_score_to_label_neutral():
    label, color = score_to_label(0)
    assert label == "中性观望"
    assert color == "yellow"

def test_score_to_label_bearish():
    label, color = score_to_label(-2)
    assert label == "看跌信号"
    assert color == "red"

def test_score_to_label_strong_bearish():
    label, color = score_to_label(-4)
    assert label == "强烈看跌"
    assert color == "red"

def test_score_to_label_score_3_is_strong_bullish():
    label, color = score_to_label(3)
    assert label == "强烈看涨"
    assert color == "green"

def test_score_to_label_score_1_is_bullish():
    label, color = score_to_label(1)
    assert label == "看涨信号"
    assert color == "green"

def test_score_to_label_score_minus_1_is_bearish():
    label, color = score_to_label(-1)
    assert label == "看跌信号"
    assert color == "red"

def test_score_to_label_score_minus_3_is_strong_bearish():
    label, color = score_to_label(-3)
    assert label == "强烈看跌"
    assert color == "red"

def test_short_term_all_bullish():
    vals = _make_vals(
        ema_20=105, ema_50=100, rsi_daily=60,
        macd_line=0.5, macd_signal=0.3, volume_ratio=1.5
    )
    score = compute_short_term(vals)
    assert score.score == 4
    assert score.color == "green"
    assert len(score.indicators) == 4

def test_short_term_all_bearish():
    vals = _make_vals(
        ema_20=95, ema_50=100, rsi_daily=40,
        macd_line=-0.5, macd_signal=-0.3, volume_ratio=0.8
    )
    score = compute_short_term(vals)
    assert score.score == -4

def test_long_term_all_bullish():
    vals = _make_vals(
        ema_50=105, ema_200=100, ema_200_slope=0.5,
        rsi_weekly=60, current_price=110
    )
    score = compute_long_term(vals)
    assert score.score == 4

def test_long_term_all_bearish():
    vals = _make_vals(
        ema_50=95, ema_200=100, ema_200_slope=-0.5,
        rsi_weekly=40, current_price=90
    )
    score = compute_long_term(vals)
    assert score.score == -4

def test_indicators_have_descriptions():
    vals = _make_vals()
    score = compute_short_term(vals)
    for ind in score.indicators:
        assert len(ind.description) > 0
        assert ind.contribution in (-1, 1)
        assert len(ind.name) > 0

def test_short_term_handles_none_emas():
    """When EMA data is unavailable, indicator still produces a contribution and description."""
    vals = _make_vals(ema_20=None, ema_50=None)
    score = compute_short_term(vals)
    assert len(score.indicators) == 4  # still 4 indicators

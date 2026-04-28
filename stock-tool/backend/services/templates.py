from services.indicator_engine import IndicatorValues


def ema_short_description(vals: IndicatorValues, contribution: int) -> str:
    if vals.ema_20 is None or vals.ema_50 is None:
        return "EMA数据不足"
    if contribution == 1:
        return f"短期均线(EMA20={vals.ema_20:.2f})上穿长期均线(EMA50={vals.ema_50:.2f})，趋势向上"
    return f"短期均线(EMA20={vals.ema_20:.2f})下穿长期均线(EMA50={vals.ema_50:.2f})，趋势向下"


def rsi_short_description(rsi: float, contribution: int) -> str:
    if rsi < 30:
        return f"RSI({rsi:.1f})进入超卖区，可能出现反弹"
    if rsi > 70:
        return f"RSI({rsi:.1f})进入超买区，注意回调风险"
    if contribution == 1:
        return f"RSI({rsi:.1f})处于中性偏强区间，动能向上"
    return f"RSI({rsi:.1f})处于中性偏弱区间，动能不足"


def macd_description(macd: float, signal: float, contribution: int) -> str:
    if contribution == 1:
        return f"MACD({macd:.3f})上穿信号线({signal:.3f})，金叉，动能由跌转涨"
    return f"MACD({macd:.3f})下穿信号线({signal:.3f})，死叉，动能由涨转跌"


def volume_description(ratio: float, contribution: int) -> str:
    pct = (ratio - 1) * 100
    if contribution == 1:
        return f"成交量较20日均值放大{pct:.0f}%，信号更可信"
    return f"成交量较20日均值缩减{abs(pct):.0f}%，信号参考性有限"


def ema_long_description(vals: IndicatorValues, contribution: int) -> str:
    if vals.ema_50 is None or vals.ema_200 is None:
        return "长期EMA数据不足"
    if contribution == 1:
        return f"EMA50({vals.ema_50:.2f})在EMA200({vals.ema_200:.2f})上方，黄金交叉格局"
    return f"EMA50({vals.ema_50:.2f})在EMA200({vals.ema_200:.2f})下方，死亡交叉格局"


def price_vs_ema200_description(price: float, ema200: float, contribution: int) -> str:
    if contribution == 1:
        return f"当前价格({price:.2f})站上EMA200({ema200:.2f})，长期趋势向上"
    return f"当前价格({price:.2f})跌破EMA200({ema200:.2f})，长期趋势向下"


def rsi_weekly_description(rsi: float, contribution: int) -> str:
    if contribution == 1:
        return f"周线RSI({rsi:.1f})高于50，长期动能偏强"
    return f"周线RSI({rsi:.1f})低于50，长期动能偏弱"


def ema200_slope_description(slope: float, contribution: int) -> str:
    if contribution == 1:
        return f"EMA200斜率为正(+{slope:.2f})，长期趋势仍在走强"
    return f"EMA200斜率为负({slope:.2f})，长期趋势正在走弱"

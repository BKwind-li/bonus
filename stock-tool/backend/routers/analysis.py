from fastapi import APIRouter, Depends, HTTPException
from routers.auth import require_auth
from services.data_fetcher import fetch_ohlcv
from services.scanner_service import build_signal_result
from data.universe import get_ticker_info, is_forex
from config import settings

router = APIRouter()


@router.get("/{ticker}")
async def get_analysis(ticker: str, _=Depends(require_auth)):
    """Fetch fresh data for a single ticker and return signal + price history."""
    info = get_ticker_info(ticker)
    if info is None:
        raise HTTPException(status_code=404, detail="Ticker not found in universe")
    ohlcv = fetch_ohlcv(ticker)
    if ohlcv is None:
        raise HTTPException(status_code=503, detail="Failed to fetch market data")
    market = "forex" if is_forex(ticker) else "stock"
    result = build_signal_result(ticker, info["name"], info["sector"], market, ohlcv)

    prices = ohlcv.daily["Close"].tail(30).tolist()
    return {
        "signal": result.model_dump(mode="json"),
        "price_history": prices,
    }


@router.post("/{ticker}/deep")
async def deep_analysis(ticker: str, _=Depends(require_auth)):
    """Generate ~200-character Chinese analysis using Claude API.

    Returns 501 when CLAUDE_API_KEY is not configured.
    """
    if not settings.claude_api_key:
        raise HTTPException(status_code=501, detail="Claude API key not configured")

    info = get_ticker_info(ticker)
    if info is None:
        raise HTTPException(status_code=404, detail="Ticker not found")
    ohlcv = fetch_ohlcv(ticker)
    if ohlcv is None:
        raise HTTPException(status_code=503, detail="Failed to fetch market data")

    market = "forex" if is_forex(ticker) else "stock"
    result = build_signal_result(ticker, info["name"], info["sector"], market, ohlcv)

    short = result.short_term
    long_ = result.long_term
    short_lines = "\n".join([f"- {i.name}：{i.description}" for i in short.indicators])
    long_lines = "\n".join([f"- {i.name}：{i.description}" for i in long_.indicators])
    prompt = (
        f"你是一位专业的技术分析师，请用中文对以下品种给出约200字的分析摘要，"
        f"语言简洁易懂，面向没有专业背景的个人投资者。\n\n"
        f"品种：{info['name']}（{ticker}），板块：{info['sector']}\n"
        f"当前价格：{result.price}，涨跌：{result.change_pct:+.2f}%\n\n"
        f"短期信号（{short.label}，{short.score}/4分）：\n{short_lines}\n\n"
        f"长期信号（{long_.label}，{long_.score}/4分）：\n{long_lines}\n\n"
        f"请综合以上信息给出分析摘要，包含当前趋势判断和需要注意的风险。"
    )

    import anthropic
    client = anthropic.Anthropic(api_key=settings.claude_api_key)
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=400,
        messages=[{"role": "user", "content": prompt}],
    )
    return {"analysis": message.content[0].text}

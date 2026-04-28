import aiosmtplib
from email.mime.text import MIMEText
from datetime import datetime
from config import settings
from database import get_db


async def send_email(subject: str, body: str) -> None:
    """Send email via configured SMTP. Silently no-ops if SMTP not configured.

    Used for alert notifications. Does not raise on send failure (logged via print).
    """
    if not settings.smtp_user or not settings.notify_email:
        return
    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = settings.smtp_user
    msg["To"] = settings.notify_email
    try:
        await aiosmtplib.send(
            msg,
            hostname=settings.smtp_host,
            port=settings.smtp_port,
            username=settings.smtp_user,
            password=settings.smtp_pass,
            start_tls=True,
        )
    except Exception as e:
        print(f"[Notifier] Email send failed: {e}")


async def record_and_notify(ticker: str, alert_type: str, message: str) -> None:
    """Persist alert to history and send email."""
    async with get_db() as db:
        await db.execute(
            "INSERT INTO alert_history (ticker, alert_type, message) VALUES (?,?,?)",
            (ticker, alert_type, message),
        )
        await db.commit()
    await send_email(f"[投资助手] {ticker} 提醒", message)


async def check_price_alerts(ticker: str, current_price: float) -> None:
    """Check active price alerts for ticker; trigger notifications when crossed."""
    async with get_db() as db:
        cursor = await db.execute(
            "SELECT * FROM price_alerts WHERE ticker=? AND active=1", (ticker,)
        )
        alerts = await cursor.fetchall()

    for alert in alerts:
        triggered = (
            (alert["condition"] == "above" and current_price > alert["threshold"])
            or (alert["condition"] == "below" and current_price < alert["threshold"])
        )
        if triggered:
            verb = "突破" if alert["condition"] == "above" else "跌破"
            msg = f"{ticker} 当前价格 {current_price} 已{verb} {alert['threshold']}"
            await record_and_notify(ticker, "price", msg)


async def check_signal_alerts(
    ticker: str, new_short_score: int, new_long_score: int, rsi_daily: float
) -> None:
    """Check active signal alerts; detect change/strength/RSI-extreme conditions.

    Updates the previous_signals snapshot at the end so the next call has new baseline.
    """
    async with get_db() as db:
        cursor = await db.execute(
            "SELECT * FROM previous_signals WHERE ticker=?", (ticker,)
        )
        prev = await cursor.fetchone()
        cursor2 = await db.execute(
            "SELECT * FROM signal_alerts WHERE ticker=? AND active=1", (ticker,)
        )
        alerts = await cursor2.fetchall()

    for alert in alerts:
        cond = alert["condition"]
        triggered = False
        message = ""

        if cond == "any_change" and prev:
            # Trigger when either score changes by 2+ from previous snapshot
            if (
                abs(new_short_score - prev["short_score"]) >= 2
                or abs(new_long_score - prev["long_score"]) >= 2
            ):
                triggered = True
                message = (
                    f"{ticker} 信号发生跳变：短期评分 {prev['short_score']} → {new_short_score}, "
                    f"长期评分 {prev['long_score']} → {new_long_score}"
                )
        elif cond == "strong_only":
            # Trigger when current score is in strong range
            if abs(new_short_score) >= 3 or abs(new_long_score) >= 3:
                triggered = True
                message = (
                    f"{ticker} 出现强烈信号：短期 {new_short_score}/4，长期 {new_long_score}/4"
                )
        elif cond == "rsi_extreme":
            # Trigger when RSI is in oversold/overbought zone
            if rsi_daily < 30 or rsi_daily > 70:
                triggered = True
                direction = "超卖" if rsi_daily < 30 else "超买"
                message = f"{ticker} RSI({rsi_daily:.1f}) 进入{direction}区间"

        if triggered:
            await record_and_notify(ticker, "signal", message)

    # Always update the snapshot
    async with get_db() as db:
        await db.execute(
            """
            INSERT OR REPLACE INTO previous_signals
            (ticker, short_score, long_score, rsi_daily, updated_at)
            VALUES (?,?,?,?,?)
            """,
            (
                ticker,
                new_short_score,
                new_long_score,
                rsi_daily,
                datetime.utcnow().isoformat(),
            ),
        )
        await db.commit()

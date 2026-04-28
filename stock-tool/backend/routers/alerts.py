from fastapi import APIRouter, Depends
from routers.auth import require_auth
from database import get_db
from models import PriceAlertCreate, SignalAlertCreate

router = APIRouter()


@router.post("/price")
async def create_price_alert(alert: PriceAlertCreate, _=Depends(require_auth)):
    async with get_db() as db:
        cursor = await db.execute(
            "INSERT INTO price_alerts (ticker, condition, threshold) VALUES (?,?,?)",
            (alert.ticker, alert.condition, alert.threshold),
        )
        await db.commit()
        new_id = cursor.lastrowid
    return {"id": new_id}


@router.get("/price")
async def get_price_alerts(_=Depends(require_auth)):
    async with get_db() as db:
        cursor = await db.execute(
            "SELECT * FROM price_alerts ORDER BY created_at DESC"
        )
        rows = await cursor.fetchall()
    return [dict(r) for r in rows]


@router.delete("/price/{alert_id}")
async def delete_price_alert(alert_id: int, _=Depends(require_auth)):
    async with get_db() as db:
        await db.execute("DELETE FROM price_alerts WHERE id=?", (alert_id,))
        await db.commit()
    return {"status": "ok"}


@router.post("/signal")
async def create_signal_alert(alert: SignalAlertCreate, _=Depends(require_auth)):
    async with get_db() as db:
        cursor = await db.execute(
            "INSERT INTO signal_alerts (ticker, condition) VALUES (?,?)",
            (alert.ticker, alert.condition),
        )
        await db.commit()
        new_id = cursor.lastrowid
    return {"id": new_id}


@router.get("/signal")
async def get_signal_alerts(_=Depends(require_auth)):
    async with get_db() as db:
        cursor = await db.execute(
            "SELECT * FROM signal_alerts ORDER BY created_at DESC"
        )
        rows = await cursor.fetchall()
    return [dict(r) for r in rows]


@router.delete("/signal/{alert_id}")
async def delete_signal_alert(alert_id: int, _=Depends(require_auth)):
    async with get_db() as db:
        await db.execute("DELETE FROM signal_alerts WHERE id=?", (alert_id,))
        await db.commit()
    return {"status": "ok"}


@router.get("/history")
async def get_alert_history(limit: int = 30, _=Depends(require_auth)):
    async with get_db() as db:
        cursor = await db.execute(
            "SELECT * FROM alert_history ORDER BY triggered_at DESC LIMIT ?", (limit,)
        )
        rows = await cursor.fetchall()
    return [dict(r) for r in rows]


@router.post("/history/{alert_id}/read")
async def mark_as_read(alert_id: int, _=Depends(require_auth)):
    async with get_db() as db:
        await db.execute("UPDATE alert_history SET read=1 WHERE id=?", (alert_id,))
        await db.commit()
    return {"status": "ok"}


@router.get("/unread-count")
async def unread_count(_=Depends(require_auth)):
    async with get_db() as db:
        cursor = await db.execute(
            "SELECT COUNT(*) as cnt FROM alert_history WHERE read=0"
        )
        row = await cursor.fetchone()
    return {"count": row["cnt"]}

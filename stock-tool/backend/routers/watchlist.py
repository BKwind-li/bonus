from fastapi import APIRouter, Depends
from routers.auth import require_auth
from database import get_db
from models import WatchlistItem

router = APIRouter()


@router.get("")
async def get_watchlist(_=Depends(require_auth)):
    async with get_db() as db:
        cursor = await db.execute("SELECT * FROM watchlist ORDER BY added_at DESC")
        rows = await cursor.fetchall()
    return [dict(r) for r in rows]


@router.post("")
async def add_to_watchlist(item: WatchlistItem, _=Depends(require_auth)):
    async with get_db() as db:
        await db.execute(
            "INSERT OR IGNORE INTO watchlist (ticker, name, market, sector) VALUES (?,?,?,?)",
            (item.ticker, item.name, item.market, item.sector),
        )
        await db.commit()
    return {"status": "ok"}


@router.delete("/{ticker}")
async def remove_from_watchlist(ticker: str, _=Depends(require_auth)):
    async with get_db() as db:
        await db.execute("DELETE FROM watchlist WHERE ticker=?", (ticker,))
        await db.commit()
    return {"status": "ok"}

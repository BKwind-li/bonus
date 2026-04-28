import json
from fastapi import APIRouter, Depends, BackgroundTasks
from routers.auth import require_auth
from database import get_db
from services.scanner_service import run_full_scan

router = APIRouter()


@router.get("/results")
async def get_scan_results(
    market: str = "all",
    signal_type: str = "all",
    sort_by: str = "short",
    _=Depends(require_auth),
):
    """Query scan results with optional filters.

    market: "all" | "stock" | "forex"
    signal_type: "all" | "bullish" | "bearish"
    sort_by: "short" | "long" — sort by absolute value of that score
    """
    async with get_db() as db:
        cursor = await db.execute("SELECT * FROM scan_results")
        rows = await cursor.fetchall()

    results = [dict(r) for r in rows]

    # Parse JSON-encoded indicator columns
    for r in results:
        r["short_indicators"] = json.loads(r.get("short_indicators") or "[]")
        r["long_indicators"] = json.loads(r.get("long_indicators") or "[]")

    if market != "all":
        results = [r for r in results if r["market"] == market]

    if signal_type == "bullish":
        results = [r for r in results if r["short_score"] > 0 or r["long_score"] > 0]
    elif signal_type == "bearish":
        results = [r for r in results if r["short_score"] < 0 or r["long_score"] < 0]

    key = "short_score" if sort_by == "short" else "long_score"
    results.sort(key=lambda x: abs(x.get(key, 0)), reverse=True)

    return results


@router.post("/trigger")
async def trigger_scan(background_tasks: BackgroundTasks, _=Depends(require_auth)):
    """Trigger a full scan in the background. Returns immediately."""
    async def _run():
        async with get_db() as db:
            await run_full_scan(db)
    background_tasks.add_task(_run)
    return {"status": "scan started"}


@router.get("/last-scan-time")
async def last_scan_time(_=Depends(require_auth)):
    async with get_db() as db:
        cursor = await db.execute("SELECT MAX(scanned_at) as last_scan FROM scan_results")
        row = await cursor.fetchone()
    return {"last_scan": row["last_scan"] if row else None}

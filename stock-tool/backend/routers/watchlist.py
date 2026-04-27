from fastapi import APIRouter, Depends
from routers.auth import require_auth

router = APIRouter()


@router.get("")
async def get_watchlist(_=Depends(require_auth)):
    return []

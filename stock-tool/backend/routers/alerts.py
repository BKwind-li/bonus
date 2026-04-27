from fastapi import APIRouter, Depends
from routers.auth import require_auth

router = APIRouter()


@router.get("/history")
async def get_history(_=Depends(require_auth)):
    return []

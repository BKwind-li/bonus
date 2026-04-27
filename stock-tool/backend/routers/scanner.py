from fastapi import APIRouter, Depends
from routers.auth import require_auth

router = APIRouter()


@router.get("/results")
async def get_scan_results(_=Depends(require_auth)):
    return []

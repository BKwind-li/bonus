from fastapi import APIRouter, Depends
from routers.auth import require_auth

router = APIRouter()

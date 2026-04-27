from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from jose import jwt, JWTError
from datetime import datetime, timedelta, timezone
from config import settings

router = APIRouter()
bearer = HTTPBearer()


class LoginRequest(BaseModel):
    password: str


def create_token() -> str:
    payload = {"exp": datetime.now(timezone.utc) + timedelta(days=30)}
    return jwt.encode(payload, settings.secret_key, algorithm="HS256")


async def require_auth(credentials: HTTPAuthorizationCredentials = Depends(bearer)):
    try:
        jwt.decode(credentials.credentials, settings.secret_key, algorithms=["HS256"])
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    return True


@router.post("/login")
async def login(req: LoginRequest):
    if not settings.app_password or req.password != settings.app_password:
        raise HTTPException(status_code=401, detail="Invalid password")
    return {"access_token": create_token(), "token_type": "bearer"}

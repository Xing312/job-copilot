import os
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()

_PASSWORD = os.getenv("LOGIN_PASSWORD", "")
_SECRET = os.getenv("JWT_SECRET", _PASSWORD)  # fallback to password as secret
_ALGORITHM = "HS256"
_EXPIRE_DAYS = 30


class LoginRequest(BaseModel):
    password: str


@router.post("/auth/login")
def login(payload: LoginRequest):
    if not _PASSWORD:
        raise HTTPException(status_code=503, detail="Auth not configured")
    if payload.password != _PASSWORD:
        raise HTTPException(status_code=401, detail="Invalid password")
    exp = datetime.now(timezone.utc) + timedelta(days=_EXPIRE_DAYS)
    token = jwt.encode({"exp": exp}, _SECRET, algorithm=_ALGORITHM)
    return {"token": token}

import os
from collections import defaultdict
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

router = APIRouter()

_PASSWORD = os.getenv("LOGIN_PASSWORD", "")
_SECRET = os.getenv("JWT_SECRET", _PASSWORD)
_ALGORITHM = "HS256"
_EXPIRE_DAYS = 30

# Rate limiting: max 10 failed attempts per IP within 5 minutes
_MAX_FAILURES = 10
_WINDOW = timedelta(minutes=5)
_failures: dict[str, list[datetime]] = defaultdict(list)


def _check_rate_limit(ip: str):
    now = datetime.now(timezone.utc)
    cutoff = now - _WINDOW
    _failures[ip] = [t for t in _failures[ip] if t > cutoff]
    if len(_failures[ip]) >= _MAX_FAILURES:
        raise HTTPException(status_code=429, detail="Too many attempts. Try again in 5 minutes.")


def _record_failure(ip: str):
    _failures[ip].append(datetime.now(timezone.utc))


class LoginRequest(BaseModel):
    password: str


@router.post("/auth/login")
def login(payload: LoginRequest, request: Request):
    if not _PASSWORD:
        raise HTTPException(status_code=503, detail="Auth not configured")

    ip = request.client.host if request.client else "unknown"
    _check_rate_limit(ip)

    if payload.password != _PASSWORD:
        _record_failure(ip)
        raise HTTPException(status_code=401, detail="Invalid password")

    # Success — clear failure history for this IP
    _failures.pop(ip, None)

    exp = datetime.now(timezone.utc) + timedelta(days=_EXPIRE_DAYS)
    token = jwt.encode({"exp": exp}, _SECRET, algorithm=_ALGORITHM)
    return {"token": token}

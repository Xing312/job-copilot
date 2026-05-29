import os
import sys
from pathlib import Path

# Ensure backend/ is on sys.path so sub-packages resolve regardless of cwd
sys.path.insert(0, str(Path(__file__).parent))

import jwt
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from db.database import engine, Base
import models.application  # registers the model with Base
from api import applications, extract, stats, auth

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Job Copilot API")

_origins = ["http://localhost:5173"]
if _frontend_url := os.getenv("FRONTEND_URL"):
    _origins.append(_frontend_url.rstrip("/"))

app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

_LOGIN_PASSWORD = os.getenv("LOGIN_PASSWORD", "")
_JWT_SECRET = os.getenv("JWT_SECRET", _LOGIN_PASSWORD)

_PUBLIC_PATHS = {"/api/auth/login"}


@app.middleware("http")
async def require_auth(request: Request, call_next):
    if request.method == "OPTIONS":
        return await call_next(request)
    if request.url.path in _PUBLIC_PATHS:
        return await call_next(request)
    if _LOGIN_PASSWORD:
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return JSONResponse({"detail": "Unauthorized"}, status_code=401)
        try:
            jwt.decode(auth_header[7:], _JWT_SECRET, algorithms=["HS256"])
        except jwt.InvalidTokenError:
            return JSONResponse({"detail": "Invalid or expired token"}, status_code=401)
    return await call_next(request)


app.include_router(auth.router, prefix="/api")
app.include_router(applications.router, prefix="/api")
app.include_router(extract.router, prefix="/api")
app.include_router(stats.router, prefix="/api")

import os
import sys
from pathlib import Path

# Ensure backend/ is on sys.path so sub-packages resolve regardless of cwd
sys.path.insert(0, str(Path(__file__).parent))

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from db.database import engine, Base
import models.application  # registers the model with Base
from api import applications, extract, stats

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

_API_KEY = os.getenv("API_KEY", "")


@app.middleware("http")
async def require_api_key(request: Request, call_next):
    # CORS preflight requests must pass through before auth check
    if request.method == "OPTIONS":
        return await call_next(request)
    if _API_KEY and request.headers.get("X-API-Key") != _API_KEY:
        return JSONResponse({"detail": "Unauthorized"}, status_code=401)
    return await call_next(request)

app.include_router(applications.router, prefix="/api")
app.include_router(extract.router, prefix="/api")
app.include_router(stats.router, prefix="/api")

import os
import sys
from pathlib import Path

# Ensure backend/ is on sys.path so sub-packages resolve regardless of cwd
sys.path.insert(0, str(Path(__file__).parent))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import models.application  # noqa: F401 — registers model with Base
from api import applications, extract, stats

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

app.include_router(applications.router, prefix="/api")
app.include_router(extract.router, prefix="/api")
app.include_router(stats.router, prefix="/api")

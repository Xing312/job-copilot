import os
import sys

# Must set before any project imports so db.database picks up SQLite
os.environ["DATABASE_URL"] = "sqlite+pysqlite:///:memory:"
os.environ["LOGIN_PASSWORD"] = ""

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

# Replace the engine in db.database with a StaticPool SQLite engine BEFORE main.py is
# imported, so Base.metadata.create_all and all sessions share the same in-memory database.
import db.database as _db

_engine = create_engine(
    "sqlite+pysqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
_SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_engine)
_db.engine = _engine
_db.SessionLocal = _SessionLocal

import main  # noqa: E402 — must come after patching

from db.database import Base, get_db  # noqa: E402
import models.application  # noqa: F401,E402 — registers Application with Base

Base.metadata.create_all(bind=_engine)

TEST_PASSWORD = "testpassword"
TEST_SECRET = "test-jwt-secret"


def _override_get_db():
    db = _SessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(autouse=True)
def _clean_tables():
    yield
    with _engine.connect() as conn:
        conn.execute(models.application.Application.__table__.delete())
        conn.commit()


@pytest.fixture
def client():
    main.app.dependency_overrides[get_db] = _override_get_db
    with TestClient(main.app, raise_server_exceptions=True) as c:
        yield c
    main.app.dependency_overrides.clear()


@pytest.fixture
def auth_client(monkeypatch):
    import api.auth as _auth
    monkeypatch.setattr(main, "_LOGIN_PASSWORD", TEST_PASSWORD)
    monkeypatch.setattr(main, "_JWT_SECRET", TEST_SECRET)
    monkeypatch.setattr(_auth, "_PASSWORD", TEST_PASSWORD)
    monkeypatch.setattr(_auth, "_SECRET", TEST_SECRET)
    _auth._failures.clear()

    main.app.dependency_overrides[get_db] = _override_get_db
    with TestClient(main.app, raise_server_exceptions=True) as c:
        yield c
    main.app.dependency_overrides.clear()


@pytest.fixture
def token():
    import jwt as _jwt
    from datetime import datetime, timedelta, timezone
    exp = datetime.now(timezone.utc) + timedelta(days=1)
    return _jwt.encode({"exp": exp}, TEST_SECRET, algorithm="HS256")

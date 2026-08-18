# backend/tests/test_routers_status.py
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base
import app.db as db_module
from app.main import app
from app.models import EntryScoreHistory


def _seeded_db(monkeypatch):
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(bind=engine)
    monkeypatch.setattr(db_module, "SessionLocal", TestingSessionLocal)
    return TestingSessionLocal


def test_get_status_returns_null_when_no_cycle_has_ever_run(monkeypatch):
    _seeded_db(monkeypatch)
    client = TestClient(app)

    response = client.get("/status")

    assert response.status_code == 200
    assert response.json() == {"last_updated": None}


def test_get_status_returns_the_most_recent_cycle_across_all_coins(monkeypatch):
    SessionLocal = _seeded_db(monkeypatch)
    session = SessionLocal()
    base = datetime.now(timezone.utc)
    session.add(EntryScoreHistory(coin_symbol="BTCUSDT", score=10.0, computed_at=base - timedelta(hours=1)))
    session.add(EntryScoreHistory(coin_symbol="ETHUSDT", score=20.0, computed_at=base))
    session.commit()
    session.close()
    client = TestClient(app)

    response = client.get("/status")

    assert response.status_code == 200
    last_updated = response.json()["last_updated"]
    assert last_updated.endswith("Z") or last_updated.endswith("+00:00")
    assert datetime.fromisoformat(last_updated) == base

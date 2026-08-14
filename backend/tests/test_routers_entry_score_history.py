# backend/tests/test_routers_entry_score_history.py
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


def test_get_entry_score_history_returns_oldest_first(monkeypatch):
    SessionLocal = _seeded_db(monkeypatch)
    session = SessionLocal()
    base = datetime.now(timezone.utc)
    session.add(EntryScoreHistory(coin_symbol="BTCUSDT", score=10.0, computed_at=base - timedelta(hours=2)))
    session.add(EntryScoreHistory(coin_symbol="BTCUSDT", score=20.0, computed_at=base - timedelta(hours=1)))
    session.add(EntryScoreHistory(coin_symbol="BTCUSDT", score=30.0, computed_at=base))
    session.add(EntryScoreHistory(coin_symbol="ETHUSDT", score=99.0, computed_at=base))
    session.commit()
    session.close()
    client = TestClient(app)

    response = client.get("/coins/BTCUSDT/entry-score-history")

    assert response.status_code == 200
    body = response.json()
    assert [row["score"] for row in body] == [10.0, 20.0, 30.0]  # oldest first


def test_get_entry_score_history_respects_limit(monkeypatch):
    SessionLocal = _seeded_db(monkeypatch)
    session = SessionLocal()
    base = datetime.now(timezone.utc)
    for i in range(5):
        session.add(EntryScoreHistory(
            coin_symbol="BTCUSDT", score=float(i), computed_at=base - timedelta(hours=5 - i),
        ))
    session.commit()
    session.close()
    client = TestClient(app)

    response = client.get("/coins/BTCUSDT/entry-score-history", params={"limit": 2})

    assert response.status_code == 200
    body = response.json()
    # The 2 most recent, still oldest-first: scores 3.0 and 4.0
    assert [row["score"] for row in body] == [3.0, 4.0]


def test_get_entry_score_history_timestamps_carry_a_utc_offset(monkeypatch):
    SessionLocal = _seeded_db(monkeypatch)
    session = SessionLocal()
    session.add(EntryScoreHistory(coin_symbol="BTCUSDT", score=42.0))
    session.commit()
    session.close()
    client = TestClient(app)

    response = client.get("/coins/BTCUSDT/entry-score-history")

    computed_at = response.json()[0]["computed_at"]
    assert computed_at.endswith("Z") or computed_at.endswith("+00:00")


def test_get_entry_score_history_empty_for_unknown_symbol(monkeypatch):
    _seeded_db(monkeypatch)
    client = TestClient(app)

    response = client.get("/coins/DOESNOTEXIST/entry-score-history")

    assert response.status_code == 200
    assert response.json() == []

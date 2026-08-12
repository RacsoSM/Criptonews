# backend/tests/test_routers_coins_signals.py
from datetime import datetime, timezone

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base
import app.db as db_module
from app.main import app
from app.models import Coin, Position, Signal


def _seeded_db(monkeypatch):
    # StaticPool + check_same_thread=False: TestClient dispatches requests to
    # a worker thread, and a plain sqlite:///:memory: engine hands out a
    # separate (empty) in-memory database per thread. StaticPool forces every
    # connection to share the same underlying sqlite connection so the
    # endpoint's session sees the tables and data created below.
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(bind=engine)
    monkeypatch.setattr(db_module, "SessionLocal", TestingSessionLocal)

    session = TestingSessionLocal()
    session.add(Coin(symbol="BTCUSDT", name="Bitcoin", rank=1, active=True))
    session.add(Coin(symbol="ETHUSDT", name="Ethereum", rank=2, active=True))
    position = Position(
        coin_symbol="BTCUSDT",
        entry_price=60000.0,
        entry_time=datetime.now(timezone.utc),
        stop_loss=57000.0,
        take_profit=66000.0,
        status="OPEN",
    )
    session.add(position)
    session.flush()
    session.add(Signal(
        coin_symbol="BTCUSDT",
        signal_type="BUY",
        price=60000.0,
        rsi_vote="buy",
        ema_cross_vote="buy",
        macd_vote="buy",
        donchian_vote=None,
        created_at=datetime.now(timezone.utc),
        position_id=position.id,
    ))
    session.commit()
    session.close()
    return TestingSessionLocal


def test_get_coins_marks_open_position(monkeypatch):
    _seeded_db(monkeypatch)
    client = TestClient(app)

    response = client.get("/coins")

    assert response.status_code == 200
    body = response.json()
    btc = next(c for c in body if c["symbol"] == "BTCUSDT")
    eth = next(c for c in body if c["symbol"] == "ETHUSDT")
    assert btc["has_open_position"] is True
    assert btc["entry_price"] == 60000.0
    assert eth["has_open_position"] is False


def test_get_coins_ignores_closed_position(monkeypatch):
    SessionLocal = _seeded_db(monkeypatch)
    session = SessionLocal()
    session.add(Position(
        coin_symbol="ETHUSDT",
        entry_price=3000.0,
        entry_time=datetime.now(timezone.utc),
        stop_loss=2800.0,
        take_profit=3300.0,
        status="CLOSED",
        closed_price=3100.0,
        closed_time=datetime.now(timezone.utc),
    ))
    session.commit()
    session.close()
    client = TestClient(app)

    response = client.get("/coins")

    assert response.status_code == 200
    body = response.json()
    eth = next(c for c in body if c["symbol"] == "ETHUSDT")
    assert eth["has_open_position"] is False
    assert eth["entry_price"] is None


def test_get_signals_returns_history_newest_first(monkeypatch):
    _seeded_db(monkeypatch)
    client = TestClient(app)

    response = client.get("/signals")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["coin_symbol"] == "BTCUSDT"
    assert body[0]["signal_type"] == "BUY"


def test_get_signals_filters_by_coin_symbol(monkeypatch):
    _seeded_db(monkeypatch)
    client = TestClient(app)

    response = client.get("/signals", params={"coin_symbol": "ETHUSDT"})

    assert response.status_code == 200
    assert response.json() == []


def test_get_signals_orders_multiple_newest_first(monkeypatch):
    SessionLocal = _seeded_db(monkeypatch)
    session = SessionLocal()
    session.add(Signal(
        coin_symbol="BTCUSDT",
        signal_type="SELL",
        price=61000.0,
        rsi_vote="sell",
        ema_cross_vote="sell",
        macd_vote="sell",
        donchian_vote=None,
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    ))
    session.add(Signal(
        coin_symbol="BTCUSDT",
        signal_type="BUY",
        price=62000.0,
        rsi_vote="buy",
        ema_cross_vote="buy",
        macd_vote="buy",
        donchian_vote=None,
        created_at=datetime(2026, 6, 1, tzinfo=timezone.utc),
    ))
    session.commit()
    session.close()
    client = TestClient(app)

    response = client.get("/signals")

    assert response.status_code == 200
    body = response.json()
    created_ats = [s["created_at"] for s in body]
    assert created_ats == sorted(created_ats, reverse=True)

# backend/tests/test_routers_devices.py
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base
import app.db as db_module
from app.main import app
from app.models import DeviceToken


def _use_in_memory_db(monkeypatch):
    # StaticPool + check_same_thread=False: TestClient dispatches requests to
    # a worker thread, and a plain sqlite:///:memory: engine hands out a
    # separate (empty) in-memory database per thread. StaticPool forces every
    # connection to share the same underlying sqlite connection so the
    # endpoint's session sees the tables created below.
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(bind=engine)
    monkeypatch.setattr(db_module, "SessionLocal", TestingSessionLocal)
    return TestingSessionLocal


def test_register_device_token_creates_row(monkeypatch):
    SessionLocal = _use_in_memory_db(monkeypatch)
    client = TestClient(app)

    response = client.post("/devices", json={"token": "device-abc"})

    assert response.status_code == 201
    session = SessionLocal()
    assert session.query(DeviceToken).filter_by(token="device-abc").count() == 1
    session.close()


def test_register_device_token_is_idempotent(monkeypatch):
    SessionLocal = _use_in_memory_db(monkeypatch)
    client = TestClient(app)

    client.post("/devices", json={"token": "device-abc"})
    response = client.post("/devices", json={"token": "device-abc"})

    assert response.status_code == 201
    session = SessionLocal()
    assert session.query(DeviceToken).filter_by(token="device-abc").count() == 1
    session.close()

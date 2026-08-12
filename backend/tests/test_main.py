# backend/tests/test_main.py
from fastapi.testclient import TestClient

from app.main import app


def test_app_starts_and_root_health_check():
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

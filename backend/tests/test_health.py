"""Health endpoint sanity test. Does not require LLM keys."""
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)


def test_health_returns_ok():
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["service"] == "tulparai-backend"
    assert "models" in body and "reasoner" in body["models"]


def test_root_returns_service_info():
    r = client.get("/")
    assert r.status_code == 200
    assert r.json()["service"] == "tulparai"

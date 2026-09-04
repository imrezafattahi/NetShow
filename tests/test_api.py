from fastapi.testclient import TestClient

from app.main import app


def test_health():
    with TestClient(app) as client:
        body = client.get("/api/health").json()
    assert body["status"] == "ok"
    assert body["targets"] >= 1


def test_status_shape():
    with TestClient(app) as client:
        response = client.get("/api/status")
    assert response.status_code == 200
    body = response.json()
    assert {"generated_at", "interval_seconds", "system", "targets", "events"} <= body.keys()
    assert isinstance(body["targets"], list) and body["targets"]
    first = body["targets"][0]
    assert {"name", "kind", "host", "up", "history", "uptime_24h"} <= first.keys()
    assert {"cpu", "ram", "disk"} <= body["system"].keys()


def test_history_rejects_unknown_target():
    with TestClient(app) as client:
        assert client.get("/api/history", params={"target": "nope"}).status_code == 404


def test_events_endpoint():
    with TestClient(app) as client:
        body = client.get("/api/events", params={"limit": 5}).json()
    assert isinstance(body["events"], list)


def test_dashboard_is_served():
    with TestClient(app) as client:
        response = client.get("/")
    assert response.status_code == 200
    assert "NetShow" in response.text

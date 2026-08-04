from fastapi.testclient import TestClient

from app.main import create_app
from tests.fakes.container import build_test_container


def test_health_returns_trace_id() -> None:
    container, _, _ = build_test_container()
    with TestClient(create_app(container)) as client:
        response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["trace_id"].startswith("tr_")
    assert response.headers["X-Trace-ID"] == response.json()["trace_id"]

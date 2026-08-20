from fastapi.testclient import TestClient

from text_back.app import create_app


def test_health_reports_ok_and_not_production():
    client = TestClient(create_app())
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["production"] is False
    assert body["telecom"] == "stub"

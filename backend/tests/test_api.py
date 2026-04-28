from fastapi.testclient import TestClient

from app.main import create_app


def test_health_endpoint() -> None:
    client = TestClient(create_app())
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_generate_allocation_validates_password() -> None:
    client = TestClient(create_app())
    response = client.post("/api/generate-allocation", data={"glf_password": ""})
    assert response.status_code in {400, 422}

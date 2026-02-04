from fastapi.testclient import TestClient
from services.customer_lookup.main import app

client = TestClient(app)

def test_validate_valid_client_success():
    response = client.get("/exists/000_000_001")
    assert response.status_code == 200
    assert response.json() == "000_000_001"

    response = client.get("/exists/000_000_002")
    assert response.status_code == 200
    assert response.json() == "000_000_002"

    response = client.get("/exists/000_000_003")
    assert response.status_code == 200
    assert response.json() == "000_000_003"

def test_validate_invalid_client_fail():
    response = client.get("/exists/000_000_000")
    assert response.status_code == 404
    data = response.json()
    assert "detail" in data
    assert "not found" in data["detail"].lower()

def test_validate_partial_client_fail():
    response = client.get("/exists/001")
    assert response.status_code == 404
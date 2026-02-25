import pytest
import requests
from fastapi.testclient import TestClient
from backend.api import app, AUTH_TOKEN

@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c

def test_security_radius_overload(client):
    # Attempting to request a massive radius should be blocked by Pydantic validation (422)
    headers = {"X-SisRua-Token": AUTH_TOKEN}
    response = client.post(
        "/api/v1/prepare/osm",
        json={"latitude": -23.55, "longitude": -46.63, "radius": 100000}, # 100km!
        headers=headers
    )
    assert response.status_code == 422 # Pydantic le=5000.0

def test_security_malformed_coordinates(client):
    # Invalid coordinates (lat=1000) should be blocked by Pydantic validation (422)
    headers = {"X-SisRua-Token": AUTH_TOKEN}
    response = client.post(
        "/api/v1/prepare/osm",
        json={"latitude": 1000, "longitude": -46.63, "radius": 100},
        headers=headers
    )
    assert response.status_code == 422

def test_security_unauthenticated_private_path(client):
    # Health is public, but prepare is private. Missing token should return 401.
    response = client.post("/api/v1/prepare/osm", json={})
    assert response.status_code == 401

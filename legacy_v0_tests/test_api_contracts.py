"""
API Contract Tests for v0.8.0

Ensures API stability by validating:
- Request/response schema compliance
- HTTP status codes
- Error response formats
- Authentication requirements
"""
import pytest
from fastapi.testclient import TestClient

# Test configuration
TEST_TOKEN = "test-token-123"

@pytest.fixture
def client():
    """Create test client with authentication."""
    import os
    os.environ["SISRUA_AUTH_TOKEN"] = TEST_TOKEN
    
    # Import after setting env var
    from backend.api import app
    return TestClient(app)

@pytest.fixture
def headers():
    """Standard auth headers."""
    return {"X-SisRua-Token": TEST_TOKEN}


# ========== Health & Auth Endpoints ==========

def test_health_contract(client):
    """GET /api/v1/health - No auth, returns status."""
    response = client.get("/api/v1/health")
    
    assert response.status_code == 200
    data = response.json()
    
    # Contract validation
    assert "status" in data
    assert data["status"] == "ok"
    assert isinstance(data["status"], str)


def test_auth_check_contract_valid(client, headers):
    """GET /api/v1/auth/check - Valid token returns ok."""
    response = client.get("/api/v1/auth/check", headers=headers)
    
    assert response.status_code == 200
    data = response.json()
    
    assert "status" in data
    assert data["status"] == "ok"


def test_auth_check_contract_invalid(client):
    """GET /api/v1/auth/check - Invalid token returns 401."""
    response = client.get("/api/v1/auth/check")
    
    assert response.status_code == 401
    data = response.json()
    
    # Error contract
    assert "detail" in data
    assert isinstance(data["detail"], str)


def test_health_detailed_contract(client, headers):
    """GET /api/v1/health/detailed - Returns detailed health info."""
    response = client.get("/api/v1/health/detailed", headers=headers)
    
    assert response.status_code == 200
    data = response.json()
    
    # Contract validation
    assert "status" in data
    assert "timestamp" in data
    assert "services" in data
    assert isinstance(data["services"], dict)


# ========== Jobs Endpoints ==========

def test_create_job_contract(client, headers):
    """POST /api/v1/jobs/prepare - Returns job status."""
    payload = {
        "kind": "osm",
        "latitude": -21.7634,
        "longitude": -41.3235,
        "radius": 500
    }
    
    response = client.post("/api/v1/jobs/prepare", json=payload, headers=headers)
    
    assert response.status_code == 200
    data = response.json()
    
    # Job contract
    assert "job_id" in data
    assert "status" in data
    assert "progress" in data
    assert "message" in data
    
    # Type validation
    assert isinstance(data["job_id"], str)
    assert data["status"] in ["pending", "running", "completed", "failed", "cancelled"]
    assert isinstance(data["progress"], (int, float))
    assert 0.0 <= data["progress"] <= 1.0
    assert isinstance(data["message"], str)


def test_get_job_contract(client, headers):
    """GET /api/v1/jobs/{job_id} - Returns job status."""
    # First create a job
    payload = {
        "kind": "osm",
        "latitude": -21.7634,
        "longitude": -41.3235,
        "radius": 500
    }
    create_response = client.post("/api/v1/jobs/prepare", json=payload, headers=headers)
    job_id = create_response.json()["job_id"]
    
    # Now get the job
    response = client.get(f"/api/v1/jobs/{job_id}", headers=headers)
    
    assert response.status_code == 200
    data = response.json()
    
    # Same contract as create
    assert "job_id" in data
    assert "status" in data
    assert "progress" in data
    assert "message" in data


def test_get_job_not_found_contract(client, headers):
    """GET /api/v1/jobs/{job_id} - Returns 404 for missing job."""
    response = client.get("/api/v1/jobs/nonexistent", headers=headers)
    
    assert response.status_code == 404
    data = response.json()
    
    # Error contract
    assert "detail" in data


def test_cancel_job_contract(client, headers):
    """DELETE /api/v1/jobs/{job_id} - Returns ok."""
    # Create a job first
    payload = {
        "kind": "osm",
        "latitude": -21.7634,
        "longitude": -41.3235,
        "radius": 500
    }
    create_response = client.post("/api/v1/jobs/prepare", json=payload, headers=headers)
    job_id = create_response.json()["job_id"]
    
    # Cancel it
    response = client.delete(f"/api/v1/jobs/{job_id}", headers=headers)
    
    assert response.status_code == 200
    data = response.json()
    
    assert "status" in data
    assert data["status"] == "ok"


# ========== Elevation Tools ==========

def test_elevation_query_contract(client, headers):
    """POST /api/v1/tools/elevation/query - Returns elevation point."""
    payload = {
        "latitude": -21.7634,
        "longitude": -41.3235
    }
    
    response = client.post("/api/v1/tools/elevation/query", json=payload, headers=headers)
    
    # May fail if SRTM data not available, but contract should be consistent
    if response.status_code == 200:
        data = response.json()
        
        assert "latitude" in data
        assert "longitude" in data
        assert "elevation" in data
        
        assert data["latitude"] == payload["latitude"]
        assert data["longitude"] == payload["longitude"]
        assert isinstance(data["elevation"], (int, float))


def test_elevation_profile_contract(client, headers):
    """POST /api/v1/tools/elevation/profile - Returns elevation array."""
    payload = {
        "path": [
            [-21.7634, -41.3235],
            [-21.7640, -41.3240]
        ]
    }
    
    response = client.post("/api/v1/tools/elevation/profile", json=payload, headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        
        assert "elevations" in data
        assert isinstance(data["elevations"], list)
        assert len(data["elevations"]) == len(payload["path"])


# ========== AI Endpoint ==========

def test_ai_chat_contract(client, headers):
    """POST /api/v1/ai/chat - Returns chat response."""
    payload = {
        "message": "Hello",
        "context": {},
        "job_id": None
    }
    
    response = client.post("/api/v1/ai/chat", json=payload, headers=headers)
    
    # Should always return 200 (graceful degradation)
    assert response.status_code == 200
    data = response.json()
    
    assert "response" in data
    assert isinstance(data["response"], str)


# ========== Webhooks ==========

def test_webhook_register_contract(client, headers):
    """POST /api/v1/webhooks/register - Returns ok."""
    payload = {
        "url": "http://localhost:8080/webhook"
    }
    
    response = client.post("/api/v1/webhooks/register", json=payload, headers=headers)
    
    assert response.status_code == 200
    data = response.json()
    
    assert "status" in data
    assert data["status"] == "ok"


def test_event_emit_contract(client, headers):
    """POST /api/v1/events/emit - Returns ok."""
    payload = {
        "event_type": "project_saved",
        "payload": {"project_id": "test123"}
    }
    
    response = client.post("/api/v1/events/emit", json=payload, headers=headers)
    
    assert response.status_code == 200
    data = response.json()
    
    assert "status" in data
    assert data["status"] == "ok"


# ========== Projects ==========

def test_update_project_not_found_contract(client, headers):
    """PUT /api/v1/projects/{project_id} - Returns 404 for missing project."""
    payload = {
        "version": 1,
        "name": "New Name"
    }
    
    response = client.put("/api/v1/projects/nonexistent", json=payload, headers=headers)
    
    assert response.status_code == 404
    data = response.json()
    
    assert "detail" in data


# ========== Error Response Contracts ==========

def test_error_response_format_unauthorized(client):
    """All 401 errors return consistent format."""
    response = client.get("/api/v1/auth/check")
    
    assert response.status_code == 401
    data = response.json()
    
    # Standard error contract
    assert "detail" in data
    assert isinstance(data["detail"], str)


def test_error_response_format_not_found(client, headers):
    """All 404 errors return consistent format."""
    response = client.get("/api/v1/jobs/nonexistent", headers=headers)
    
    assert response.status_code == 404
    data = response.json()
    
    assert "detail" in data
    assert isinstance(data["detail"], str)


# ========== Authentication Contract ==========

def test_auth_header_requirement(client):
    """Protected endpoints require X-SisRua-Token header."""
    endpoints = [
        ("GET", "/api/v1/auth/check"),
        ("GET", "/api/v1/health/detailed"),
        ("POST", "/api/v1/jobs/prepare", {"kind": "osm", "latitude": 0, "longitude": 0, "radius": 100}),
    ]
    
    for method, url, *body in endpoints:
        if method == "GET":
            response = client.get(url)
        elif method == "POST":
            response = client.post(url, json=body[0] if body else {})
        
        # Should fail auth
        assert response.status_code == 401
        data = response.json()
        assert "detail" in data


# ========== Idempotency Contract ==========

def test_job_creation_idempotency(client, headers):
    """Same job payload returns same job_id."""
    payload = {
        "kind": "osm",
        "latitude": -21.7634,
        "longitude": -41.3235,
        "radius": 500
    }
    
    # Create job twice
    response1 = client.post("/api/v1/jobs/prepare", json=payload, headers=headers)
    response2 = client.post("/api/v1/jobs/prepare", json=payload, headers=headers)
    
    assert response1.status_code == 200
    assert response2.status_code == 200
    
    job_id1 = response1.json()["job_id"]
    job_id2 = response2.json()["job_id"]
    
    # Idempotency: same payload = same job_id
    assert job_id1 == job_id2


# ========== Backward Compatibility ==========

def test_backward_compatibility_v070_health(client):
    """v0.7.0 client can still call health endpoint."""
    # v0.7.0 health check
    response = client.get("/api/v1/health")
    
    assert response.status_code == 200
    data = response.json()
    
    # v0.7.0 expected this exact format
    assert data == {"status": "ok"}


def test_backward_compatibility_v070_job_create(client, headers):
    """v0.7.0 client can still create jobs."""
    # v0.7.0 job creation payload
    payload = {
        "kind": "osm",
        "latitude": -21.7634,
        "longitude": -41.3235,
        "radius": 500
    }
    
    response = client.post("/api/v1/jobs/prepare", json=payload, headers=headers)
    
    assert response.status_code == 200
    data = response.json()
    
    # v0.7.0 expected these exact fields
    assert "job_id" in data
    assert "status" in data
    assert "progress" in data
    assert "message" in data


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

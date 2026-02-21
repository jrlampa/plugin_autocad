import pytest
import time
import math
from unittest.mock import MagicMock
from fastapi import HTTPException
from pydantic import ValidationError
from backend.core.rate_limit import TokenBucket, RateLimiter
from backend.core.utils import (
    cache_key, norm_optional_str, sanitize_jsonable, 
    get_color_from_elevation, estimate_width_m, get_layer_name
)
from backend.core.circuit_breaker import CircuitBreaker, CircuitState, CircuitBreakerOpenException
from backend.models import (
    PrepareOsmRequest, ElevationQueryRequest, ElevationProfileRequest,
    PrepareJobRequest,
)

# --- Rate Limit Tests ---
def test_token_bucket():
    bucket = TokenBucket(capacity=2, refill_rate=1.0)
    assert bucket.consume(1) is True
    assert bucket.consume(1) is True
    assert bucket.consume(1) is False
    
    # Wait for refill
    time.sleep(1.1)
    assert bucket.consume(1) is True

import asyncio

def test_rate_limiter():
    limiter = RateLimiter(calls=2, period=1)
    request = MagicMock()
    request.client.host = "127.0.0.1"
    
    async def run_test():
        await limiter(request)
        await limiter(request)
        with pytest.raises(HTTPException) as excinfo:
            await limiter(request)
        assert excinfo.value.status_code == 429
        
    asyncio.run(run_test())

# --- Utils Tests ---
def test_cache_key():
    key1 = cache_key(["a", "b"])
    key2 = cache_key(["a", "b"])
    key3 = cache_key(["a", "c"])
    assert key1 == key2
    assert key1 != key3
    assert len(key1) == 64

def test_norm_optional_str():
    assert norm_optional_str("  hello  ") == "hello"
    assert norm_optional_str(None) is None
    assert norm_optional_str(float('nan')) is None
    assert norm_optional_str("NaN") is None
    assert norm_optional_str("") is None

def test_sanitize_jsonable():
    data = {
        "a": 1,
        "b": float('nan'),
        "c": [1, 2, float('inf')],
        "d": {"nested": float('-inf')}
    }
    sanitized = sanitize_jsonable(data)
    assert sanitized["b"] is None
    assert sanitized["c"][2] is None
    assert sanitized["d"]["nested"] is None
    assert sanitized["a"] == 1

def test_get_color_from_elevation():
    assert get_color_from_elevation(10, 0, 100) == "5" # Blue (ratio 0.1)
    assert get_color_from_elevation(95, 0, 100) == "1" # Red (ratio 0.95)
    assert get_color_from_elevation(50, 0, 100) == "3" # Green (ratio 0.5)
    assert get_color_from_elevation(10, 10, 10) == "255,255,255"

def test_estimate_width_m():
    assert estimate_width_m(None, "residential") == 5.0
    assert estimate_width_m(None, "motorway") == 20.0
    assert estimate_width_m(None, "unknown") == 6.0
    assert estimate_width_m(None, None) is None

# --- Layer Mapping Tests ---
def test_get_layer_name_highway():
    assert get_layer_name({"highway": "residential"}) == "SISRUA_Vias_Locais"
    assert get_layer_name({"highway": "primary"}) == "SISRUA_Vias_Arteriais"
    assert get_layer_name({"highway": "motorway"}) == "SISRUA_Vias_Expressas"

def test_get_layer_name_unknown_returns_default():
    assert get_layer_name({"amenity": "bench"}) == "SISRUA_DEFAULT"
    assert get_layer_name({}) == "SISRUA_DEFAULT"

def test_get_layer_name_custom_default():
    result = get_layer_name({"unknown": "tag"}, default="MY_LAYER")
    assert result == "MY_LAYER"

# --- Coordinate Validation Tests ---
def test_prepare_osm_request_valid():
    req = PrepareOsmRequest(latitude=-22.15018, longitude=-42.92185, radius=500.0)
    assert req.latitude == -22.15018
    assert req.longitude == -42.92185
    assert req.radius == 500.0

def test_prepare_osm_request_invalid_latitude():
    with pytest.raises(ValidationError):
        PrepareOsmRequest(latitude=91.0, longitude=-42.92185, radius=500.0)

def test_prepare_osm_request_invalid_longitude():
    with pytest.raises(ValidationError):
        PrepareOsmRequest(latitude=-22.15018, longitude=181.0, radius=500.0)

def test_prepare_osm_request_invalid_radius_zero():
    with pytest.raises(ValidationError):
        PrepareOsmRequest(latitude=-22.15018, longitude=-42.92185, radius=0.0)

def test_prepare_osm_request_invalid_radius_too_large():
    with pytest.raises(ValidationError):
        PrepareOsmRequest(latitude=-22.15018, longitude=-42.92185, radius=50001.0)

def test_elevation_query_request_valid():
    req = ElevationQueryRequest(latitude=-22.15018, longitude=-42.92185)
    assert req.latitude == -22.15018

def test_elevation_query_request_invalid_lat():
    with pytest.raises(ValidationError):
        ElevationQueryRequest(latitude=-91.0, longitude=-42.92185)

def test_elevation_query_request_invalid_lon():
    with pytest.raises(ValidationError):
        ElevationQueryRequest(latitude=-22.15018, longitude=-181.0)

def test_elevation_profile_request_valid():
    req = ElevationProfileRequest(path=[[-22.15018, -42.92185], [-22.16, -42.93]])
    assert len(req.path) == 2

def test_elevation_profile_request_too_few_points():
    with pytest.raises(ValidationError):
        ElevationProfileRequest(path=[[-22.15018, -42.92185]])

def test_elevation_profile_request_invalid_lat_in_path():
    with pytest.raises(ValidationError):
        ElevationProfileRequest(path=[[-91.0, -42.92185], [-22.16, -42.93]])

def test_elevation_profile_request_invalid_lon_in_path():
    with pytest.raises(ValidationError):
        ElevationProfileRequest(path=[[-22.15018, -181.0], [-22.16, -42.93]])

def test_prepare_job_request_osm_valid():
    req = PrepareJobRequest(kind="osm", latitude=-22.15018, longitude=-42.92185, radius=100.0)
    assert req.kind == "osm"
    assert req.radius == 100.0

def test_prepare_job_request_osm_invalid_coords():
    with pytest.raises(ValidationError):
        PrepareJobRequest(kind="osm", latitude=200.0, longitude=-42.92185, radius=100.0)

# --- Circuit Breaker Tests ---
def test_circuit_breaker_flow():
    cb = CircuitBreaker(failure_threshold=2, recovery_timeout=0.1)
    
    def failing_func():
        raise ValueError("Fail")
    
    decorated = cb(failing_func)
    
    # First failure
    with pytest.raises(ValueError):
        decorated()
    assert cb.state == CircuitState.CLOSED
    
    # Second failure -> Open
    with pytest.raises(ValueError):
        decorated()
    assert cb.state == CircuitState.OPEN
    
    # Calls blocked
    with pytest.raises(CircuitBreakerOpenException):
        decorated()
        
    # Wait for recovery
    time.sleep(0.15)
    
    # Next call -> Half Open
    def success_func():
        return "ok"
    
    decorated_success = cb(success_func)
    assert decorated_success() == "ok"
    assert cb.state == CircuitState.CLOSED

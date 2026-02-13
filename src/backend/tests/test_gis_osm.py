import pytest
import json
from unittest.mock import MagicMock, patch
from backend.gis_core.osm import _parse_overpass_to_features, prepare_osm_compute
from backend.models import CadFeature

# --- Mock Data ---
OVERPASS_MOCK_DATA = {
    "elements": [
        {
            "type": "node",
            "id": 1,
            "lat": -23.55052,
            "lon": -46.633308,
            "tags": {"highway": "street_light", "name": "Light 1"}
        },
        {
            "type": "way",
            "id": 10,
            "nodes": [1, 2],
            "tags": {"highway": "residential", "name": "Street 1"}
        },
        {
            "type": "node",
            "id": 2,
            "lat": -23.551,
            "lon": -46.634,
            "tags": {}
        }
    ]
}

def test_parse_overpass_to_features():
    # Test coordinates projection and parsing
    nodes, edges = _parse_overpass_to_features(OVERPASS_MOCK_DATA, epsg_out=31983)
    
    assert len(nodes) == 1 # Only the one with tags
    assert len(edges) == 1
    assert edges[0].highway == "residential"
    assert nodes[0].highway == "street_light"

@patch("backend.gis_core.osm._fetch_overpass_data")
def test_prepare_osm_compute(mock_fetch):
    mock_fetch.return_value = OVERPASS_MOCK_DATA
    
    cache_svc = MagicMock()
    cache_svc.get.return_value = None
    
    elev_svc = MagicMock()
    elev_svc.get_elevation_profile.return_value = [10.0, 15.0]
    elev_svc.get_contours.return_value = []
    
    result = prepare_osm_compute(
        latitude=-23.55,
        longitude=-46.63,
        radius=100,
        cache_service=cache_svc,
        elevation_service=elev_svc
    )
    
    assert "features" in result
    features = result["features"]
    
    # Check if we have at least one Polyline and one Point
    types = [f["feature_type"] for f in features]
    assert "Polyline" in types
    assert "Point" in types
    
    # Check if elevation was injected
    elevated = [f for f in features if f.get("elevation") is not None]
    assert len(elevated) > 0
    
    # Ensure cache_service.set was called
    assert cache_svc.set.called

def test_prepare_osm_compute_cache_hit():
    cache_svc = MagicMock()
    cache_svc.get.return_value = {"features": [], "crs_out": "EPSG:31983"}
    
    elev_svc = MagicMock()
    
    result = prepare_osm_compute(
        latitude=-23.55,
        longitude=-46.63,
        radius=100,
        cache_service=cache_svc,
        elevation_service=elev_svc
    )
    
    assert result["cache_hit"] is True
    assert result["features"] == []

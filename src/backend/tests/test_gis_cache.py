"""
Tests for GIS Cache Service
"""

import pytest
import json
from backend.services.gis_cache import GISCacheService, InMemoryCache


def test_memory_cache_basic():
    """Test basic in-memory cache operations"""
    cache = InMemoryCache(max_size=10)
    
    # Set and get
    cache.set("key1", "value1", ttl=3600)
    assert cache.get("key1") == "value1"
    
    # Get non-existent key
    assert cache.get("key_nonexistent") is None
    
    # Stats
    stats = cache.get_stats()
    assert stats['hits'] == 1
    assert stats['misses'] == 1


def test_memory_cache_expiry():
    """Test TTL expiry in memory cache"""
    import time
    cache = InMemoryCache()
    
    # Set with 1 second TTL
    cache.set("key_expire", "value", ttl=1)
    assert cache.get("key_expire") == "value"
    
    # Wait for expiry
    time.sleep(1.1)
    assert cache.get("key_expire") is None  # Should be expired


def test_memory_cache_eviction():
    """Test that cache evicts oldest when full"""
    cache = InMemoryCache(max_size=3)
    
    cache.set("key1", "value1", ttl=3600)
    cache.set("key2", "value2", ttl=3600)
    cache.set("key3", "value3", ttl=3600)
    
    # Cache is full, adding 4th should evict oldest
    cache.set("key4", "value4", ttl=3600)
    
    # One of the first keys should be gone
    assert cache.get("key4") == "value4"
    assert len(cache._cache) == 3


def test_gis_cache_osm_data():
    """Test OSM data caching"""
    cache = GISCacheService(use_redis=False)  # Use in-memory
    
    bbox = (-21.7634, -41.3235, -21.7500, -41.3100)
    network_type = "all"
    osm_data = {
        "type": "FeatureCollection",
        "features": [{"type": "Feature", "geometry": {}, "properties": {}}]
    }
    
    # Cache miss
    result = cache.get_osm_data(bbox, network_type)
    assert result is None
    
    # Set cache
    cache.set_osm_data(bbox, network_type, osm_data)
    
    # Cache hit
    result = cache.get_osm_data(bbox, network_type)
    assert result is not None
    assert result['type'] == "FeatureCollection"


def test_gis_cache_geocode():
    """Test geocoding cache"""
    cache = GISCacheService(use_redis=False)
    
    address = "Rua Exemplo, 123, São Paulo"
    geocode_result = {
        "lat": -23.5505,
        "lon": -46.6333,
        "display_name": address
    }
    
    # Cache miss
    assert cache.get_geocode(address) is None
    
    # Set cache
    cache.set_geocode(address, geocode_result)
    
    # Cache hit
    result = cache.get_geocode(address)
    assert result is not None
    assert result['lat'] == -23.5505
    
    # Test case insensitivity
    result2 = cache.get_geocode(address.upper())
    assert result2 is not None


def test_gis_cache_crs_zone():
    """Test CRS zone caching"""
    cache = GISCacheService(use_redis=False)
    
    lat, lon = -21.7634, -41.3235
    utm_zone = 24
    
    # Cache miss
    assert cache.get_crs_zone(lat, lon) is None
    
    # Set cache
    cache.set_crs_zone(lat, lon, utm_zone)
    
    # Cache hit
    result = cache.get_crs_zone(lat, lon)
    assert result == utm_zone


def test_gis_cache_stats():
    """Test cache statistics"""
    cache = GISCacheService(use_redis=False)
    
    # Get initial stats
    stats = cache.get_stats()
    assert 'type' in stats
    assert stats['type'] == 'in-memory'
    
    # Do some operations
    bbox = (-21.7634, -41.3235, -21.7500, -41.3100)
    cache.get_osm_data(bbox, "all")  # miss
    cache.set_osm_data(bbox, "all", {})
    cache.get_osm_data(bbox, "all")  # hit
    
    # Check updated stats
    stats = cache.get_stats()
    assert stats['hits'] >= 1
    assert stats['misses'] >= 1


def test_gis_cache_clear():
    """Test cache clearing"""
    cache = GISCacheService(use_redis=False)
    
    # Add some data
    cache.set_osm_data((-21, -41, -20, -40), "all", {"test": "data"})
    cache.set_geocode("Test Address", {"lat": 0, "lon": 0})
    
    # Verify data exists
    assert cache.get_osm_data((-21, -41, -20, -40), "all") is not None
    
    # Clear
    cache.clear()
    
    # Verify data is gone
    assert cache.get_osm_data((-21, -41, -20, -40), "all") is None
    assert cache.get_geocode("Test Address") is None


def test_bbox_rounding():
    """Test that bbox coordinates are rounded for consistent caching"""
    cache = GISCacheService(use_redis=False)
    
    bbox1 = (-21.763456789, -41.323456789, -21.750000000, -41.310000000)
    bbox2 = (-21.763457, -41.323457, -21.750000, -41.310000)
    
    data = {"test": "data"}
    
    # Set with first bbox
    cache.set_osm_data(bbox1, "all", data)
    
    # Should hit with similar bbox (rounded to same value)
    result = cache.get_osm_data(bbox2, "all")
    assert result is not None

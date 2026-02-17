"""
Tests for cache service with metrics.
"""
import pytest
from backend.services.cache import CacheService


def test_cache_stats_initial():
    """Cache stats should start at zero."""
    cache = CacheService()
    stats = cache.get_stats()
    
    assert stats["hits"] == 0
    assert stats["misses"] == 0
    assert stats["total_requests"] == 0
    assert stats["hit_rate"] == 0


def test_cache_miss_increments():
    """Cache miss should increment counters."""
    cache = CacheService()
    cache.clear_stats()
    
    result = cache.get("nonexistent_key")
    assert result is None
    
    stats = cache.get_stats()
    assert stats["misses"] == 1
    assert stats["total_requests"] == 1
    assert stats["hit_rate"] == 0


def test_cache_hit_increments():
    """Cache hit should increment counters."""
    cache = CacheService()
    cache.clear_stats()
    
    # Set a value
    cache.set("test_key", {"data": "value"})
    
    # Get it back (should be a hit)
    result = cache.get("test_key")
    assert result == {"data": "value"}
    
    stats = cache.get_stats()
    assert stats["hits"] == 1
    assert stats["misses"] == 0
    assert stats["total_requests"] == 1
    assert stats["hit_rate"] == 100.0


def test_cache_hit_rate_calculation():
    """Hit rate should be calculated correctly."""
    cache = CacheService()
    cache.clear_stats()
    
    # Set some values
    cache.set("key1", "value1")
    cache.set("key2", "value2")
    
    # 2 hits
    cache.get("key1")
    cache.get("key2")
    
    # 3 misses
    cache.get("nonexistent1")
    cache.get("nonexistent2")
    cache.get("nonexistent3")
    
    stats = cache.get_stats()
    assert stats["hits"] == 2
    assert stats["misses"] == 3
    assert stats["total_requests"] == 5
    assert stats["hit_rate"] == 40.0  # 2/5 = 40%


def test_cache_clear_stats():
    """Clear stats should reset counters."""
    cache = CacheService()
    
    # Generate some activity
    cache.set("key1", "value1")
    cache.get("key1")
    cache.get("nonexistent")
    
    # Verify we have stats
    stats = cache.get_stats()
    assert stats["total_requests"] > 0
    
    # Clear
    cache.clear_stats()
    
    # Verify reset
    stats = cache.get_stats()
    assert stats["hits"] == 0
    assert stats["misses"] == 0
    assert stats["total_requests"] == 0


def test_cache_stats_with_complex_data():
    """Cache should handle complex data and track stats."""
    cache = CacheService()
    cache.clear_stats()
    
    complex_data = {
        "features": [
            {"type": "Point", "coords": [1.0, 2.0]},
            {"type": "LineString", "coords": [[1.0, 2.0], [3.0, 4.0]]}
        ],
        "metadata": {
            "count": 2,
            "bbox": [1.0, 2.0, 3.0, 4.0]
        }
    }
    
    cache.set("complex_key", complex_data)
    result = cache.get("complex_key")
    
    assert result == complex_data
    stats = cache.get_stats()
    assert stats["hits"] == 1
    assert stats["hit_rate"] == 100.0


def test_cache_backend_info():
    """Stats should include backend information."""
    cache = CacheService()
    stats = cache.get_stats()
    
    assert "backend" in stats
    assert "cache_dir" in stats
    # Without Redis, backend should be "file"
    assert stats["backend"] == "file"

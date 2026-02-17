"""
GIS Cache Service - In-Memory Implementation

Provides caching for expensive GIS operations (OSM data, geocoding, etc.)
with fallback to in-memory when Redis is not available.

Part of Implementation #1 from Fullstack Analysis.

Usage:
    from backend.services.gis_cache import gis_cache
    
    # Try to get from cache
    data = gis_cache.get_osm_data(bbox, network_type)
    if data is None:
        # Cache miss - compute
        data = expensive_osm_operation()
        gis_cache.set_osm_data(bbox, network_type, data)
"""

import hashlib
import json
import time
from typing import Optional, Dict, Any, Tuple
from functools import lru_cache
import logging

logger = logging.getLogger(__name__)


class InMemoryCache:
    """
    Simple in-memory cache with TTL support.
    
    This is a fallback when Redis is not available.
    Uses Python dict with timestamps for TTL.
    """
    
    def __init__(self, max_size: int = 100):
        self._cache: Dict[str, Tuple[Any, float]] = {}  # key -> (value, expiry_time)
        self._max_size = max_size
        self._hits = 0
        self._misses = 0
    
    def get(self, key: str) -> Optional[str]:
        """Get value from cache, returns None if not found or expired"""
        if key in self._cache:
            value, expiry = self._cache[key]
            if time.time() < expiry:
                self._hits += 1
                return value
            else:
                # Expired - remove it
                del self._cache[key]
        
        self._misses += 1
        return None
    
    def set(self, key: str, value: str, ttl: int):
        """Set value in cache with TTL in seconds"""
        # Simple eviction: if full, remove oldest
        if len(self._cache) >= self._max_size:
            # Find and remove the entry with earliest expiry
            oldest_key = min(self._cache.keys(), key=lambda k: self._cache[k][1])
            del self._cache[oldest_key]
        
        expiry_time = time.time() + ttl
        self._cache[key] = (value, expiry_time)
    
    def delete(self, key: str):
        """Delete key from cache"""
        if key in self._cache:
            del self._cache[key]
    
    def clear(self):
        """Clear all cache"""
        self._cache.clear()
        self._hits = 0
        self._misses = 0
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        total = self._hits + self._misses
        hit_rate = (self._hits / total * 100) if total > 0 else 0
        
        return {
            'type': 'in-memory',
            'hits': self._hits,
            'misses': self._misses,
            'total_requests': total,
            'hit_rate': f"{hit_rate:.1f}%",
            'size': len(self._cache),
            'max_size': self._max_size
        }


class GISCacheService:
    """
    GIS-specific caching service.
    
    Caches expensive operations:
    - OSM data by bounding box
    - Geocoding results
    - CRS transformations
    - Terrain data
    
    Automatically falls back to in-memory cache if Redis unavailable.
    """
    
    def __init__(self, redis_url: Optional[str] = None, use_redis: bool = True):
        """
        Initialize cache service.
        
        Args:
            redis_url: Redis connection URL (e.g., "redis://localhost:6379/0")
            use_redis: Whether to try using Redis (defaults to True)
        """
        self.redis_client = None
        self.memory_cache = InMemoryCache(max_size=100)
        
        if use_redis and redis_url:
            try:
                import redis
                self.redis_client = redis.from_url(redis_url, decode_responses=True)
                # Test connection
                self.redis_client.ping()
                logger.info("gis_cache_redis_connected", url=redis_url)
            except Exception as e:
                logger.warning("gis_cache_redis_unavailable", error=str(e), fallback="in-memory")
                self.redis_client = None
        else:
            logger.info("gis_cache_using_memory", reason="Redis disabled or no URL")
        
        # TTL configurations (in seconds)
        self.ttl_osm = 7 * 24 * 3600  # 7 days
        self.ttl_geocode = 30 * 24 * 3600  # 30 days (geocoding rarely changes)
        self.ttl_crs = 90 * 24 * 3600  # 90 days (CRS never changes)
    
    def _make_key(self, prefix: str, *args) -> str:
        """Generate cache key from arguments"""
        key_parts = [str(arg) for arg in args]
        key_str = ":".join(key_parts)
        # Hash if too long
        if len(key_str) > 200:
            key_hash = hashlib.md5(key_str.encode()).hexdigest()
            return f"{prefix}:{key_hash}"
        return f"{prefix}:{key_str}"
    
    def _get(self, key: str) -> Optional[str]:
        """Get from Redis or memory cache"""
        if self.redis_client:
            try:
                return self.redis_client.get(key)
            except Exception as e:
                logger.error("redis_get_failed", key=key, error=str(e))
                # Fallback to memory
                return self.memory_cache.get(key)
        else:
            return self.memory_cache.get(key)
    
    def _set(self, key: str, value: str, ttl: int):
        """Set in Redis or memory cache"""
        if self.redis_client:
            try:
                self.redis_client.setex(key, ttl, value)
            except Exception as e:
                logger.error("redis_set_failed", key=key, error=str(e))
                # Fallback to memory
                self.memory_cache.set(key, value, ttl)
        else:
            self.memory_cache.set(key, value, ttl)
    
    # --- OSM Data Caching ---
    
    def get_osm_data(self, bbox: Tuple[float, float, float, float], network_type: str = "all") -> Optional[Dict]:
        """
        Get cached OSM data for a bounding box.
        
        Args:
            bbox: (min_lat, min_lon, max_lat, max_lon)
            network_type: OSM network type ('all', 'drive', 'walk', etc.)
        
        Returns:
            Cached OSM data dict or None if not found
        """
        # Round bbox to 6 decimals for consistent keys (~0.1m precision)
        bbox_rounded = tuple(round(x, 6) for x in bbox)
        key = self._make_key("osm", network_type, *bbox_rounded)
        
        cached = self._get(key)
        if cached:
            logger.debug("osm_cache_hit", bbox=bbox_rounded, network_type=network_type)
            return json.loads(cached)
        
        logger.debug("osm_cache_miss", bbox=bbox_rounded, network_type=network_type)
        return None
    
    def set_osm_data(self, bbox: Tuple[float, float, float, float], network_type: str, data: Dict):
        """Cache OSM data"""
        bbox_rounded = tuple(round(x, 6) for x in bbox)
        key = self._make_key("osm", network_type, *bbox_rounded)
        
        try:
            value = json.dumps(data)
            self._set(key, value, self.ttl_osm)
            logger.debug("osm_cache_set", bbox=bbox_rounded, network_type=network_type)
        except Exception as e:
            logger.error("osm_cache_set_failed", error=str(e))
    
    # --- Geocoding Caching ---
    
    def get_geocode(self, address: str) -> Optional[Dict]:
        """Get cached geocoding result"""
        # Normalize address for consistent caching
        address_normalized = address.lower().strip()
        key = self._make_key("geocode", address_normalized)
        
        cached = self._get(key)
        if cached:
            logger.debug("geocode_cache_hit", address=address)
            return json.loads(cached)
        
        logger.debug("geocode_cache_miss", address=address)
        return None
    
    def set_geocode(self, address: str, data: Dict):
        """Cache geocoding result"""
        address_normalized = address.lower().strip()
        key = self._make_key("geocode", address_normalized)
        
        try:
            value = json.dumps(data)
            self._set(key, value, self.ttl_geocode)
            logger.debug("geocode_cache_set", address=address)
        except Exception as e:
            logger.error("geocode_cache_set_failed", error=str(e))
    
    # --- CRS Transformation Caching ---
    
    def get_crs_zone(self, lat: float, lon: float) -> Optional[int]:
        """Get cached UTM zone for coordinates"""
        lat_rounded = round(lat, 2)
        lon_rounded = round(lon, 2)
        key = self._make_key("crs_zone", lat_rounded, lon_rounded)
        
        cached = self._get(key)
        if cached:
            return int(cached)
        return None
    
    def set_crs_zone(self, lat: float, lon: float, zone: int):
        """Cache UTM zone"""
        lat_rounded = round(lat, 2)
        lon_rounded = round(lon, 2)
        key = self._make_key("crs_zone", lat_rounded, lon_rounded)
        
        self._set(key, str(zone), self.ttl_crs)
    
    # --- Statistics ---
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        if self.redis_client:
            try:
                info = self.redis_client.info()
                return {
                    'type': 'redis',
                    'connected': True,
                    'used_memory': info.get('used_memory_human', 'N/A'),
                    'total_keys': self.redis_client.dbsize(),
                    'hits': info.get('keyspace_hits', 0),
                    'misses': info.get('keyspace_misses', 0)
                }
            except Exception as e:
                logger.error("redis_stats_failed", error=str(e))
                return {'type': 'redis', 'connected': False, 'error': str(e)}
        else:
            return self.memory_cache.get_stats()
    
    def clear(self):
        """Clear all caches"""
        if self.redis_client:
            try:
                self.redis_client.flushdb()
                logger.info("redis_cache_cleared")
            except Exception as e:
                logger.error("redis_clear_failed", error=str(e))
        
        self.memory_cache.clear()
        logger.info("memory_cache_cleared")


# Global singleton instance
# Can be configured via environment variables
import os
_redis_url = os.environ.get("REDIS_URL", None)
_use_redis = os.environ.get("USE_REDIS_CACHE", "false").lower() == "true"

gis_cache = GISCacheService(redis_url=_redis_url, use_redis=_use_redis)

import os
import json
import logging
from typing import Optional, Any
from backend.core.utils import read_cache as read_file_cache, write_cache as write_file_cache, sanitize_jsonable

logger = logging.getLogger("sisrua.cache")

class CacheService:
    """
    Tiered caching service:
    L1: Redis (In-memory, distributed)
    L2: Filesystem (Persistent, local fallback)
    """
    def __init__(self):
        self.redis_url = os.environ.get("REDIS_URL")
        self.redis = None
        
        if self.redis_url:
            try:
                import redis
                self.redis = redis.from_url(self.redis_url, decode_responses=True)
                # Quick health check
                self.redis.ping()
                logger.info(f"[cache] Redis connected at {self.redis_url}")
            except Exception as e:
                logger.warning(f"[cache] Failed to connect to Redis: {e}. Falling back to filesystem only.")
                self.redis = None

    def get(self, key: str) -> Optional[Any]:
        """
        Retrieves data from Redis (L1) or Filesystem (L2).
        """
        # 1. Try Redis
        if self.redis:
            try:
                data = self.redis.get(key)
                if data:
                    logger.debug(f"[cache] Hit (Redis): {key}")
                    return json.loads(data)
            except Exception as e:
                logger.error(f"[cache] Redis get error: {e}")

        # 2. Try Filesystem Fallback
        cached = read_file_cache(key)
        if cached:
            logger.debug(f"[cache] Hit (Filesystem): {key}")
            # If we missed Redis but hit File, repopulate Redis (read-through)
            if self.redis:
                self._safe_redis_set(key, cached)
            return cached

        logger.debug(f"[cache] Miss: {key}")
        return None

    def set(self, key: str, value: Any, ttl: int = 3600) -> None:
        """
        Saves data to both Redis and Filesystem.
        """
        # Always write to filesystem for persistence
        write_file_cache(key, value)
        
        # Write to Redis if available
        if self.redis:
            self._safe_redis_set(key, value, ttl)

    def _safe_redis_set(self, key: str, value: Any, ttl: Optional[int] = 3600) -> None:
        try:
            sanitized = sanitize_jsonable(value)
            self.redis.set(key, json.dumps(sanitized, ensure_ascii=False), ex=ttl)
        except Exception as e:
            logger.error(f"[cache] Redis set error: {e}")

# Singleton instance
cache_service = CacheService()

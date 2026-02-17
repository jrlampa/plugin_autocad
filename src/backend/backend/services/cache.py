import os
import json
import logging
from pathlib import Path
from typing import Optional, Any
from backend.core.utils import sanitize_jsonable

logger = logging.getLogger("sisrua.cache")

class CacheService:
    """
    Tiered caching service with metrics:
    L1: Redis (In-memory, distributed)
    L2: Filesystem (Persistent, local fallback)
    
    Features:
    - Hit/miss tracking
    - Performance metrics
    - TTL support
    """
    def __init__(self):
        # Filesystem cache config
        base = Path(os.environ.get("LOCALAPPDATA") or Path.home())
        self.file_cache_dir = base / "sisRUA" / "cache"
        self.file_cache_dir.mkdir(parents=True, exist_ok=True)

        self.redis = None # Redis removed for local standalone plugin
        
        # Metrics
        self._hits = 0
        self._misses = 0
        self._total_requests = 0

    def _sanitize_key(self, key: str) -> str:
        # Replace non-filesystem safe chars
        return key.replace(":", "_").replace("/", "_").replace("\\", "_")

    def get(self, key: str) -> Optional[Any]:
        self._total_requests += 1
        
        # 1. Try Redis
        if self.redis:
            try:
                data = self.redis.get(key)
                if data:
                    self._hits += 1
                    logger.debug(f"[cache] HIT (Redis): {key[:50]}")
                    return json.loads(data)
            except Exception:
                pass

        # 2. Try Filesystem
        try:
            filename = self._sanitize_key(key) + ".json"
            path = self.file_cache_dir / filename
            if path.exists():
                data = json.loads(path.read_text(encoding="utf-8"))
                cached = sanitize_jsonable(data)
                self._hits += 1
                logger.debug(f"[cache] HIT (File): {key[:50]}")
                # Read-through: Repopulate Redis
                if self.redis:
                    self._safe_redis_set(key, cached)
                return cached
        except Exception:
            pass

        self._misses += 1
        logger.debug(f"[cache] MISS: {key[:50]}")
        return None

    def set(self, key: str, value: Any, ttl: int = 3600) -> None:
        # File Persistence
        try:
            filename = self._sanitize_key(key) + ".json"
            path = self.file_cache_dir / filename
            safe = sanitize_jsonable(value)
            path.write_text(json.dumps(safe, ensure_ascii=False), encoding="utf-8")
        except Exception as e:
            logger.error(f"[cache] File write error: {e}")
        
        # Redis Speed
        if self.redis:
            self._safe_redis_set(key, value, ttl)

    def _safe_redis_set(self, key: str, value: Any, ttl: Optional[int] = 3600) -> None:
        try:
            sanitized = sanitize_jsonable(value)
            self.redis.set(key, json.dumps(sanitized, ensure_ascii=False), ex=ttl)
        except Exception:
            pass
    
    def get_stats(self) -> dict:
        """Get cache statistics for monitoring."""
        hit_rate = (self._hits / self._total_requests * 100) if self._total_requests > 0 else 0
        return {
            "hits": self._hits,
            "misses": self._misses,
            "total_requests": self._total_requests,
            "hit_rate": round(hit_rate, 2),
            "backend": "redis+file" if self.redis else "file",
            "cache_dir": str(self.file_cache_dir)
        }
    
    def clear_stats(self) -> None:
        """Reset cache statistics."""
        self._hits = 0
        self._misses = 0
        self._total_requests = 0
        logger.info("[cache] Statistics cleared")

# Module-level singleton
cache_service = CacheService()

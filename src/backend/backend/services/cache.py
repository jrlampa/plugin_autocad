import os
import json
import logging
from pathlib import Path
from typing import Optional, Any
from backend.core.utils import sanitize_jsonable

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
        
        # Filesystem cache config
        base = Path(os.environ.get("LOCALAPPDATA") or Path.home())
        self.file_cache_dir = base / "sisRUA" / "cache"
        self.file_cache_dir.mkdir(parents=True, exist_ok=True)

        if self.redis_url:
            try:
                import redis
                self.redis = redis.from_url(self.redis_url, decode_responses=True)
                self.redis.ping()
                logger.info(f"[cache] Redis connected at {self.redis_url}")
            except Exception as e:
                logger.warning(f"[cache] Redis unavailable: {e}")

    def _sanitize_key(self, key: str) -> str:
        # Replace non-filesystem safe chars
        return key.replace(":", "_").replace("/", "_").replace("\\", "_")

    def get(self, key: str) -> Optional[Any]:
        # 1. Try Redis
        if self.redis:
            try:
                data = self.redis.get(key)
                if data:
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
                # Read-through: Repopulate Redis
                if self.redis:
                    self._safe_redis_set(key, cached)
                return cached
        except Exception:
            pass

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

# Module-level singleton
cache_service = CacheService()

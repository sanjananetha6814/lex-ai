import os
import time
import copy
import json
import logging
import threading
from typing import Any, Optional, Dict, Tuple

logger = logging.getLogger(__name__)

class CacheManager:
    """
    Thread-safe, high-performance cache manager.
    Supports in-memory TTL caching with optional Redis backend for multi-process consistency.
    """
    def __init__(self, default_ttl: int = 60):
        self.default_ttl = default_ttl
        self._memory_cache: Dict[str, Tuple[Any, float]] = {}
        self._lock = threading.RLock()
        self._redis_client = None
        self._redis_available = False

        # Attempt Redis connection if REDIS_URL is explicitly configured
        redis_url = os.getenv("REDIS_URL")
        if redis_url:
            try:
                import redis
                self._redis_client = redis.Redis.from_url(redis_url, socket_timeout=2)
                self._redis_client.ping()
                self._redis_available = True
                logger.info("Shared Redis cache backend initialized successfully.")
            except Exception as e:
                logger.warning("Redis configured but unavailable (%s). Using thread-safe in-memory cache fallback.", e)
                self._redis_client = None
                self._redis_available = False

    def get(self, key: str) -> Optional[Any]:
        """Retrieve an item from cache if present and not expired."""
        if self._redis_available and self._redis_client:
            try:
                raw = self._redis_client.get(key)
                if raw is not None:
                    return json.loads(raw.decode("utf-8"))
                # Key does not exist in Redis (or was invalidated by another worker)
                return None
            except Exception as e:
                logger.debug("Redis read error for key %s: %s. Falling back to local cache.", key, e)

        # In-memory lookup
        with self._lock:
            entry = self._memory_cache.get(key)
            if not entry:
                return None
            val, expiry = entry
            if time.time() > expiry:
                del self._memory_cache[key]
                return None
            return copy.deepcopy(val)

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Store an item in cache with a TTL in seconds."""
        effective_ttl = ttl if ttl is not None else self.default_ttl

        if self._redis_available and self._redis_client:
            try:
                # Handle Pydantic models, dicts, or lists
                serialized = json.dumps(value, default=lambda o: getattr(o, "model_dump", lambda: str(o))())
                self._redis_client.set(key, serialized, ex=effective_ttl)
                return
            except Exception as e:
                logger.debug("Redis write error for key %s: %s. Storing in local cache.", key, e)

        with self._lock:
            expiry = time.time() + effective_ttl
            self._memory_cache[key] = (copy.deepcopy(value), expiry)

    def invalidate_key(self, key: str) -> None:
        """Invalidate a specific cache key."""
        if self._redis_available and self._redis_client:
            try:
                self._redis_client.delete(key)
                return
            except Exception as e:
                logger.debug("Redis delete error: %s", e)

        with self._lock:
            self._memory_cache.pop(key, None)

    def invalidate_prefix(self, prefix: str) -> None:
        """Invalidate all keys matching a prefix (e.g. 'lawyers:')."""
        if self._redis_available and self._redis_client:
            try:
                keys = self._redis_client.keys(f"{prefix}*")
                if keys:
                    self._redis_client.delete(*keys)
                return
            except Exception as e:
                logger.debug("Redis prefix delete error: %s", e)

        with self._lock:
            to_delete = [k for k in self._memory_cache if k.startswith(prefix)]
            for k in to_delete:
                del self._memory_cache[k]

    def clear(self) -> None:
        """Clear the entire cache."""
        if self._redis_available and self._redis_client:
            try:
                self._redis_client.flushdb()
                return
            except Exception as e:
                logger.debug("Redis flush error: %s", e)

        with self._lock:
            self._memory_cache.clear()

# Global singleton instance
cache_manager = CacheManager(default_ttl=60)

def get_lawyer_list_cache_key(
    search: Optional[str] = None,
    city: Optional[str] = None,
    specialty: Optional[str] = None,
    skip: int = 0,
    limit: int = 50
) -> str:
    """Generate a deterministic cache key for lawyer directory queries."""
    s = search.strip().lower() if search else ""
    c = city.strip().lower() if city else ""
    sp = specialty.strip().lower() if specialty else ""
    return f"lawyers:list:s={s}:c={c}:sp={sp}:sk={skip}:lim={limit}"

def get_lawyer_detail_cache_key(lawyer_id: int) -> str:
    """Generate a deterministic cache key for single lawyer profile."""
    return f"lawyers:detail:{lawyer_id}"

def invalidate_lawyer_caches(lawyer_id: Optional[int] = None) -> None:
    """
    Invalidate public lawyer caches when reviews or profile details change.
    Invalidates directory listings and optionally a specific detail record.
    """
    cache_manager.invalidate_prefix("lawyers:list:")
    if lawyer_id is not None:
        cache_manager.invalidate_key(get_lawyer_detail_cache_key(lawyer_id))
    else:
        cache_manager.invalidate_prefix("lawyers:detail:")


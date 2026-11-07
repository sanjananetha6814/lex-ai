import os
import time
import logging
import threading
from typing import Optional, Dict, List
from fastapi import Request, HTTPException, status
from app.config import settings

logger = logging.getLogger(__name__)

class RateLimiter:
    """
    High-performance distributed rate limiter for authentication and sensitive routes.
    Uses Redis backend for multi-worker coordination across Uvicorn processes when available,
    with a thread-safe sliding-window in-memory fallback.
    """
    def __init__(self, default_limit: int = 10, window_seconds: int = 60):
        self.default_limit = default_limit
        self.window_seconds = window_seconds
        self._memory_buckets: Dict[str, List[float]] = {}
        self._lock = threading.RLock()
        self._redis_client = None
        self._redis_available = False

        # Attempt Redis connection from environment or settings
        redis_url = os.getenv("REDIS_URL")
        if redis_url:
            try:
                import redis
                self._redis_client = redis.Redis.from_url(redis_url, socket_timeout=2)
                self._redis_client.ping()
                self._redis_available = True
                logger.info("RateLimiter: Shared Redis backend connected successfully.")
            except Exception as e:
                logger.warning("RateLimiter: Redis unavailable (%s). Using thread-safe in-memory fallback.", e)
                self._redis_client = None
                self._redis_available = False

    def _get_client_ip(self, request: Request) -> str:
        """
        Extract the authoritative client IP address.
        Uvicorn with --proxy-headers and --forwarded-allow-ips automatically
        populates request.client.host from the trusted reverse proxy.
        """
        # If running behind trusted reverse proxy
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            # Client IP is the first entry in X-Forwarded-For
            client_ip = forwarded_for.split(",")[0].strip()
            if client_ip:
                return client_ip

        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip.strip()

        if request.client and request.client.host:
            return request.client.host

        return "127.0.0.1"

    def check_rate_limit(
        self,
        request: Request,
        key_prefix: str = "login",
        limit: Optional[int] = None,
        window: Optional[int] = None
    ) -> None:
        """
        Enforce sliding-window rate limit for the requesting client IP.
        Raises HTTP 429 Too Many Requests if the limit is exceeded.
        """
        # Allow disabling rate limiting during specific test suites via environment variable
        if os.getenv("DISABLE_RATE_LIMITER", "").lower() in ["true", "1", "yes"]:
            return

        effective_limit = limit if limit is not None else int(os.getenv("AUTH_RATE_LIMIT_LOGIN", str(self.default_limit)))
        effective_window = window if window is not None else self.window_seconds

        client_ip = self._get_client_ip(request)
        rate_key = f"ratelimit:{key_prefix}:{client_ip}"
        now = time.time()
        window_start = now - effective_window

        # 1. Distributed Redis sliding window
        if self._redis_available and self._redis_client:
            try:
                pipe = self._redis_client.pipeline()
                pipe.zremrangebyscore(rate_key, 0, window_start)
                pipe.zcard(rate_key)
                res = pipe.execute()
                current_count = res[1]

                if current_count >= effective_limit:
                    logger.warning(
                        "Rate limit exceeded for IP %s on prefix '%s' (Count: %d, Limit: %d)",
                        client_ip, key_prefix, current_count, effective_limit
                    )
                    raise HTTPException(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        detail="Too many login attempts. Please try again later.",
                        headers={"Retry-After": str(effective_window)}
                    )

                # Record current request with a unique member key
                member = f"{now}:{os.urandom(4).hex()}"
                pipe = self._redis_client.pipeline()
                pipe.zadd(rate_key, {member: now})
                pipe.expire(rate_key, effective_window + 5)
                pipe.execute()
                return
            except HTTPException:
                raise
            except Exception as e:
                logger.debug("Redis rate limiting error (%s). Falling back to in-memory check.", e)

        # 2. In-memory sliding window fallback
        with self._lock:
            timestamps = self._memory_buckets.get(rate_key, [])
            # Prune expired timestamps
            timestamps = [t for t in timestamps if t > window_start]

            if len(timestamps) >= effective_limit:
                self._memory_buckets[rate_key] = timestamps
                logger.warning(
                    "In-memory rate limit exceeded for IP %s on prefix '%s' (Count: %d, Limit: %d)",
                    client_ip, key_prefix, len(timestamps), effective_limit
                )
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Too many login attempts. Please try again later.",
                    headers={"Retry-After": str(effective_window)}
                )

            timestamps.append(now)
            self._memory_buckets[rate_key] = timestamps

    def reset(self) -> None:
        """Reset rate limiter buckets (used primarily in test fixtures)."""
        with self._lock:
            self._memory_buckets.clear()
        if self._redis_available and self._redis_client:
            try:
                keys = self._redis_client.keys("ratelimit:*")
                if keys:
                    self._redis_client.delete(*keys)
            except Exception:
                pass

auth_rate_limiter = RateLimiter(default_limit=10, window_seconds=60)


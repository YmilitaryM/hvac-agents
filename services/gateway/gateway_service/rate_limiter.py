import time
from collections import defaultdict

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware


class RateLimiter:
    """Token-bucket rate limiter per client IP."""

    def __init__(self, rate: int = 100, burst: int = 200):
        self._rate = rate  # requests per second
        self._burst = burst
        self._buckets: dict[str, tuple[float, float]] = {}  # ip -> (tokens, last_update)

    def is_allowed(self, client_id: str) -> bool:
        now = time.monotonic()
        tokens, last = self._buckets.get(client_id, (float(self._burst), now))
        elapsed = now - last
        tokens = min(self._burst, tokens + elapsed * self._rate)
        self._buckets[client_id] = (tokens - 1.0, now)
        return tokens >= 1.0


class RateLimitMiddleware(BaseHTTPMiddleware):
    """FastAPI middleware for per-IP rate limiting."""

    def __init__(self, app, rate: int = 100, burst: int = 200):
        super().__init__(app)
        self._limiter = RateLimiter(rate=rate, burst=burst)

    async def dispatch(self, request: Request, call_next):
        client = request.client.host if request.client else "unknown"
        if not self._limiter.is_allowed(client):
            return Response(
                content='{"detail":"Too Many Requests"}',
                status_code=429,
                media_type="application/json",
            )
        return await call_next(request)

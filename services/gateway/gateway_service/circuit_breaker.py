import asyncio
import time
from collections import defaultdict
from enum import Enum
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse


class CircuitState(str, Enum):
    CLOSED = "closed"  # normal operation
    OPEN = "open"  # failing, reject requests
    HALF_OPEN = "half_open"  # testing recovery


class CircuitBreaker:
    """Circuit breaker that opens after consecutive failures and probes with half-open."""

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 30.0,
        half_open_limit: int = 3,
    ):
        self._failure_threshold = failure_threshold
        self._recovery_timeout = recovery_timeout
        self._half_open_limit = half_open_limit
        self._state: dict[str, CircuitState] = defaultdict(lambda: CircuitState.CLOSED)
        self._failures: dict[str, int] = defaultdict(int)
        self._last_failure: dict[str, float] = {}
        self._half_open_count: dict[str, int] = defaultdict(int)

    def _transition(self, service: str, new_state: CircuitState) -> None:
        self._state[service] = new_state

    def record_success(self, service: str) -> None:
        if self._state[service] == CircuitState.HALF_OPEN:
            self._half_open_count[service] += 1
            if self._half_open_count[service] >= self._half_open_limit:
                self._transition(service, CircuitState.CLOSED)
                self._failures[service] = 0
                self._half_open_count[service] = 0

    def record_failure(self, service: str) -> None:
        self._failures[service] += 1
        self._last_failure[service] = time.monotonic()
        if (
            self._state[service] == CircuitState.CLOSED
            and self._failures[service] >= self._failure_threshold
        ):
            self._transition(service, CircuitState.OPEN)

    def is_allowed(self, service: str) -> bool:
        state = self._state[service]
        if state == CircuitState.CLOSED:
            return True
        if state == CircuitState.OPEN:
            elapsed = time.monotonic() - self._last_failure.get(service, 0)
            if elapsed >= self._recovery_timeout:
                self._transition(service, CircuitState.HALF_OPEN)
                self._half_open_count[service] = 0
                return True
            return False
        return True  # HALF_OPEN — allow probe request

    def get_state(self, service: str) -> dict:
        return {
            "state": self._state[service],
            "failures": self._failures[service],
        }


class CircuitBreakerMiddleware(BaseHTTPMiddleware):
    """FastAPI middleware to wrap downstream calls with circuit breaker."""

    def __init__(
        self,
        app,
        failure_threshold: int = 5,
        recovery_timeout: float = 30.0,
    ):
        super().__init__(app)
        self._breaker = CircuitBreaker(
            failure_threshold=failure_threshold,
            recovery_timeout=recovery_timeout,
        )

    async def dispatch(self, request: Request, call_next):
        # Extract service name from URL path
        path = request.url.path
        service = "unknown"
        if path.startswith("/api/"):
            parts = path.split("/")
            if len(parts) > 2:
                service = parts[2]  # /api/{service}/...

        if not self._breaker.is_allowed(service):
            return JSONResponse(
                status_code=503,
                content={"detail": f"Service {service} is temporarily unavailable"},
            )

        try:
            response = await call_next(request)
            if response.status_code < 500:
                self._breaker.record_success(service)
            else:
                self._breaker.record_failure(service)
            return response
        except Exception:
            self._breaker.record_failure(service)
            return JSONResponse(
                status_code=502,
                content={"detail": "Bad Gateway"},
            )

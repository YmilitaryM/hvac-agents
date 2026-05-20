"""Shared Prometheus metrics setup for all HVAC services."""

from prometheus_client import Counter, Histogram, Gauge, generate_latest, REGISTRY
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
import time


REQUEST_COUNT = Counter(
    "hvac_http_requests_total",
    "Total HTTP requests",
    ["service", "method", "endpoint", "status"],
)

REQUEST_LATENCY = Histogram(
    "hvac_http_request_duration_seconds",
    "HTTP request duration",
    ["service", "method", "endpoint"],
)

DB_POOL_SIZE = Gauge(
    "hvac_db_pool_size",
    "Database connection pool size",
    ["service"],
)

DB_POOL_ACTIVE = Gauge(
    "hvac_db_pool_active",
    "Active database connections",
    ["service"],
)

CIRCUIT_BREAKER_STATE = Gauge(
    "hvac_circuit_breaker_state",
    "Circuit breaker state (0=closed, 1=open, 2=half_open)",
    ["service", "target"],
)


def metrics_endpoint() -> Response:
    """FastAPI endpoint handler for /metrics."""
    return Response(
        content=generate_latest(REGISTRY),
        media_type="text/plain; version=0.0.4",
    )


class MetricsMiddleware(BaseHTTPMiddleware):
    """FastAPI middleware to record request metrics."""

    def __init__(self, app, service_name: str):
        super().__init__(app)
        self._service = service_name

    async def dispatch(self, request: Request, call_next):
        start = time.monotonic()
        response = await call_next(request)
        duration = time.monotonic() - start

        endpoint = request.url.path
        REQUEST_COUNT.labels(
            service=self._service,
            method=request.method,
            endpoint=endpoint,
            status=response.status_code,
        ).inc()
        REQUEST_LATENCY.labels(
            service=self._service,
            method=request.method,
            endpoint=endpoint,
        ).observe(duration)

        return response

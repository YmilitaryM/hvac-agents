"""FastAPI application for the HVAC chiller plant multi-agent system."""

import logging
import time
import uuid

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from .monitoring import router as monitoring_router
from .strategy import router as strategy_router
from .reports import router as reports_router
from .websocket import router as ws_router

logger = logging.getLogger(__name__)


def create_app(debug: bool = False) -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="HVAC Chiller Plant Multi-Agent System",
        description="REST API for real-time monitoring, strategy management, and reporting",
        version="0.1.0",
        debug=debug,
    )

    # CORS middleware for frontend access
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Request ID middleware for tracing
    @app.middleware("http")
    async def add_request_id(request: Request, call_next):
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4())[:8])
        request.state.request_id = request_id
        t0 = time.monotonic()
        response = await call_next(request)
        elapsed = (time.monotonic() - t0) * 1000
        logger.info(
            "%s %s -> %d (%.0fms) [%s]",
            request.method,
            request.url.path,
            response.status_code,
            elapsed,
            request_id,
        )
        response.headers["X-Request-ID"] = request_id
        return response

    # Mount routers
    app.include_router(monitoring_router, prefix="/api/monitoring", tags=["Monitoring"])
    app.include_router(strategy_router, prefix="/api/strategies", tags=["Strategies"])
    app.include_router(reports_router, prefix="/api/reports", tags=["Reports"])
    app.include_router(ws_router, tags=["WebSocket"])

    # Database lifecycle
    @app.on_event("startup")
    async def startup_db():
        from src.config import get_config
        if get_config().storage.use_db:
            from src.db.engine import init_db
            await init_db()

    @app.on_event("shutdown")
    async def shutdown_db():
        from src.config import get_config
        if get_config().storage.use_db:
            from src.db.engine import close_db
            await close_db()

    @app.get("/api/health")
    async def health_check():
        return {"status": "healthy", "version": "0.1.0"}

    @app.get("/api/status")
    async def system_status():
        """Get overall system status."""
        return {
            "status": "running",
            "agents": {
                "monitor": "ready",
                "predict": "ready",
                "strategy": "ready",
                "advocates": "ready",
                "coordinator": "ready",
                "safety": "ready",
                "parameter": "ready",
                "report": "ready",
            },
            "execution_status": "idle",
        }

    return app


# Default application instance
app = create_app()

"""FastAPI application for the HVAC chiller plant multi-agent system."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .monitoring import router as monitoring_router
from .strategy import router as strategy_router
from .reports import router as reports_router


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

    # Mount routers
    app.include_router(monitoring_router, prefix="/api/monitoring", tags=["Monitoring"])
    app.include_router(strategy_router, prefix="/api/strategies", tags=["Strategies"])
    app.include_router(reports_router, prefix="/api/reports", tags=["Reports"])

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

from contextlib import asynccontextmanager

import redis.asyncio as aioredis
from fastapi import FastAPI

from common.metrics import MetricsMiddleware, metrics_endpoint

from .api import simulation, faults, whatif, rl_env
from .api import calibration as _calibration  # noqa: F401
from .faults import injector as _fault_injector  # noqa: F401 — ensure module is loaded


@asynccontextmanager
async def lifespan(app: FastAPI):
    from common.config import get_settings
    s = get_settings()
    app.state.asset_service_url = s.asset_service_url
    app.state.env_service_url = s.env_service_url
    try:
        app.state.redis = aioredis.from_url(s.redis_url)
    except Exception:
        app.state.redis = None
    whatif.init_task_manager(app.state.redis)
    yield
    if app.state.redis:
        await app.state.redis.close()


app = FastAPI(title="Simulation Engine", version="0.1.0", lifespan=lifespan)

app.add_middleware(MetricsMiddleware, service_name="simulation")

app.include_router(simulation.router, prefix="/api/simulation", tags=["Simulation"])
app.include_router(whatif.router, prefix="/api/simulation", tags=["What-If"])
app.include_router(faults.router, prefix="/api/faults", tags=["Faults"])
app.include_router(rl_env.router, prefix="/api/simulation", tags=["RL Environment"])
app.include_router(_calibration.router, prefix="/api/simulation", tags=["Calibration"])


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "simulation"}


@app.get("/metrics")(metrics_endpoint)

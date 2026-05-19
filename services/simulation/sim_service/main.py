from contextlib import asynccontextmanager

import redis.asyncio as aioredis
from fastapi import FastAPI

from .api import simulation, faults


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
    yield
    if app.state.redis:
        await app.state.redis.close()


app = FastAPI(title="Simulation Engine", version="0.1.0", lifespan=lifespan)

app.include_router(simulation.router, prefix="/api/simulation", tags=["Simulation"])
app.include_router(faults.router, prefix="/api/faults", tags=["Faults"])


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "simulation"}

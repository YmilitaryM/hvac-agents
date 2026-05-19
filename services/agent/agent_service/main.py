from contextlib import asynccontextmanager

import redis.asyncio as aioredis
from fastapi import FastAPI

from common.db import create_engine, create_session_factory, Base

from .api import monitoring


@asynccontextmanager
async def lifespan(app: FastAPI):
    from common.config import get_settings
    s = get_settings()
    engine = create_engine(s.database_url)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    app.state.engine = engine
    app.state.session_factory = create_session_factory(engine)
    app.state.sim_service_url = s.sim_service_url
    try:
        app.state.redis = aioredis.from_url(s.redis_url)
    except Exception:
        app.state.redis = None
    yield
    if app.state.redis:
        await app.state.redis.close()
    await engine.dispose()


app = FastAPI(title="Agent Pipeline", version="0.1.0", lifespan=lifespan)

app.include_router(monitoring.router, prefix="/api/monitoring", tags=["Monitoring"])


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "agent"}

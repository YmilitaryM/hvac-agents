from contextlib import asynccontextmanager

from fastapi import FastAPI

from common.config import get_settings
from common.db import create_engine, create_session_factory
from common.metrics import MetricsMiddleware, metrics_endpoint
from .models import Base

from .api import registry, heartbeat, config, ota
# TODO: Wire up remaining API routers once modules are created in future tasks.
# from .api import data


@asynccontextmanager
async def lifespan(app: FastAPI):
    s = get_settings()
    engine = create_engine(s.database_url)
    app.state.engine = engine
    app.state.session_factory = create_session_factory(engine)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield

    await engine.dispose()


app = FastAPI(title="Edge Manager Service", version="0.1.0", lifespan=lifespan)
app.add_middleware(MetricsMiddleware, service_name="edgemanager")

app.include_router(registry.router, prefix="/api/edges", tags=["Registry"])
app.include_router(heartbeat.router, prefix="/api/edges", tags=["Heartbeat"])
app.include_router(config.router, prefix="/api/edges", tags=["Config"])
# TODO: Wire up remaining API routers once modules are created in future tasks.
# app.include_router(data.router, prefix="/api/edges", tags=["Data"])
app.include_router(ota.router, prefix="/api/edges", tags=["OTA"])


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "edgemanager"}


@app.get("/metrics")
async def get_metrics():
    return metrics_endpoint()

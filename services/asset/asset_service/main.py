from contextlib import asynccontextmanager

from fastapi import FastAPI

from common.db import create_engine, create_session_factory, Base
from common.metrics import MetricsMiddleware, metrics_endpoint

from .seed import seed_equipment_types
from .api import equipment, plants, templates, versions


@asynccontextmanager
async def lifespan(app: FastAPI):
    from common.config import get_settings
    engine = create_engine(get_settings().database_url)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    app.state.engine = engine
    app.state.session_factory = create_session_factory(engine)
    await seed_equipment_types(app.state.session_factory)
    yield
    await engine.dispose()


app = FastAPI(title="Asset Service", version="0.1.0", lifespan=lifespan)

app.add_middleware(MetricsMiddleware, service_name="asset")

app.include_router(equipment.router, prefix="/api/equipment", tags=["Equipment"])
app.include_router(plants.router, prefix="/api/plants", tags=["Plants"])
app.include_router(templates.router, prefix="/api/templates", tags=["Templates"])
app.include_router(versions.router, prefix="/api/versions", tags=["Versions"])


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "asset"}


@app.get("/metrics")(metrics_endpoint)

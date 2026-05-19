from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy import text

from common.db import create_engine, create_session_factory, Base

from .api import weather, pricing, buildings


@asynccontextmanager
async def lifespan(app: FastAPI):
    from common.config import get_settings
    engine = create_engine(get_settings().database_url)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # Create TimescaleDB hypertables
        try:
            await conn.execute(text(
                "SELECT create_hypertable('weather_records', 'timestamp', if_not_exists => TRUE)"
            ))
            await conn.execute(text(
                "SELECT create_hypertable('energy_prices', 'timestamp', if_not_exists => TRUE)"
            ))
        except Exception:
            pass  # TimescaleDB may not be available in dev
    app.state.engine = engine
    app.state.session_factory = create_session_factory(engine)
    yield
    await engine.dispose()


app = FastAPI(title="Environment Service", version="0.1.0", lifespan=lifespan)

app.include_router(weather.router, prefix="/api/env", tags=["Weather"])
app.include_router(pricing.router, prefix="/api/env", tags=["Pricing"])
app.include_router(buildings.router, prefix="/api/env", tags=["Buildings"])


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "environment"}

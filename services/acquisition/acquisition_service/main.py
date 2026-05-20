from contextlib import asynccontextmanager
import logging

import redis.asyncio as aioredis
from fastapi import FastAPI

from common.config import get_settings
from common.db import create_engine, create_session_factory, Base
from .models import create_hypertable

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    s = get_settings()
    engine = create_engine(s.database_url)
    app.state.engine = engine
    app.state.session_factory = create_session_factory(engine)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        try:
            await conn.run_sync(create_hypertable)
        except Exception:
            logger.warning("TimescaleDB hypertable creation failed", exc_info=True)

    try:
        app.state.redis = aioredis.from_url(s.redis_url)
    except Exception:
        logger.warning("Redis connection failed", exc_info=True)
        app.state.redis = None

    app.state.asset_service_url = s.asset_service_url

    # Will be added in future tasks:
    # from .poller import PollingEngine
    # app.state.poller = PollingEngine(app.state.session_factory, app.state.redis)
    # await app.state.poller.start()

    yield

    # await app.state.poller.stop()
    if app.state.redis:
        await app.state.redis.close()
    await engine.dispose()


app = FastAPI(title="Data Acquisition Service", version="0.1.0", lifespan=lifespan)

# Will be added in future tasks:
# app.include_router(points.router, prefix="/api/acquisition", tags=["Points"])
# app.include_router(status.router, prefix="/api/acquisition", tags=["Status"])
# app.include_router(commands.router, prefix="/api/acquisition", tags=["Commands"])


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "acquisition"}

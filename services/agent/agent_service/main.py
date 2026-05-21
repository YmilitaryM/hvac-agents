from contextlib import asynccontextmanager

import redis.asyncio as aioredis
from fastapi import FastAPI

from common.db import create_engine, create_session_factory, Base
from common.metrics import MetricsMiddleware, metrics_endpoint

from .api import monitoring, strategies, reports, alerts, prediction, benchmarking, rl, dispatch, carbon as carbon_api
from .predictive_maintenance.api.maintenance import router as maintenance_router
from .workorder.api.workorders import router as workorder_router
from .api import override as _override
from . import models  # ensure models are imported for create_all


@asynccontextmanager
async def lifespan(app: FastAPI):
    from common.config import get_settings
    s = get_settings()
    engine = create_engine(s.database_url)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    app.state.engine = engine
    sf = create_session_factory(engine)
    app.state.session_factory = sf
    app.state.sim_service_url = s.sim_service_url
    try:
        app.state.redis = aioredis.from_url(s.redis_url)
    except Exception:
        app.state.redis = None

    # Initialize simulated carbon market with long-lived session
    from .carbon_repositories import (
        CarbonOrderRepository, CarbonTradeRepository,
        CarbonLedgerRepository, CarbonPriceRepository,
        CarbonHoldingsRepository, CarbonComplianceRepository,
        CarbonAuctionRepository,
    )
    from .carbon.market_adapter.simulated_market import SimulatedMarket

    market_session = sf()
    app.state._carbon_session = market_session
    try:
        app.state.carbon_market = SimulatedMarket(
            CarbonOrderRepository(market_session),
            CarbonTradeRepository(market_session),
            CarbonLedgerRepository(market_session),
            CarbonPriceRepository(market_session),
            CarbonHoldingsRepository(market_session),
            CarbonComplianceRepository(market_session),
            CarbonAuctionRepository(market_session),
        )
    except Exception:
        await market_session.close()
        raise
    yield
    if app.state.redis:
        await app.state.redis.close()
    await market_session.close()
    await engine.dispose()


app = FastAPI(title="Agent Pipeline", version="0.1.0", lifespan=lifespan)

app.add_middleware(MetricsMiddleware, service_name="agent")

app.include_router(monitoring.router, prefix="/api/monitoring", tags=["Monitoring"])
app.include_router(strategies.router, prefix="/api/strategies", tags=["Strategies"])
app.include_router(reports.router, prefix="/api/reports", tags=["Reports"])
app.include_router(alerts.router, prefix="/api/alerts", tags=["Alerts"])
app.include_router(prediction.router, prefix="/api/prediction", tags=["Prediction"])
app.include_router(benchmarking.router, prefix="/api/benchmarking", tags=["Benchmarking"])
app.include_router(rl.router, prefix="/api/rl", tags=["RL"])
app.include_router(dispatch.router, prefix="/api", tags=["Dispatch"])
app.include_router(carbon_api.emissions, prefix="/api/carbon/emissions", tags=["Carbon:Emissions"])
app.include_router(carbon_api.holdings, prefix="/api/carbon/holdings", tags=["Carbon:Holdings"])
app.include_router(carbon_api.trading, prefix="/api/carbon/trading", tags=["Carbon:Trading"])
app.include_router(carbon_api.compliance, prefix="/api/carbon/compliance", tags=["Carbon:Compliance"])
app.include_router(carbon_api.market_api, prefix="/api/carbon/market", tags=["Carbon:Market"])

app.include_router(_override.router, prefix="/api", tags=["Override"])

app.include_router(maintenance_router, prefix="/api/maintenance", tags=["Maintenance"])

app.include_router(workorder_router, prefix="/api/workorders", tags=["WorkOrders"])


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "agent"}


@app.get("/metrics")
async def get_metrics():
    return metrics_endpoint()

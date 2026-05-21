import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from common.db import Base
from services.agent.agent_service.carbon.market_adapter.simulated_market import SimulatedMarket
from services.agent.agent_service.carbon_repositories import (
    CarbonOrderRepository, CarbonTradeRepository,
    CarbonLedgerRepository, CarbonPriceRepository,
    CarbonHoldingsRepository, CarbonComplianceRepository,
    CarbonAuctionRepository,
)


@pytest_asyncio.fixture
async def session():
    engine = create_async_engine("sqlite+aiosqlite://", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as s:
        yield s
    await engine.dispose()


@pytest.mark.asyncio
async def test_place_and_cancel_order(session):
    market = SimulatedMarket(
        CarbonOrderRepository(session), CarbonTradeRepository(session),
        CarbonLedgerRepository(session), CarbonPriceRepository(session),
        CarbonHoldingsRepository(session), CarbonComplianceRepository(session),
        CarbonAuctionRepository(session),
    )
    result = await market.place_order({
        "plant_id": "plant-1", "side": "buy", "allowance_type": "CEA",
        "qty": 100.0, "price": 85.0,
    })
    assert result["order"]["status"] == "pending"
    assert result["order"]["remaining"] == 100.0

    cancelled = await market.cancel_order(result["order"]["id"])
    assert cancelled is True


@pytest.mark.asyncio
async def test_holdings_after_allocation(session):
    market = SimulatedMarket(
        CarbonOrderRepository(session), CarbonTradeRepository(session),
        CarbonLedgerRepository(session), CarbonPriceRepository(session),
        CarbonHoldingsRepository(session), CarbonComplianceRepository(session),
        CarbonAuctionRepository(session),
    )
    await market.receive_allocation("plant-1", "2026", 5000.0)
    h = await market.get_holdings("plant-1", "2026")
    assert h["CEA"] == 5000.0

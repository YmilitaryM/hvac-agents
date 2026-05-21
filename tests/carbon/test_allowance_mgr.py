import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from common.db import Base
from services.agent.agent_service.carbon_repositories import CarbonLedgerRepository
from services.agent.agent_service.carbon.assets.allowance_mgr import AllowanceManager


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
async def test_allocate(session):
    repo = CarbonLedgerRepository(session)
    mgr = AllowanceManager(repo)
    result = await mgr.allocate("plant-1", "2026", 3000.0)
    assert result["allocated"] == 3000.0
    assert result["balance"] == 3000.0


@pytest.mark.asyncio
async def test_transfer(session):
    repo = CarbonLedgerRepository(session)
    mgr = AllowanceManager(repo)
    await mgr.allocate("plant-1", "2026", 5000.0)
    await mgr.allocate("plant-2", "2026", 1000.0)
    result = await mgr.transfer("plant-1", "plant-2", 1000.0, "CEA", "2026")
    assert result["status"] == "completed"

    h1 = await mgr.get_holdings("plant-1", "2026")
    h2 = await mgr.get_holdings("plant-2", "2026")
    assert h1["CEA"] == 4000.0
    assert h2["CEA"] == 2000.0

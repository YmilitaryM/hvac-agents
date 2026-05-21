import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from common.db import Base
from services.agent.agent_service.carbon.emission.factor_registry import FactorRegistry
from services.agent.agent_service.carbon.emission.emission_monitor import EmissionMonitor
from services.agent.agent_service.carbon_repositories import (
    CarbonEmissionRepository, CarbonLedgerRepository,
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
async def test_record_minute_emission(session):
    monitor = EmissionMonitor(
        CarbonEmissionRepository(session),
        CarbonLedgerRepository(session),
        FactorRegistry(),
    )
    record = await monitor.record_minute("plant-1", 850.0, region="east")
    await monitor.emission_repo.commit()
    assert record.tco2 > 0
    assert record.emission_factor == 0.498

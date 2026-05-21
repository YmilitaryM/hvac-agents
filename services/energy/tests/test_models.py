# services/energy/tests/test_models.py
import datetime
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy import select
from energy_service.models import (
    Base, EnergySnapshot, EnergyPrice, EnergyBaseline,
    DemandEvent, EnergyReport, PowerQuality
)

@pytest_asyncio.fixture
async def engine():
    e = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with e.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield e
    await e.dispose()

@pytest_asyncio.fixture
async def session(engine):
    async with AsyncSession(engine) as s:
        yield s

@pytest.mark.asyncio
async def test_energy_snapshot_creation(session):
    snap = EnergySnapshot(
        plant_id=1, total_power_kw=450.0, cop=5.2,
        cooling_load_rt=200.0, outdoor_wb_temp=28.5
    )
    session.add(snap)
    await session.commit()
    result = await session.execute(select(EnergySnapshot).limit(1))
    row = result.scalar_one()
    assert row.total_power_kw == 450.0
    assert row.cop == 5.2

@pytest.mark.asyncio
async def test_energy_baseline_creation(session):
    now = datetime.datetime.now(datetime.timezone.utc)
    bl = EnergyBaseline(
        plant_id=1, period_start=now, period_end=now,
        baseline_kwh_per_rt=0.68, method="regression",
        r_squared=0.82, climate_zone="III", building_type="office"
    )
    session.add(bl)
    await session.commit()
    result = await session.execute(select(EnergyBaseline).limit(1))
    row = result.scalar_one()
    assert row.baseline_kwh_per_rt == 0.68
    assert row.method == "regression"

@pytest.mark.asyncio
async def test_demand_event_creation(session):
    now = datetime.datetime.now(datetime.timezone.utc)
    evt = DemandEvent(
        plant_id=1, start_time=now,
        peak_kw=520.0, target_kw=450.0, strategy="load_shift",
        actual_reduction_kw=65.0
    )
    session.add(evt)
    await session.commit()
    result = await session.execute(select(DemandEvent).limit(1))
    row = result.scalar_one()
    assert row.actual_reduction_kw == 65.0

@pytest.mark.asyncio
async def test_power_quality_creation(session):
    pq = PowerQuality(
        equipment_id=1, thd_v_pct=3.2, thd_i_pct=8.5,
        power_factor=0.93, voltage_unbalance_pct=0.8, frequency_hz=50.02
    )
    session.add(pq)
    await session.commit()
    result = await session.execute(select(PowerQuality).limit(1))
    row = result.scalar_one()
    assert row.power_factor == 0.93

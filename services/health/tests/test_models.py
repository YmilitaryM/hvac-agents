import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy import select
from health_service.models import (
    Base, HealthScore, RULPrediction, FaultDiagnosis,
    FMEARecord, VibrationSpectrum, OilAnalysis, ModelValidation
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
async def test_health_score_creation(session):
    hs = HealthScore(equipment_id=1, overall_score=85.0, component_scores={"compressor": 90, "bearing": 78})
    session.add(hs)
    await session.commit()
    result = await session.execute(select(HealthScore).limit(1))
    row = result.scalar_one()
    assert row.overall_score == 85.0
    assert row.component_scores["bearing"] == 78


@pytest.mark.asyncio
async def test_rul_prediction_creation(session):
    rul = RULPrediction(equipment_id=1, component="compressor", predicted_hours=2000,
                        confidence_interval={"lo": 1500, "hi": 2500}, degradation_model="weibull")
    session.add(rul)
    await session.commit()
    result = await session.execute(select(RULPrediction).limit(1))
    row = result.scalar_one()
    assert row.predicted_hours == 2000


@pytest.mark.asyncio
async def test_fmea_record_creation(session):
    fmea = FMEARecord(equipment_type="centrifugal_chiller", component="compressor",
                       failure_mode="bearing_wear", severity=7, occurrence=4, detection=3, rpn=84)
    session.add(fmea)
    await session.commit()
    result = await session.execute(select(FMEARecord).limit(1))
    row = result.scalar_one()
    assert row.rpn == 84


@pytest.mark.asyncio
async def test_fault_diagnosis_creation(session):
    fd = FaultDiagnosis(equipment_id=1, symptom_signature={"vibration_rms": 7.2, "temp_rise": 15},
                        matched_fmea_id=1, confidence=0.85, root_cause="轴承磨损", severity=3)
    session.add(fd)
    await session.commit()
    result = await session.execute(select(FaultDiagnosis).limit(1))
    row = result.scalar_one()
    assert row.root_cause == "轴承磨损"

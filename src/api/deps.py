"""FastAPI dependency injection for database sessions and repositories."""

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import get_config
from src.db.engine import get_session
from src.db.repositories import (
    AlertRepository,
    EquipmentRepository,
    MemoryRepository,
    PlantRepository,
    ReportRepository,
    RLRepository,
    SnapshotRepository,
    StrategyHistoryRepository,
    StrategyRepository,
)


def use_db() -> bool:
    return get_config().storage.use_db


async def get_db_session() -> AsyncSession:
    async for session in get_session():
        yield session


async def get_snapshot_repo(session: AsyncSession = Depends(get_db_session)) -> SnapshotRepository:
    return SnapshotRepository(session)


async def get_alert_repo(session: AsyncSession = Depends(get_db_session)) -> AlertRepository:
    return AlertRepository(session)


async def get_strategy_repo(
    session: AsyncSession = Depends(get_db_session),
) -> StrategyRepository:
    return StrategyRepository(session)


async def get_strategy_history_repo(
    session: AsyncSession = Depends(get_db_session),
) -> StrategyHistoryRepository:
    return StrategyHistoryRepository(session)


async def get_report_repo(session: AsyncSession = Depends(get_db_session)) -> ReportRepository:
    return ReportRepository(session)


async def get_memory_repo(session: AsyncSession = Depends(get_db_session)) -> MemoryRepository:
    return MemoryRepository(session)


async def get_rl_repo(session: AsyncSession = Depends(get_db_session)) -> RLRepository:
    return RLRepository(session)


async def get_plant_repo(session: AsyncSession = Depends(get_db_session)) -> PlantRepository:
    return PlantRepository(session)


async def get_equipment_repo(session: AsyncSession = Depends(get_db_session)) -> EquipmentRepository:
    return EquipmentRepository(session)

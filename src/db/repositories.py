"""Async repository classes for each entity."""

from typing import Any, Dict, List, Optional

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from .models import (
    AlertModel,
    MemoryLogEntryModel,
    PlantSnapshotModel,
    ReportModel,
    RLTrainingExampleModel,
    RLWeightsModel,
    StrategyHistoryModel,
    StrategyModel,
)


class SnapshotRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, data: dict) -> PlantSnapshotModel:
        obj = PlantSnapshotModel(**data)
        self.session.add(obj)
        await self.session.flush()
        await self.session.commit()
        return obj

    async def get_latest(self) -> Optional[PlantSnapshotModel]:
        result = await self.session.execute(
            select(PlantSnapshotModel)
            .order_by(PlantSnapshotModel.timestamp.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_range(
        self, start_ts: float, end_ts: float, limit: int = 100
    ) -> List[PlantSnapshotModel]:
        result = await self.session.execute(
            select(PlantSnapshotModel)
            .where(PlantSnapshotModel.timestamp >= start_ts)
            .where(PlantSnapshotModel.timestamp <= end_ts)
            .order_by(PlantSnapshotModel.timestamp.asc())
            .limit(limit)
        )
        return list(result.scalars().all())


class AlertRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, data: dict) -> AlertModel:
        obj = AlertModel(**data)
        self.session.add(obj)
        await self.session.flush()
        await self.session.commit()
        return obj

    async def get_recent(self, limit: int = 50) -> List[AlertModel]:
        result = await self.session.execute(
            select(AlertModel)
            .order_by(AlertModel.timestamp.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_by_level(self, level: str, limit: int = 50) -> List[AlertModel]:
        result = await self.session.execute(
            select(AlertModel)
            .where(AlertModel.level == level)
            .order_by(AlertModel.timestamp.desc())
            .limit(limit)
        )
        return list(result.scalars().all())


class StrategyRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, data: dict) -> StrategyModel:
        obj = StrategyModel(**data)
        self.session.add(obj)
        await self.session.flush()
        await self.session.commit()
        return obj

    async def get_by_id(self, strategy_id: str) -> Optional[StrategyModel]:
        result = await self.session.execute(
            select(StrategyModel).where(StrategyModel.strategy_id == strategy_id)
        )
        return result.scalar_one_or_none()

    async def list_all(
        self, status: Optional[str] = None, limit: int = 50
    ) -> List[StrategyModel]:
        stmt = select(StrategyModel).order_by(StrategyModel.created_at.desc())
        if status:
            stmt = stmt.where(StrategyModel.status == status)
        stmt = stmt.limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def update_status(self, strategy_id: str, new_status: str) -> bool:
        obj = await self.get_by_id(strategy_id)
        if obj is None:
            return False
        obj.status = new_status
        await self.session.flush()
        await self.session.commit()
        return True

    async def delete(self, strategy_id: str) -> bool:
        obj = await self.get_by_id(strategy_id)
        if obj is None:
            return False
        await self.session.delete(obj)
        await self.session.flush()
        await self.session.commit()
        return True


class StrategyHistoryRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, data: dict) -> StrategyHistoryModel:
        obj = StrategyHistoryModel(**data)
        self.session.add(obj)
        await self.session.flush()
        await self.session.commit()
        return obj

    async def get_recent(
        self, strategy_id: Optional[str] = None, limit: int = 20
    ) -> List[StrategyHistoryModel]:
        stmt = select(StrategyHistoryModel).order_by(
            StrategyHistoryModel.created_at.desc()
        )
        if strategy_id:
            stmt = stmt.where(StrategyHistoryModel.strategy_id == strategy_id)
        stmt = stmt.limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())


class ReportRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def save(self, data: dict) -> ReportModel:
        date = data.get("date", "")
        period = data.get("period", "daily")
        existing = await self.get_by_date(date, period)
        if existing:
            existing.content = data.get("content")
            existing.format = data.get("format", "json")
            await self.session.flush()
            await self.session.commit()
            return existing
        obj = ReportModel(**data)
        self.session.add(obj)
        await self.session.flush()
        await self.session.commit()
        return obj

    async def get_by_date(self, date: str, period: str = "daily") -> Optional[ReportModel]:
        result = await self.session.execute(
            select(ReportModel)
            .where(ReportModel.date == date)
            .where(ReportModel.period == period)
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def list_dates(self, period: str = "daily") -> List[str]:
        result = await self.session.execute(
            select(ReportModel.date)
            .where(ReportModel.period == period)
            .order_by(ReportModel.date.desc())
        )
        return [row[0] for row in result.all()]


class MemoryRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, data: dict) -> MemoryLogEntryModel:
        obj = MemoryLogEntryModel(**data)
        self.session.add(obj)
        await self.session.flush()
        await self.session.commit()
        return obj

    async def get_recent(self, limit: int = 50) -> List[MemoryLogEntryModel]:
        result = await self.session.execute(
            select(MemoryLogEntryModel)
            .order_by(MemoryLogEntryModel.timestamp.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_successful(self, limit: int = 50) -> List[MemoryLogEntryModel]:
        result = await self.session.execute(
            select(MemoryLogEntryModel)
            .where(MemoryLogEntryModel.safety_passed == True)
            .order_by(MemoryLogEntryModel.timestamp.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_failures(self, limit: int = 50) -> List[MemoryLogEntryModel]:
        result = await self.session.execute(
            select(MemoryLogEntryModel)
            .where(MemoryLogEntryModel.safety_passed == False)
            .order_by(MemoryLogEntryModel.timestamp.desc())
            .limit(limit)
        )
        return list(result.scalars().all())


class RLRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def save_weights(self, action: str, weights: List[float]) -> None:
        existing = await self.session.execute(
            select(RLWeightsModel).where(RLWeightsModel.action == action)
        )
        obj = existing.scalar_one_or_none()
        if obj:
            obj.weights = weights
        else:
            obj = RLWeightsModel(action=action, weights=weights)
            self.session.add(obj)
        await self.session.flush()
        await self.session.commit()

    async def load_weights(self, action: str) -> Optional[List[float]]:
        result = await self.session.execute(
            select(RLWeightsModel).where(RLWeightsModel.action == action)
        )
        obj = result.scalar_one_or_none()
        return obj.weights if obj else None

    async def save_example(
        self, features: List[float], action_taken: str, reward: float
    ) -> RLTrainingExampleModel:
        obj = RLTrainingExampleModel(
            features=features, action_taken=action_taken, reward=reward
        )
        self.session.add(obj)
        await self.session.flush()
        await self.session.commit()
        return obj

    async def get_examples(self, limit: int = 500) -> List[RLTrainingExampleModel]:
        result = await self.session.execute(
            select(RLTrainingExampleModel)
            .order_by(RLTrainingExampleModel.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

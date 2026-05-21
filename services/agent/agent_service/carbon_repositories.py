"""Async repository classes for carbon domain."""
from typing import List, Optional

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from .carbon_models import (
    CarbonLedgerModel, CarbonEmissionModel, CarbonOrderModel,
    CarbonTradeModel, CarbonHoldingsSnapshotModel,
    CarbonComplianceModel, CarbonPriceHistoryModel, CarbonAuctionModel,
)


class CarbonLedgerRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_entry(self, data: dict) -> CarbonLedgerModel:
        obj = CarbonLedgerModel(**data)
        self.session.add(obj)
        await self.session.flush()
        return obj

    async def get_balance(
        self, plant_id: str, allowance_type: str, period: str
    ) -> float:
        result = await self.session.execute(
            select(CarbonLedgerModel)
            .where(CarbonLedgerModel.plant_id == plant_id)
            .where(CarbonLedgerModel.allowance_type == allowance_type)
            .where(CarbonLedgerModel.period == period)
            .order_by(CarbonLedgerModel.created_at.desc())
            .limit(1)
        )
        last = result.scalar_one_or_none()
        return last.balance_after if last else 0.0

    async def get_entries(
        self, plant_id: str, period: Optional[str] = None,
        entry_type: Optional[str] = None, limit: int = 50, offset: int = 0,
    ) -> List[CarbonLedgerModel]:
        stmt = select(CarbonLedgerModel).where(
            CarbonLedgerModel.plant_id == plant_id
        )
        if period:
            stmt = stmt.where(CarbonLedgerModel.period == period)
        if entry_type:
            stmt = stmt.where(CarbonLedgerModel.entry_type == entry_type)
        stmt = stmt.order_by(CarbonLedgerModel.created_at.desc()).limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def commit(self):
        await self.session.commit()


class CarbonEmissionRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def insert(self, data: dict) -> CarbonEmissionModel:
        data.setdefault("source", "grid")
        obj = CarbonEmissionModel(**data)
        self.session.add(obj)
        await self.session.flush()
        return obj

    async def get_range(
        self, plant_id: str, from_ts: float, to_ts: float, limit: int = 1440
    ) -> List[CarbonEmissionModel]:
        result = await self.session.execute(
            select(CarbonEmissionModel)
            .where(CarbonEmissionModel.plant_id == plant_id)
            .where(CarbonEmissionModel.timestamp >= from_ts)
            .where(CarbonEmissionModel.timestamp <= to_ts)
            .order_by(CarbonEmissionModel.timestamp.asc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_summary(
        self, plant_id: str, from_ts: float, to_ts: float
    ) -> dict:
        result = await self.session.execute(
            select(
                func.sum(CarbonEmissionModel.tco2).label("total_tco2"),
                func.avg(CarbonEmissionModel.power_kw).label("avg_power_kw"),
                func.max(CarbonEmissionModel.tco2).label("peak_tco2"),
            )
            .where(CarbonEmissionModel.plant_id == plant_id)
            .where(CarbonEmissionModel.timestamp >= from_ts)
            .where(CarbonEmissionModel.timestamp <= to_ts)
        )
        row = result.one()
        return {
            "total_tco2": row.total_tco2 or 0.0,
            "avg_power_kw": row.avg_power_kw or 0.0,
            "peak_tco2": row.peak_tco2 or 0.0,
        }

    async def commit(self):
        await self.session.commit()


class CarbonOrderRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, data: dict) -> CarbonOrderModel:
        data.setdefault("status", "pending")
        data.setdefault("order_type", "limit")
        obj = CarbonOrderModel(**data)
        self.session.add(obj)
        await self.session.flush()
        return obj

    async def get_by_id(self, order_id: str) -> Optional[CarbonOrderModel]:
        result = await self.session.execute(
            select(CarbonOrderModel).where(CarbonOrderModel.id == order_id)
        )
        return result.scalar_one_or_none()

    async def get_open_orders(
        self, plant_id: Optional[str] = None, allowance_type: Optional[str] = None,
        side: Optional[str] = None, status: Optional[str] = None,
    ) -> List[CarbonOrderModel]:
        if status:
            stmt = select(CarbonOrderModel).where(CarbonOrderModel.status == status)
        else:
            stmt = select(CarbonOrderModel).where(
                CarbonOrderModel.status.in_(["pending", "partial_fill"])
            )
        if plant_id:
            stmt = stmt.where(CarbonOrderModel.plant_id == plant_id)
        if allowance_type:
            stmt = stmt.where(CarbonOrderModel.allowance_type == allowance_type)
        if side:
            stmt = stmt.where(CarbonOrderModel.side == side)
        stmt = stmt.order_by(CarbonOrderModel.created_at.asc())
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def update_remaining(
        self, order_id: str, new_remaining: float, new_status: str
    ) -> bool:
        obj = await self.get_by_id(order_id)
        if not obj:
            return False
        obj.remaining = new_remaining
        obj.status = new_status
        return True

    async def commit(self):
        await self.session.commit()


class CarbonTradeRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, data: dict) -> CarbonTradeModel:
        data.setdefault("settlement_status", "settled")
        obj = CarbonTradeModel(**data)
        self.session.add(obj)
        await self.session.flush()
        return obj

    async def get_by_plant(
        self, plant_id: str, from_ts: Optional[float] = None,
        to_ts: Optional[float] = None, limit: int = 50,
    ) -> List[CarbonTradeModel]:
        stmt = select(CarbonTradeModel).where(
            (CarbonTradeModel.buy_plant_id == plant_id)
            | (CarbonTradeModel.sell_plant_id == plant_id)
        )
        if from_ts:
            stmt = stmt.where(CarbonTradeModel.created_at >= from_ts)
        if to_ts:
            stmt = stmt.where(CarbonTradeModel.created_at <= to_ts)
        stmt = stmt.order_by(CarbonTradeModel.created_at.desc()).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def commit(self):
        await self.session.commit()


class CarbonHoldingsRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def upsert_snapshot(self, data: dict) -> CarbonHoldingsSnapshotModel:
        existing = await self.session.execute(
            select(CarbonHoldingsSnapshotModel).where(
                and_(
                    CarbonHoldingsSnapshotModel.plant_id == data["plant_id"],
                    CarbonHoldingsSnapshotModel.period == data["period"],
                    CarbonHoldingsSnapshotModel.allowance_type == data["allowance_type"],
                )
            )
        )
        obj = existing.scalar_one_or_none()
        if obj:
            for k, v in data.items():
                setattr(obj, k, v)
        else:
            obj = CarbonHoldingsSnapshotModel(**data)
            self.session.add(obj)
        await self.session.flush()
        return obj

    async def get_holdings(
        self, plant_id: str, period: str
    ) -> List[CarbonHoldingsSnapshotModel]:
        result = await self.session.execute(
            select(CarbonHoldingsSnapshotModel).where(
                CarbonHoldingsSnapshotModel.plant_id == plant_id,
                CarbonHoldingsSnapshotModel.period == period,
            )
        )
        return list(result.scalars().all())

    async def commit(self):
        await self.session.commit()


class CarbonComplianceRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def upsert(self, data: dict) -> CarbonComplianceModel:
        existing = await self.session.execute(
            select(CarbonComplianceModel).where(
                CarbonComplianceModel.plant_id == data["plant_id"],
                CarbonComplianceModel.period == data["period"],
            )
        )
        obj = existing.scalar_one_or_none()
        if obj:
            for k, v in data.items():
                setattr(obj, k, v)
        else:
            obj = CarbonComplianceModel(**data)
            self.session.add(obj)
        await self.session.flush()
        return obj

    async def get_by_plant_period(
        self, plant_id: str, period: str
    ) -> Optional[CarbonComplianceModel]:
        result = await self.session.execute(
            select(CarbonComplianceModel).where(
                CarbonComplianceModel.plant_id == plant_id,
                CarbonComplianceModel.period == period,
            )
        )
        return result.scalar_one_or_none()

    async def commit(self):
        await self.session.commit()


class CarbonPriceRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def insert(self, data: dict) -> CarbonPriceHistoryModel:
        obj = CarbonPriceHistoryModel(**data)
        self.session.add(obj)
        await self.session.flush()
        return obj

    async def get_ohlcv(
        self, allowance_type: str, interval: str,
        from_ts: float, to_ts: float, limit: int = 200,
    ) -> List[CarbonPriceHistoryModel]:
        result = await self.session.execute(
            select(CarbonPriceHistoryModel)
            .where(CarbonPriceHistoryModel.allowance_type == allowance_type)
            .where(CarbonPriceHistoryModel.interval == interval)
            .where(CarbonPriceHistoryModel.timestamp >= from_ts)
            .where(CarbonPriceHistoryModel.timestamp <= to_ts)
            .order_by(CarbonPriceHistoryModel.timestamp.asc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_latest_price(self, allowance_type: str) -> Optional[float]:
        result = await self.session.execute(
            select(CarbonPriceHistoryModel.close)
            .where(CarbonPriceHistoryModel.allowance_type == allowance_type)
            .where(CarbonPriceHistoryModel.interval == "1m")
            .order_by(CarbonPriceHistoryModel.timestamp.desc())
            .limit(1)
        )
        row = result.scalar_one_or_none()
        return row if row else None

    async def commit(self):
        await self.session.commit()


class CarbonAuctionRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, data: dict) -> CarbonAuctionModel:
        obj = CarbonAuctionModel(**data)
        self.session.add(obj)
        await self.session.flush()
        return obj

    async def get_by_period(self, period: str) -> List[CarbonAuctionModel]:
        result = await self.session.execute(
            select(CarbonAuctionModel)
            .where(CarbonAuctionModel.period == period)
            .order_by(CarbonAuctionModel.bid_start.asc())
        )
        return list(result.scalars().all())

    async def update_clearing(self, auction_id: str, clearing_price: float, winners: dict) -> bool:
        obj = await self.session.execute(
            select(CarbonAuctionModel).where(CarbonAuctionModel.id == auction_id)
        )
        auction = obj.scalar_one_or_none()
        if not auction:
            return False
        auction.clearing_price = clearing_price
        auction.winners = winners
        auction.status = "cleared"
        return True

    async def commit(self):
        await self.session.commit()

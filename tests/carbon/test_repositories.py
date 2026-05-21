import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from common.db import Base
from services.agent.agent_service.carbon_models import (
    CarbonLedgerModel, CarbonEmissionModel, CarbonOrderModel,
    CarbonTradeModel, CarbonHoldingsSnapshotModel,
    CarbonComplianceModel, CarbonPriceHistoryModel, CarbonAuctionModel,
)
from services.agent.agent_service.carbon_repositories import (
    CarbonLedgerRepository, CarbonEmissionRepository,
    CarbonOrderRepository, CarbonTradeRepository,
    CarbonHoldingsRepository, CarbonComplianceRepository,
    CarbonPriceRepository, CarbonAuctionRepository,
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
async def test_ledger_create_and_get_balance(session):
    repo = CarbonLedgerRepository(session)
    await repo.create_entry({
        "plant_id": "plant-1", "period": "2026", "entry_type": "allocation",
        "direction": "credit", "allowance_type": "CEA", "qty_tco2": 1000.0,
        "balance_after": 1000.0,
    })
    await repo.create_entry({
        "plant_id": "plant-1", "period": "2026", "entry_type": "emission",
        "direction": "debit", "allowance_type": "CEA", "qty_tco2": 50.0,
        "balance_after": 950.0,
    })
    await repo.commit()
    balance = await repo.get_balance("plant-1", "CEA", "2026")
    assert balance == 950.0

    entries = await repo.get_entries("plant-1", period="2026")
    assert len(entries) == 2


@pytest.mark.asyncio
async def test_order_create_and_update(session):
    repo = CarbonOrderRepository(session)
    order = await repo.create({
        "plant_id": "plant-1", "side": "sell", "allowance_type": "CEA",
        "order_type": "limit", "qty": 200.0, "remaining": 200.0, "price": 85.0,
    })
    assert order.id is not None
    await repo.commit()

    await repo.update_remaining(order.id, 100.0, "partial_fill")
    await repo.commit()

    updated = await repo.get_by_id(order.id)
    assert updated.remaining == 100.0
    assert updated.status == "partial_fill"


@pytest.mark.asyncio
async def test_emission_insert_and_summary(session):
    repo = CarbonEmissionRepository(session)
    await repo.insert({
        "plant_id": "plant-1", "timestamp": 100.0, "power_kw": 500.0,
        "tco2": 0.25, "period_tag": "2026",
    })
    await repo.insert({
        "plant_id": "plant-1", "timestamp": 160.0, "power_kw": 700.0,
        "tco2": 0.35, "period_tag": "2026",
    })
    await repo.commit()

    summary = await repo.get_summary("plant-1", 0.0, 200.0)
    assert summary["total_tco2"] == 0.60
    assert summary["avg_power_kw"] == 600.0
    assert summary["peak_tco2"] == 0.35


@pytest.mark.asyncio
async def test_trade_create_and_query(session):
    repo = CarbonTradeRepository(session)
    await repo.create({
        "buy_order_id": "ord-1", "sell_order_id": "ord-2",
        "buy_plant_id": "plant-1", "sell_plant_id": "plant-2",
        "allowance_type": "CEA", "qty_tco2": 100.0, "price": 82.5,
        "total_value": 8250.0, "fee": 8.25,
    })
    await repo.commit()

    trades = await repo.get_by_plant("plant-1")
    assert len(trades) == 1
    assert trades[0].qty_tco2 == 100.0


@pytest.mark.asyncio
async def test_holdings_upsert_and_get(session):
    repo = CarbonHoldingsRepository(session)
    snap = await repo.upsert_snapshot({
        "plant_id": "plant-1", "period": "2026", "allowance_type": "CEA",
        "total_held": 3000.0, "used": 800.0, "available": 2000.0, "locked": 200.0,
    })
    await repo.commit()
    assert snap.total_held == 3000.0

    holdings = await repo.get_holdings("plant-1", "2026")
    assert len(holdings) == 1
    assert holdings[0].available == 2000.0


@pytest.mark.asyncio
async def test_compliance_upsert(session):
    repo = CarbonComplianceRepository(session)
    comp = await repo.upsert({
        "plant_id": "plant-1", "period": "2026",
        "required_surrender": 1000.0, "actual_surrender": 500.0,
        "deficit": 500.0, "status": "partial",
    })
    await repo.commit()
    assert comp.status == "partial"

    found = await repo.get_by_plant_period("plant-1", "2026")
    assert found is not None
    assert found.deficit == 500.0


@pytest.mark.asyncio
async def test_price_insert_and_latest(session):
    repo = CarbonPriceRepository(session)
    await repo.insert({
        "allowance_type": "CEA", "interval": "1m",
        "open": 82.0, "high": 83.0, "low": 81.0, "close": 82.5,
        "volume": 100.0, "timestamp": 1000.0,
    })
    await repo.insert({
        "allowance_type": "CEA", "interval": "1m",
        "open": 82.5, "high": 84.0, "low": 82.0, "close": 83.0,
        "volume": 150.0, "timestamp": 1060.0,
    })
    await repo.commit()

    latest = await repo.get_latest_price("CEA")
    assert latest == 83.0

    ohlcv = await repo.get_ohlcv("CEA", "1m", 0.0, 2000.0)
    assert len(ohlcv) == 2


@pytest.mark.asyncio
async def test_auction_create_and_update(session):
    from datetime import datetime, timezone, timedelta
    repo = CarbonAuctionRepository(session)
    auction = await repo.create({
        "period": "2026", "auction_type": "CEA", "total_qty": 5000.0,
        "floor_price": 70.0,
        "bid_start": datetime.now(timezone.utc),
        "bid_end": datetime.now(timezone.utc) + timedelta(days=3),
        "status": "upcoming",
    })
    await repo.commit()
    assert auction.floor_price == 70.0

    success = await repo.update_clearing(auction.id, 75.0, {"plant-1": 2000})
    await repo.commit()
    assert success

    by_period = await repo.get_by_period("2026")
    assert len(by_period) == 1
    assert by_period[0].status == "cleared"

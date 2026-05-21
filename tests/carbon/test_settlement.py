import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from common.db import Base
from services.agent.agent_service.carbon.trading.matching_engine import (
    MatchingEngine, Match,
)
from services.agent.agent_service.carbon.trading.settlement import SettlementEngine
from services.agent.agent_service.carbon_repositories import (
    CarbonTradeRepository, CarbonLedgerRepository, CarbonOrderRepository,
)
from services.agent.agent_service.carbon_models import CarbonOrderModel


def _make_order(id, plant_id, side, price, qty):
    return CarbonOrderModel(
        id=id, plant_id=plant_id, side=side, allowance_type="CEA",
        order_type="limit", qty=qty, remaining=qty, price=price,
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
async def test_settle_trade(session):
    trade_repo = CarbonTradeRepository(session)
    ledger_repo = CarbonLedgerRepository(session)
    order_repo = CarbonOrderRepository(session)

    # Setup initial balances
    await ledger_repo.create_entry({
        "plant_id": "plant-1", "period": "2026", "entry_type": "allocation",
        "direction": "credit", "allowance_type": "CEA", "qty_tco2": 5000.0, "balance_after": 5000.0,
    })
    await ledger_repo.create_entry({
        "plant_id": "plant-2", "period": "2026", "entry_type": "allocation",
        "direction": "credit", "allowance_type": "CEA", "qty_tco2": 1000.0, "balance_after": 1000.0,
    })

    buy = _make_order("b1", "plant-1", "buy", 85.0, 100.0)
    buy.remaining = 0.0
    buy.status = "filled"
    sell = _make_order("s1", "plant-2", "sell", 85.0, 100.0)
    sell.remaining = 0.0
    sell.status = "filled"

    settlement = SettlementEngine(trade_repo, ledger_repo, order_repo)
    trades = await settlement.settle([Match(buy, sell, 100.0, 85.0)])

    assert len(trades) == 1
    assert trades[0]["price"] == 85.0
    assert trades[0]["total"] == 8500.0

    # Check ledger
    b1_bal = await ledger_repo.get_balance("plant-1", "CEA", "2026")
    b2_bal = await ledger_repo.get_balance("plant-2", "CEA", "2026")
    assert b1_bal == 5100.0  # bought 100
    assert b2_bal == 900.0   # sold 100

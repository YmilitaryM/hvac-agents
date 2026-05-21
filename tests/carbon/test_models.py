import pytest
from services.agent.agent_service.carbon_models import (
    CarbonLedgerModel,
    CarbonEmissionModel,
    CarbonOrderModel,
    CarbonTradeModel,
    CarbonHoldingsSnapshotModel,
    CarbonComplianceModel,
    CarbonPriceHistoryModel,
    CarbonAuctionModel,
)


def test_carbon_ledger_credit_allocation():
    entry = CarbonLedgerModel(
        plant_id="plant-1",
        period="2026",
        entry_type="allocation",
        direction="credit",
        allowance_type="CEA",
        qty_tco2=1000.0,
        unit_price=0.0,
        balance_after=5000.0,
    )
    assert entry.plant_id == "plant-1"
    assert entry.entry_type == "allocation"
    assert entry.direction == "credit"
    assert entry.balance_after == 5000.0


def test_carbon_ledger_debit_emission():
    entry = CarbonLedgerModel(
        plant_id="plant-1",
        period="2026",
        entry_type="emission",
        direction="debit",
        allowance_type="CEA",
        qty_tco2=0.42,
        unit_price=80.0,
        balance_after=4999.58,
    )
    assert entry.direction == "debit"
    assert entry.qty_tco2 == 0.42


def test_carbon_emission_record():
    record = CarbonEmissionModel(
        plant_id="plant-1",
        timestamp=1716300000.0,
        power_kw=850.0,
        emission_factor=0.50,
        tco2=0.425,
        period_tag="2026",
        source="grid",
    )
    assert record.tco2 == 0.425
    assert record.source == "grid"


def test_order_lifecycle():
    order = CarbonOrderModel(
        plant_id="plant-1", side="sell", allowance_type="CEA",
        order_type="limit", qty=200.0, remaining=200.0, price=85.0,
        status="pending",
    )
    assert order.status == "pending"
    order.remaining = 100.0
    order.status = "partial_fill"
    assert order.remaining == 100.0
    order.remaining = 0.0
    order.status = "filled"
    assert order.status == "filled"


def test_trade_settlement():
    trade = CarbonTradeModel(
        buy_order_id="ord-1", sell_order_id="ord-2",
        buy_plant_id="plant-1", sell_plant_id="plant-2",
        allowance_type="CEA", qty_tco2=100.0, price=82.5,
        total_value=8250.0, fee=8.25,
        settlement_status="settled",
    )
    assert trade.settlement_status == "settled"
    assert trade.total_value == 8250.0


def test_holdings_snapshot_unique():
    s1 = CarbonHoldingsSnapshotModel(
        plant_id="plant-1", period="2026", allowance_type="CEA",
        total_held=3000.0, used=800.0, available=2000.0, locked=200.0,
    )
    assert s1.available == 2000.0
    assert s1.locked == 200.0


def test_compliance_status():
    c = CarbonComplianceModel(
        plant_id="plant-1", period="2026",
        required_surrender=1000.0, actual_surrender=680.0,
        deficit=320.0, status="partial",
    )
    assert c.deficit == 320.0
    assert c.status == "partial"


def test_price_history_ohlcv():
    bar = CarbonPriceHistoryModel(
        allowance_type="CEA", interval="1h",
        open=82.0, high=85.5, low=81.0, close=84.2,
        volume=500.0, timestamp=1716300000.0,
    )
    assert bar.high >= bar.low
    assert bar.volume == 500.0


def test_auction_upcoming():
    from datetime import datetime, timezone, timedelta
    a = CarbonAuctionModel(
        period="2026", auction_type="CEA", total_qty=5000.0,
        floor_price=70.0,
        bid_start=datetime.now(timezone.utc),
        bid_end=datetime.now(timezone.utc) + timedelta(days=3),
        status="upcoming",
    )
    assert a.floor_price == 70.0
    assert a.status == "upcoming"

"""Carbon domain SQLAlchemy ORM models."""
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import JSON, Boolean, DateTime, Float, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from common.db import Base


def _new_id() -> str:
    return uuid.uuid4().hex[:16]


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class CarbonLedgerModel(Base):
    """Double-entry ledger for all allowance movements."""
    __tablename__ = "carbon_ledger"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_new_id)
    plant_id: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    period: Mapped[str] = mapped_column(String(10), index=True, nullable=False)
    entry_type: Mapped[str] = mapped_column(String(32), nullable=False)
    direction: Mapped[str] = mapped_column(String(10), nullable=False)  # debit | credit
    allowance_type: Mapped[str] = mapped_column(String(10), nullable=False)  # CEA | CCER
    qty_tco2: Mapped[float] = mapped_column(Float, nullable=False)
    unit_price: Mapped[float] = mapped_column(Float, default=0.0)
    balance_after: Mapped[float] = mapped_column(Float, nullable=False)
    trade_id: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    emission_id: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    compliance_id: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    note: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    __table_args__ = (
        Index("ix_ledger_plant_period", "plant_id", "period"),
        Index("ix_ledger_plant_type", "plant_id", "allowance_type"),
        Index("ix_ledger_entry_type", "entry_type", "created_at"),
    )


class CarbonEmissionModel(Base):
    """Minute-level emission records (TimescaleDB hypertable preferred)."""
    __tablename__ = "carbon_emissions"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_new_id)
    plant_id: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    timestamp: Mapped[float] = mapped_column(Float, index=True, nullable=False)
    power_kw: Mapped[float] = mapped_column(Float, default=0.0)
    emission_factor: Mapped[float] = mapped_column(Float, default=0.50)
    tco2: Mapped[float] = mapped_column(Float, default=0.0)
    cooling_gj: Mapped[float] = mapped_column(Float, default=0.0)
    source: Mapped[str] = mapped_column(String(20), default="grid")
    period_tag: Mapped[str] = mapped_column(String(10), default="")
    chiller_id: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    __table_args__ = (
        Index("ix_emission_plant_ts", "plant_id", "timestamp"),
        Index("ix_emission_period", "period_tag", "timestamp"),
    )


class CarbonOrderModel(Base):
    """Order book entries for continuous auction."""
    __tablename__ = "carbon_orders"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_new_id)
    plant_id: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    side: Mapped[str] = mapped_column(String(10), nullable=False)  # buy | sell
    allowance_type: Mapped[str] = mapped_column(String(10), nullable=False)  # CEA | CCER
    order_type: Mapped[str] = mapped_column(String(16), default="limit")  # market | limit | iceberg
    qty: Mapped[float] = mapped_column(Float, nullable=False)
    remaining: Mapped[float] = mapped_column(Float, nullable=False)
    price: Mapped[float] = mapped_column(Float, nullable=False)
    peak_qty: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(String(20), index=True, default="pending")
    expire_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    __table_args__ = (
        Index("ix_orders_status_created", "status", "created_at"),
        Index("ix_orders_plant_side_type", "plant_id", "side", "allowance_type", "status"),
    )


class CarbonTradeModel(Base):
    """Completed trades (T+0 settlement)."""
    __tablename__ = "carbon_trades"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_new_id)
    buy_order_id: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    sell_order_id: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    buy_plant_id: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    sell_plant_id: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    allowance_type: Mapped[str] = mapped_column(String(10), nullable=False)
    qty_tco2: Mapped[float] = mapped_column(Float, nullable=False)
    price: Mapped[float] = mapped_column(Float, nullable=False)
    total_value: Mapped[float] = mapped_column(Float, nullable=False)
    fee: Mapped[float] = mapped_column(Float, default=0.0)
    settlement_status: Mapped[str] = mapped_column(String(20), default="settled")
    settled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    __table_args__ = (
        Index("ix_trades_buy_plant", "buy_plant_id", "created_at"),
        Index("ix_trades_sell_plant", "sell_plant_id", "created_at"),
    )


class CarbonHoldingsSnapshotModel(Base):
    """Daily holdings snapshot for fast queries."""
    __tablename__ = "carbon_holdings_snapshot"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_new_id)
    plant_id: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    period: Mapped[str] = mapped_column(String(10), nullable=False)
    allowance_type: Mapped[str] = mapped_column(String(10), nullable=False)
    total_held: Mapped[float] = mapped_column(Float, default=0.0)
    used: Mapped[float] = mapped_column(Float, default=0.0)
    available: Mapped[float] = mapped_column(Float, default=0.0)
    locked: Mapped[float] = mapped_column(Float, default=0.0)
    snapshot_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    __table_args__ = (
        Index("ix_holdings_plant_period_type", "plant_id", "period", "allowance_type", unique=True),
    )


class CarbonComplianceModel(Base):
    """Annual compliance / surrender records."""
    __tablename__ = "carbon_compliance"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_new_id)
    plant_id: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    period: Mapped[str] = mapped_column(String(10), nullable=False)
    required_surrender: Mapped[float] = mapped_column(Float, nullable=False)
    actual_surrender: Mapped[float] = mapped_column(Float, default=0.0)
    ccer_used: Mapped[float] = mapped_column(Float, default=0.0)
    deficit: Mapped[float] = mapped_column(Float, default=0.0)
    penalty_yuan: Mapped[float] = mapped_column(Float, default=0.0)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    __table_args__ = (
        Index("ix_compliance_plant_period", "plant_id", "period", unique=True),
    )


class CarbonPriceHistoryModel(Base):
    """OHLCV price history."""
    __tablename__ = "carbon_price_history"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_new_id)
    allowance_type: Mapped[str] = mapped_column(String(10), nullable=False)
    interval: Mapped[str] = mapped_column(String(10), nullable=False)  # 1m | 5m | 15m | 1h | 1d
    open: Mapped[float] = mapped_column(Float, nullable=False)
    high: Mapped[float] = mapped_column(Float, nullable=False)
    low: Mapped[float] = mapped_column(Float, nullable=False)
    close: Mapped[float] = mapped_column(Float, nullable=False)
    volume: Mapped[float] = mapped_column(Float, default=0.0)
    timestamp: Mapped[float] = mapped_column(Float, index=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    __table_args__ = (
        Index("ix_price_type_interval_ts", "allowance_type", "interval", "timestamp"),
    )


class CarbonAuctionModel(Base):
    """Allowance auction records."""
    __tablename__ = "carbon_auctions"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_new_id)
    period: Mapped[str] = mapped_column(String(10), nullable=False)
    auction_type: Mapped[str] = mapped_column(String(20), nullable=False)  # CEA | CCER
    total_qty: Mapped[float] = mapped_column(Float, nullable=False)
    floor_price: Mapped[float] = mapped_column(Float, nullable=False)
    clearing_price: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    bid_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    bid_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="upcoming")
    winners: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

"""SQLAlchemy ORM models for the HVAC chiller plant system."""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import JSON, Boolean, DateTime, Float, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


def _new_id() -> str:
    return uuid.uuid4().hex[:16]


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class PlantSnapshotModel(Base):
    __tablename__ = "plant_snapshots"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_new_id)
    timestamp: Mapped[float] = mapped_column(Float, index=True, nullable=False)
    total_cooling_load_rt: Mapped[float] = mapped_column(Float, default=0.0)
    total_power_kw: Mapped[float] = mapped_column(Float, default=0.0)
    system_cop: Mapped[float] = mapped_column(Float, default=0.0)
    outdoor_wb_temp: Mapped[float] = mapped_column(Float, default=0.0)
    outdoor_db_temp: Mapped[float] = mapped_column(Float, default=0.0)
    chiller_data: Mapped[Optional[Dict]] = mapped_column(JSON, nullable=True)
    pump_data: Mapped[Optional[Dict]] = mapped_column(JSON, nullable=True)
    tower_data: Mapped[Optional[Dict]] = mapped_column(JSON, nullable=True)
    raw_snapshot: Mapped[Optional[Dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    __table_args__ = (
        Index("ix_plant_snapshots_ts_created", "timestamp", "created_at"),
    )


class AlertModel(Base):
    __tablename__ = "alerts"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_new_id)
    timestamp: Mapped[float] = mapped_column(Float, index=True, nullable=False)
    level: Mapped[str] = mapped_column(String(20), nullable=False)  # info, warning, critical
    device: Mapped[str] = mapped_column(String(50), default="")
    message: Mapped[str] = mapped_column(Text, default="")
    acknowledged: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    __table_args__ = (
        Index("ix_alerts_level_ts", "level", "timestamp"),
    )


class StrategyModel(Base):
    __tablename__ = "strategies"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_new_id)
    strategy_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    trigger_type: Mapped[str] = mapped_column(String(32), default="scheduled")
    trigger_time: Mapped[float] = mapped_column(Float, default=0.0)
    current_load_rt: Mapped[float] = mapped_column(Float, default=0.0)
    predicted_load_rt: Mapped[float] = mapped_column(Float, default=0.0)
    outdoor_wb_temp: Mapped[float] = mapped_column(Float, default=0.0)
    electricity_price: Mapped[float] = mapped_column(Float, default=0.0)
    carbon_intensity: Mapped[float] = mapped_column(Float, default=0.0)
    actions: Mapped[Optional[List]] = mapped_column(JSON, nullable=True)
    transition_plan: Mapped[Optional[Dict]] = mapped_column(JSON, nullable=True)
    expected_cop_improvement: Mapped[float] = mapped_column(Float, default=0.0)
    expected_energy_saving_kwh_per_h: Mapped[float] = mapped_column(Float, default=0.0)
    status: Mapped[str] = mapped_column(String(32), index=True, default="draft")
    raw_strategy: Mapped[Optional[Dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    __table_args__ = (
        Index("ix_strategies_status_created", "status", "created_at"),
    )


class StrategyHistoryModel(Base):
    __tablename__ = "strategy_history"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_new_id)
    strategy_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    timestamp: Mapped[float] = mapped_column(Float, default=0.0)
    details: Mapped[Optional[Dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class ReportModel(Base):
    __tablename__ = "reports"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_new_id)
    date: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    period: Mapped[str] = mapped_column(String(16), default="daily")  # daily or monthly
    content: Mapped[Optional[Dict]] = mapped_column(JSON, nullable=True)
    format: Mapped[str] = mapped_column(String(16), default="json")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    __table_args__ = (
        Index("ix_reports_date_period", "date", "period"),
    )


class MemoryLogEntryModel(Base):
    __tablename__ = "memory_log"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_new_id)
    timestamp: Mapped[float] = mapped_column(Float, index=True, nullable=False)
    strategy_id: Mapped[str] = mapped_column(String(64), default="")
    trigger_type: Mapped[str] = mapped_column(String(32), default="scheduled")
    current_load_rt: Mapped[float] = mapped_column(Float, default=0.0)
    predicted_load_rt: Mapped[float] = mapped_column(Float, default=0.0)
    cop_improvement: Mapped[float] = mapped_column(Float, default=0.0)
    energy_saving_kwh: Mapped[float] = mapped_column(Float, default=0.0)
    execution_status: Mapped[str] = mapped_column(String(32), index=True, default="pending")
    safety_passed: Mapped[bool] = mapped_column(Boolean, default=False)
    extra: Mapped[Optional[Dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class RLWeightsModel(Base):
    __tablename__ = "rl_weights"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_new_id)
    action: Mapped[str] = mapped_column(String(16), nullable=False)  # approve or reject
    weights: Mapped[List] = mapped_column(JSON, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    __table_args__ = (
        Index("ix_rl_weights_action", "action", unique=True),
    )


class RLTrainingExampleModel(Base):
    __tablename__ = "rl_training_examples"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_new_id)
    features: Mapped[List] = mapped_column(JSON, nullable=False)
    action_taken: Mapped[str] = mapped_column(String(16), nullable=False)
    reward: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import String, Float, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from common.db import Base


class EdgeDevice(Base):
    __tablename__ = "edge_devices"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    plant_id: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    mode: Mapped[str] = mapped_column(String(16), default="hybrid")
    version: Mapped[str] = mapped_column(String(32), nullable=False)
    config_hash: Mapped[Optional[str]] = mapped_column(String(64))
    registered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    last_seen_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))


class Heartbeat(Base):
    __tablename__ = "heartbeats"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    edge_id: Mapped[str] = mapped_column(String(32), ForeignKey("edge_devices.id"), nullable=False)
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    cpu_pct: Mapped[Optional[float]] = mapped_column(Float)
    mem_mb: Mapped[Optional[float]] = mapped_column(Float)
    disk_pct: Mapped[Optional[float]] = mapped_column(Float)
    collector_ok: Mapped[Optional[bool]] = mapped_column(Boolean)
    controller_ok: Mapped[Optional[bool]] = mapped_column(Boolean)
    inspector_ok: Mapped[Optional[bool]] = mapped_column(Boolean)


class OTATask(Base):
    __tablename__ = "ota_tasks"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    edge_id: Mapped[str] = mapped_column(String(32), ForeignKey("edge_devices.id"), nullable=False)
    target_type: Mapped[str] = mapped_column(String(16), nullable=False)
    version: Mapped[str] = mapped_column(String(32), nullable=False)
    payload_url: Mapped[str] = mapped_column(String(512), nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="pending")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))


class SyncWatermark(Base):
    __tablename__ = "sync_watermarks"

    edge_id: Mapped[str] = mapped_column(String(32), ForeignKey("edge_devices.id"), primary_key=True)
    table_name: Mapped[str] = mapped_column(String(64), primary_key=True)
    last_synced_until: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

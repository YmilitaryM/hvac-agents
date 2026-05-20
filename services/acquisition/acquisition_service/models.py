from datetime import datetime, timezone

from sqlalchemy import String, Float, DateTime, Index, text
from sqlalchemy.orm import Mapped, mapped_column

from common.db import Base


class EquipmentReading(Base):
    __tablename__ = "equipment_readings"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True,
        default=lambda: datetime.now(timezone.utc)
    )
    equipment_id: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    plant_id: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    point_id: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    point_code: Mapped[str] = mapped_column(String(64), nullable=False)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    quality: Mapped[str] = mapped_column(String(16), default="good")
    source: Mapped[str] = mapped_column(String(16), default="live")

    __table_args__ = (
        Index("ix_readings_point_time", "point_id", "time"),
        Index("ix_readings_equip_time", "equipment_id", "time"),
    )


def create_hypertable(conn):
    conn.execute(text(
        "SELECT create_hypertable('equipment_readings', 'time', if_not_exists => TRUE)"
    ))
    conn.execute(text(
        "SELECT add_retention_policy('equipment_readings', INTERVAL '90 days', if_not_exists => TRUE)"
    ))

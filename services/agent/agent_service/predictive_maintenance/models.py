from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import String, Float, DateTime, JSON
from sqlalchemy.orm import Mapped, mapped_column

from common.db import Base


class DegradationResult(Base):
    __tablename__ = "degradation_results"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    edge_id: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    equipment_id: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    equipment_type: Mapped[str] = mapped_column(String(32), nullable=False)
    evaluated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    severity: Mapped[str] = mapped_column(String(16), default="normal")
    cop_degradation_pct: Mapped[Optional[float]] = mapped_column(Float)
    approach_temp_drift_k: Mapped[Optional[float]] = mapped_column(Float)
    vibration_trend: Mapped[Optional[float]] = mapped_column(Float)
    cusum_triggered: Mapped[bool] = mapped_column(default=False)
    recommended_action: Mapped[Optional[str]] = mapped_column(String(256))
    detail: Mapped[Optional[dict]] = mapped_column(JSON, default=dict)

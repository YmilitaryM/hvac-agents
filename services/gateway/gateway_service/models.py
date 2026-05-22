import uuid
from datetime import datetime, timezone

from sqlalchemy import String, Boolean, DateTime, JSON, Text, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from typing import Optional

from common.db import Base


class UserModel(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: uuid.uuid4().hex[:16])
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(256))
    role: Mapped[str] = mapped_column(String(16), default="viewer")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    tenant_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False, index=True, default=1,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class AuditLogModel(Base):
    __tablename__ = "audit_logs"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: uuid.uuid4().hex[:16])
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)
    user_id: Mapped[str] = mapped_column(String(128), index=True)
    username: Mapped[str] = mapped_column(String(128))
    action: Mapped[str] = mapped_column(String(128), index=True)
    resource_type: Mapped[str] = mapped_column(String(64))
    resource_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    method: Mapped[str] = mapped_column(String(10))
    path: Mapped[str] = mapped_column(String(512))
    old_value: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    new_value: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    ip_address: Mapped[str] = mapped_column(String(45), default="")
    user_agent: Mapped[str] = mapped_column(String(256), default="")
    status_code: Mapped[int] = mapped_column(Integer, default=0)
    success: Mapped[bool] = mapped_column(Boolean, default=True)

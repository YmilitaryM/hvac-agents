from sqlalchemy import Column, ForeignKey, Integer, String, DateTime
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from datetime import datetime, timezone


class Base(DeclarativeBase):
    pass


class TenantMixin:
    """Mixin that adds tenant_id column for multi-tenant isolation.

    Usage::

        class MyModel(Base, TenantMixin):
            __tablename__ = "my_table"
            ...
    """

    tenant_id = Column(
        Integer,
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        default=1,  # MVP: default to the "default" tenant
    )


class TenantModel(Base):
    """The tenants table that owns all tenant-scoped data."""
    __tablename__ = "tenants"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(128), unique=True, nullable=False)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


def create_engine(database_url: str):
    return create_async_engine(database_url, echo=False)


def create_session_factory(engine):
    return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

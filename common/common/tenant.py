"""Multi-tenant data isolation helpers.

Provides a thread-safe tenant context via ContextVar and a query filter
utility that automatically appends a WHERE clause for tenant_id.
"""

from contextvars import ContextVar, Token
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.sql import Select

# ContextVar for the current request's tenant_id.
# Uses None as the sentinel meaning "no tenant set"; callers should
# default to tenant_id=1 (the default tenant) in MVP.
current_tenant_id: ContextVar[Optional[int]] = ContextVar(
    "current_tenant_id", default=None
)


def set_current_tenant(tenant_id: int) -> Token:
    """Set the tenant_id for the current request context.

    Returns a Token that must be passed to ``current_tenant_id.reset()``
    to restore the previous value when the request is done.

    Usage::

        token = set_current_tenant(42)
        try:
            ...  # all queries in this scope see tenant_id=42
        finally:
            current_tenant_id.reset(token)
    """
    return current_tenant_id.set(tenant_id)


def get_current_tenant() -> Optional[int]:
    """Return the tenant_id for the current request context.

    Returns ``None`` when no tenant has been set.  In MVP the caller
    should fall back to tenant_id=1 (the default tenant).
    """
    return current_tenant_id.get()


def tenant_filter(query: Select, model: Any, field_name: str = "tenant_id") -> Select:
    """Apply a tenant_id WHERE clause to a SQLAlchemy query.

    The filter is only added when ``get_current_tenant()`` returns a
    non-None value; otherwise the query is returned unchanged so that
    MVP callers without a tenant context continue to work.

    Usage::

        q = select(EnergySnapshot).where(EnergySnapshot.plant_id == 5)
        q = tenant_filter(q, EnergySnapshot)
        results = await session.execute(q)
    """
    tid = get_current_tenant()
    if tid is not None:
        column = getattr(model, field_name, None)
        if column is not None:
            return query.where(column == tid)
    return query

"""Tests for multi-tenant isolation helpers (common.tenant).

Run from the repo root:

    uv run --directory common pytest common/tests/test_tenant.py -v
"""

import asyncio
import concurrent.futures

from common.tenant import (
    current_tenant_id,
    set_current_tenant,
    get_current_tenant,
    tenant_filter,
)
from sqlalchemy import Column, Integer, String, select
from sqlalchemy.orm import DeclarativeBase


# ---- Test models -----------------------------------------------------------

class _TestBase(DeclarativeBase):
    pass


class _Widget(_TestBase):
    __tablename__ = "widgets"
    id = Column(Integer, primary_key=True)
    name = Column(String)
    tenant_id = Column(Integer, nullable=False)


# ---- ContextVar tests ------------------------------------------------------

def test_tenant_contextvar_default():
    """get_current_tenant returns None when nothing has been set."""
    assert get_current_tenant() is None


def test_set_and_get_tenant():
    """set_current_tenant places a value; reset restores the previous."""
    assert get_current_tenant() is None

    token = set_current_tenant(42)
    assert get_current_tenant() == 42

    current_tenant_id.reset(token)
    assert get_current_tenant() is None


def test_nested_tenants():
    """Nested set_current_tenant calls are properly isolated."""
    token1 = set_current_tenant(10)
    assert get_current_tenant() == 10

    token2 = set_current_tenant(20)
    assert get_current_tenant() == 20

    current_tenant_id.reset(token2)
    assert get_current_tenant() == 10

    current_tenant_id.reset(token1)
    assert get_current_tenant() is None


def test_tenant_isolation_across_contexts():
    """Two concurrent logical contexts see different tenant values.

    We simulate this by creating separate asyncio tasks, each of which
    sets its own tenant and verifies isolation.
    """
    results = {}

    async def task(tenant_id: int):
        token = set_current_tenant(tenant_id)
        try:
            # The value visible inside this task must be ours
            results[tenant_id] = get_current_tenant()
            await asyncio.sleep(0.01)
            # After a yield the value must still be ours
            results[f"{tenant_id}_after_yield"] = get_current_tenant()
        finally:
            current_tenant_id.reset(token)

    async def run():
        await asyncio.gather(task(5), task(99))

    asyncio.run(run())
    assert results[5] == 5
    assert results[99] == 99
    assert results["5_after_yield"] == 5
    assert results["99_after_yield"] == 99

    # After tasks complete, the default value is restored
    assert get_current_tenant() is None


# ---- tenant_filter tests ---------------------------------------------------

def test_tenant_filter_applies_when_tenant_is_set():
    """tenant_filter adds a WHERE tenant_id=... clause."""
    token = set_current_tenant(7)
    try:
        q = select(_Widget).where(_Widget.name == "pump")
        filtered = tenant_filter(q, _Widget)
        sql = str(filtered.compile(compile_kwargs={"literal_binds": True}))
        assert "tenant_id = 7" in sql
        assert "widgets.name = 'pump'" in sql
    finally:
        current_tenant_id.reset(token)


def test_tenant_filter_noop_when_tenant_is_none():
    """tenant_filter does not modify the query when no tenant is set."""
    # Ensure no tenant is set
    q = select(_Widget).where(_Widget.name == "pump")
    filtered = tenant_filter(q, _Widget)
    sql = str(filtered.compile(compile_kwargs={"literal_binds": True}))
    # The SELECT list may contain the column name, but WHERE must not
    assert "WHERE widgets.name = 'pump'" in sql
    # Verify no WHERE clause references tenant_id
    where_start = sql.find("WHERE")
    where_clause = sql[where_start:] if where_start >= 0 else ""
    assert "tenant_id" not in where_clause


def test_tenant_filter_noop_when_model_lacks_column():
    """tenant_filter is safe to call on models without a tenant_id column."""

    class ModelWithoutTenant(_TestBase):
        __tablename__ = "no_tenant"
        id = Column(Integer, primary_key=True)

    token = set_current_tenant(3)
    try:
        q = select(ModelWithoutTenant)
        filtered = tenant_filter(q, ModelWithoutTenant)
        sql = str(filtered.compile(compile_kwargs={"literal_binds": True}))
        assert "tenant_id" not in sql
    finally:
        current_tenant_id.reset(token)


def test_set_current_tenant_returns_token():
    """set_current_tenant returns a ContextVar Token."""
    token = set_current_tenant(1)
    assert hasattr(token, "var")
    assert token.var is current_tenant_id
    current_tenant_id.reset(token)


# ---- Integration-style: multiple queries in single scope -------------------

def test_multiple_queries_in_same_scope():
    """Multiple queries in the same tenant scope all get the filter."""
    token = set_current_tenant(12)
    try:
        q1 = tenant_filter(select(_Widget), _Widget)
        q2 = tenant_filter(select(_Widget).where(_Widget.name == "fan"), _Widget)

        sql1 = str(q1.compile(compile_kwargs={"literal_binds": True}))
        sql2 = str(q2.compile(compile_kwargs={"literal_binds": True}))

        assert "tenant_id = 12" in sql1
        assert "tenant_id = 12" in sql2
    finally:
        current_tenant_id.reset(token)

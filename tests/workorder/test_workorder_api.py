"""Tests for the workorder FastAPI endpoints.

Uses httpx.ASGITransport against the real FastAPI app backed by an in-memory
SQLite database.  No mocking — the real app, router, and DB layer are exercised.
"""

import os
from contextlib import AsyncExitStack

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from agent_service.main import app, lifespan


@pytest_asyncio.fixture
async def client():
    """Configure the app with a SQLite in-memory DB, enter lifespan, return an AsyncClient."""
    os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///test.db"

    # Bust the cached settings singleton so the env var is re-read.
    import common.config
    common.config._settings = None

    async with AsyncExitStack() as stack:
        await stack.enter_async_context(lifespan(app))

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            yield c


# ── helpers ──────────────────────────────────────────────────────────────────

async def _create(client, **overrides):
    """Create a work order and return the parsed JSON body."""
    payload = {
        "edge_id": "edge-001",
        "equipment_id": "CH-1",
        "severity": "warning",
        "title": "Test work order",
        "description": "Created by test",
        **overrides,
    }
    resp = await client.post("/api/workorders/", json=payload)
    assert resp.status_code == 201, resp.text
    return resp.json()


# ── POST / (create) ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_work_order_returns_201(client):
    wo = await _create(client)
    assert wo["status"] == "open"
    assert "id" in wo
    assert wo["edge_id"] == "edge-001"
    assert wo["equipment_id"] == "CH-1"
    assert wo["severity"] == "warning"
    assert wo["title"] == "Test work order"
    assert wo["description"] == "Created by test"


@pytest.mark.asyncio
async def test_create_work_order_with_equipment_type_assigns_role(client):
    wo = await _create(client, equipment_type="pump", severity="critical")
    assert wo["assigned_to"] == "mechanic-lead"


@pytest.mark.asyncio
async def test_create_work_order_with_explicit_assigned_to(client):
    wo = await _create(client, assigned_to="super-operator")
    assert wo["assigned_to"] == "super-operator"


@pytest.mark.asyncio
async def test_create_work_order_no_equipment_type_no_auto_assign(client):
    wo = await _create(client, equipment_type=None)
    assert wo["assigned_to"] is None


# ── GET / (list) ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_work_orders_returns_200(client):
    resp = await client.get("/api/workorders/")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_list_work_orders_filter_by_status(client):
    await _create(client, title="order-A")
    await _create(client, title="order-B")

    resp = await client.get("/api/workorders/", params={"status": "open"})
    assert resp.status_code == 200
    data = resp.json()
    assert all(wo["status"] == "open" for wo in data)


@pytest.mark.asyncio
async def test_list_work_orders_filter_by_edge_id(client):
    await _create(client, edge_id="edge-X", title="X-1")
    await _create(client, edge_id="edge-Y", title="Y-1")

    resp = await client.get("/api/workorders/", params={"edge_id": "edge-X"})
    assert resp.status_code == 200
    data = resp.json()
    assert all(wo["edge_id"] == "edge-X" for wo in data)


# ── GET /{wo_id} ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_work_order_by_id(client):
    wo = await _create(client, title="single-get")
    resp = await client.get(f"/api/workorders/{wo['id']}")
    assert resp.status_code == 200
    assert resp.json()["title"] == "single-get"


@pytest.mark.asyncio
async def test_get_work_order_404(client):
    resp = await client.get("/api/workorders/99999")
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Work order not found"


# ── POST /{wo_id}/transition ─────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_transition_valid_full_lifecycle(client):
    """open → acknowledged → in_progress → resolved → closed."""
    wo = await _create(client, title="full-cycle")

    # open -> acknowledged
    resp = await client.post(
        f"/api/workorders/{wo['id']}/transition",
        json={"to_status": "acknowledged", "changed_by": "op", "note": "seen"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "acknowledged"

    # acknowledged -> in_progress
    resp = await client.post(
        f"/api/workorders/{wo['id']}/transition",
        json={"to_status": "in_progress"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "in_progress"

    # in_progress -> resolved
    resp = await client.post(
        f"/api/workorders/{wo['id']}/transition",
        json={"to_status": "resolved"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "resolved"
    assert data["resolved_at"] is not None

    # resolved -> closed
    resp = await client.post(
        f"/api/workorders/{wo['id']}/transition",
        json={"to_status": "closed"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "closed"


@pytest.mark.asyncio
async def test_transition_reopen(client):
    """resolved → in_progress (reopen) is valid."""
    wo = await _create(client)
    await client.post(f"/api/workorders/{wo['id']}/transition",
                      json={"to_status": "acknowledged"})
    await client.post(f"/api/workorders/{wo['id']}/transition",
                      json={"to_status": "in_progress"})
    await client.post(f"/api/workorders/{wo['id']}/transition",
                      json={"to_status": "resolved"})
    # Reopen
    resp = await client.post(f"/api/workorders/{wo['id']}/transition",
                             json={"to_status": "in_progress"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "in_progress"


@pytest.mark.asyncio
async def test_transition_invalid_returns_400(client):
    wo = await _create(client)
    resp = await client.post(
        f"/api/workorders/{wo['id']}/transition",
        json={"to_status": "resolved"},  # open -> resolved is invalid
    )
    assert resp.status_code == 400
    assert "Cannot transition" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_transition_non_existent_returns_404(client):
    resp = await client.post(
        "/api/workorders/99999/transition",
        json={"to_status": "acknowledged"},
    )
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Work order not found"


# ── POST /generate ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_auto_generate_anomaly(client):
    resp = await client.post(
        "/api/workorders/generate",
        json={
            "edge_id": "edge-10",
            "equipment_id": "CT-1",
            "equipment_type": "cooling_tower",
            "severity": "critical",
            "detail": "Approach temp exceeded",
            "check_id": "approach_check",
            "generate_type": "anomaly",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == "Inspection failed: approach_check"
    assert data["source"] == "auto"
    assert data["status"] == "open"
    assert data["assigned_to"] == "hvac-technician-lead"


@pytest.mark.asyncio
async def test_auto_generate_degradation(client):
    resp = await client.post(
        "/api/workorders/generate",
        json={
            "edge_id": "edge-11",
            "equipment_id": "P-2",
            "equipment_type": "pump",
            "severity": "critical",
            "detail": "Efficiency dropped",
            "generate_type": "degradation",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == "Degradation detected: P-2"
    assert data["source"] == "auto"
    assert data["status"] == "open"
    assert data["assigned_to"] == "mechanic-lead"

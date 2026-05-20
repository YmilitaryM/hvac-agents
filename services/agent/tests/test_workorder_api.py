# services/agent/tests/test_workorder_api.py
import os
from contextlib import AsyncExitStack

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from agent_service.main import app, lifespan


@pytest_asyncio.fixture
async def client():
    # Ensure SQLite is used for tests
    os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///test.db"
    # Reset cached settings so the env var is picked up
    import common.config
    common.config._settings = None

    async with AsyncExitStack() as stack:
        # Enter the app lifespan (sets up engine + session_factory on app.state)
        await stack.enter_async_context(lifespan(app))

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            yield c


@pytest.mark.asyncio
async def test_create_work_order(client):
    payload = {
        "edge_id": "edge-001",
        "equipment_id": "CH-1",
        "severity": "critical",
        "title": "COP degradation detected",
        "description": "COP dropped from 5.5 to 3.8",
    }
    resp = await client.post("/api/workorders/", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "open"
    assert "id" in data


@pytest.mark.asyncio
async def test_list_work_orders(client):
    resp = await client.get("/api/workorders/")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_transition_work_order(client):
    # Create
    create_resp = await client.post("/api/workorders/", json={
        "edge_id": "edge-001",
        "equipment_id": "P-1",
        "severity": "warning",
        "title": "Test order",
    })
    wo_id = create_resp.json()["id"]

    # Transition
    resp = await client.post(f"/api/workorders/{wo_id}/transition", json={
        "to_status": "acknowledged",
        "changed_by": "operator-1",
        "note": "Acknowledged, will inspect",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "acknowledged"


@pytest.mark.asyncio
async def test_invalid_transition_rejected(client):
    create_resp = await client.post("/api/workorders/", json={
        "edge_id": "edge-001",
        "equipment_id": "P-1",
        "severity": "warning",
        "title": "Test order",
    })
    wo_id = create_resp.json()["id"]

    resp = await client.post(f"/api/workorders/{wo_id}/transition", json={
        "to_status": "resolved",
    })
    assert resp.status_code == 400

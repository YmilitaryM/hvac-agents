import pytest
from httpx import ASGITransport, AsyncClient

from edgemanager_service.main import app


@pytest.fixture
async def client(setup_app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        # Register an edge first
        await c.post("/api/edges/register", json={
            "id": "edge-hb-001",
            "name": "HB Test",
            "plant_id": "plant-001",
            "version": "0.1.0",
        })
        yield c


@pytest.mark.asyncio
async def test_post_heartbeat(client):
    payload = {
        "cpu_pct": 45.2,
        "mem_mb": 512.0,
        "disk_pct": 30.1,
        "collector_ok": True,
        "controller_ok": True,
        "inspector_ok": False,
    }
    resp = await client.post("/api/edges/edge-hb-001/heartbeat", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"


@pytest.mark.asyncio
async def test_heartbeat_updates_last_seen(client):
    await client.post("/api/edges/edge-hb-001/heartbeat", json={"cpu_pct": 10.0})
    resp = await client.get("/api/edges/edge-hb-001")
    assert resp.json()["last_seen_at"] is not None


@pytest.mark.asyncio
async def test_heartbeat_unknown_edge(client):
    resp = await client.post("/api/edges/edge-unknown/heartbeat", json={"cpu_pct": 10.0})
    assert resp.status_code == 404

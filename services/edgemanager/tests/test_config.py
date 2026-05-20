import pytest
from httpx import ASGITransport, AsyncClient

from edgemanager_service.main import app


@pytest.fixture
async def client(setup_app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        await c.post("/api/edges/register", json={
            "id": "edge-cfg-001",
            "name": "Config Test",
            "plant_id": "plant-001",
            "version": "0.1.0",
        })
        yield c


@pytest.mark.asyncio
async def test_set_config(client):
    payload = {"mode": "live", "acquisition": {"poll_interval_ms": 500}}
    resp = await client.post("/api/edges/edge-cfg-001/config", json=payload)
    assert resp.status_code == 200
    assert resp.json()["config_hash"] is not None


@pytest.mark.asyncio
async def test_get_config(client):
    resp = await client.get("/api/edges/edge-cfg-001/config")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_set_config_unknown_edge(client):
    resp = await client.post("/api/edges/edge-unknown/config", json={"mode": "live"})
    assert resp.status_code == 404

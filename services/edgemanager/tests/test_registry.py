import pytest
from httpx import ASGITransport, AsyncClient

from edgemanager_service.main import app


@pytest.fixture
async def client(setup_app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


@pytest.mark.asyncio
async def test_register_edge_device(client):
    payload = {
        "id": "edge-001",
        "name": "Station A Edge",
        "plant_id": "plant-001",
        "mode": "hybrid",
        "version": "0.1.0",
    }
    resp = await client.post("/api/edges/register", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["id"] == "edge-001"
    assert data["mode"] == "hybrid"


@pytest.mark.asyncio
async def test_list_edge_devices(client):
    resp = await client.get("/api/edges/")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_register_duplicate_rejected(client):
    payload = {"id": "edge-002", "name": "Dup", "plant_id": "p1", "version": "0.1.0"}
    await client.post("/api/edges/register", json=payload)
    resp = await client.post("/api/edges/register", json=payload)
    assert resp.status_code == 409

import pytest
from httpx import ASGITransport, AsyncClient

from edgemanager_service.main import app


@pytest.fixture
async def client(setup_app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        await c.post("/api/edges/register", json={
            "id": "edge-ota-001",
            "name": "OTA Test",
            "plant_id": "plant-001",
            "version": "0.1.0",
        })
        yield c


@pytest.mark.asyncio
async def test_create_ota_task(client):
    payload = {
        "target_type": "model",
        "version": "anomaly_v2.onnx",
        "payload_url": "https://models.example.com/anomaly_v2.onnx",
    }
    resp = await client.post("/api/edges/edge-ota-001/ota", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "pending"
    assert "id" in data


@pytest.mark.asyncio
async def test_get_ota_task(client):
    payload = {"target_type": "model", "version": "v1", "payload_url": "https://x.com/m.onnx"}
    create = await client.post("/api/edges/edge-ota-001/ota", json=payload)
    task_id = create.json()["id"]

    resp = await client.get(f"/api/edges/edge-ota-001/ota/{task_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == task_id

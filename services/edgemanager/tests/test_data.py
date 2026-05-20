import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from edgemanager_service.main import app
from edgemanager_service.models import SyncWatermark


@pytest_asyncio.fixture
async def client(setup_app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        await c.post("/api/edges/register", json={
            "id": "edge-data-001",
            "name": "Data Test",
            "plant_id": "plant-001",
            "version": "0.1.0",
        })
        yield c


@pytest.mark.asyncio
async def test_ingest_readings(client):
    payload = {
        "readings": [
            {"time": "2026-05-20T10:00:00Z", "point_id": "p1", "value": 23.5, "quality": "good"},
            {"time": "2026-05-20T10:15:00Z", "point_id": "p1", "value": 24.0, "quality": "good"},
        ],
        "inspections": [],
        "work_orders": [],
    }
    resp = await client.post("/api/edges/edge-data-001/data/ingest", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["readings_received"] == 2
    assert "watermark" in data


@pytest.mark.asyncio
async def test_ingest_updates_watermark(client):
    payload = {"readings": [
        {"time": "2026-05-20T11:00:00Z", "point_id": "p2", "value": 30.0, "quality": "good"},
    ], "inspections": [], "work_orders": []}
    await client.post("/api/edges/edge-data-001/data/ingest", json=payload)

    async with app.state.session_factory() as session:
        result = await session.execute(
            select(SyncWatermark).where(
                SyncWatermark.edge_id == "edge-data-001",
                SyncWatermark.table_name == "readings",
            )
        )
        wm = result.scalar_one_or_none()
        assert wm is not None

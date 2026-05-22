import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from health_service.main import app


@pytest_asyncio.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


@pytest.mark.asyncio
async def test_health_endpoint(client):
    r = await client.get("/health")
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_health_dashboard(client):
    r = await client.get("/api/health/dashboard?plant_id=1")
    assert r.status_code == 200
    data = r.json()
    assert "equipment_health" in data or "items" in data


@pytest.mark.asyncio
async def test_rul_endpoint(client):
    r = await client.get("/api/health/rul?plant_id=1")
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_fmea_endpoint(client):
    r = await client.get("/api/health/fmea?equipment_type=centrifugal_chiller")
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_vibration_endpoint(client):
    r = await client.get("/api/health/vibration?equipment_id=1")
    assert r.status_code == 200

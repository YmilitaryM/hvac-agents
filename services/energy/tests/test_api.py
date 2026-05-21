import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from energy_service.main import app


@pytest_asyncio.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


@pytest.mark.asyncio
async def test_health_endpoint(client):
    r = await client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "healthy"


@pytest.mark.asyncio
async def test_dashboard_endpoint(client):
    r = await client.get("/api/energy/dashboard?plant_id=1")
    assert r.status_code == 200
    data = r.json()
    assert "current_cop" in data
    assert "total_power_kw" in data


@pytest.mark.asyncio
async def test_baseline_endpoint(client):
    r = await client.get("/api/energy/baseline?plant_id=1")
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_demand_endpoint(client):
    r = await client.get("/api/energy/peak-demand?plant_id=1")
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_comparison_endpoint(client):
    r = await client.get("/api/energy/comparison?plant_id=1&period=month")
    assert r.status_code == 200

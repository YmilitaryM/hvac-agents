"""Integration tests: service health checks."""
import pytest
import httpx

BASE = "http://localhost:8000"
SERVICES = ["asset", "environment", "simulation", "agent", "acquisition", "gateway"]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_gateway_health():
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{BASE}/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["service"] == "gateway"


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.parametrize("service", SERVICES)
async def test_service_health_via_gateway(service: str):
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{BASE}/api/health", params={"service": service})
        assert resp.status_code in (200, 404)  # 404 ok if route not proxied

# services/agent/tests/test_maintenance_api.py
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from agent_service.main import app


@pytest_asyncio.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


@pytest.mark.asyncio
async def test_evaluate_degradation(client):
    payload = {
        "edge_id": "edge-001",
        "equipment_id": "CH-1",
        "equipment_type": "chiller",
        "design_cop": 5.5,
        "cop_window": [3.8, 3.9, 3.7, 3.85, 3.9],
        "approach_temp_avg": 2.5,
        "vibration_window": [1.2, 1.3, 1.1],
    }
    resp = await client.post("/api/maintenance/evaluate", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert "severity" in data
    assert data["cop_degradation_pct"] > 20


@pytest.mark.asyncio
async def test_predict_failure(client):
    payload = {
        "cop_current": 3.2,
        "vibration_rms": 8.5,
        "approach_temp": 6.0,
    }
    resp = await client.post("/api/maintenance/predict", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert "failure_probability" in data
    assert data["failure_probability"] > 0.5  # clearly failing features

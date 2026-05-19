import pytest
import httpx

ASSET_URL = "http://localhost:8001"
SIM_URL = "http://localhost:8003"
GATEWAY_URL = "http://localhost:8000"


@pytest.mark.integration
async def test_create_equipment_and_run_simulation():
    async with httpx.AsyncClient() as client:
        # 1. Get equipment types
        resp = await client.get(f"{ASSET_URL}/api/templates/equipment-types")
        assert resp.status_code == 200
        types = resp.json()
        chiller_type = next(t for t in types if t["category"] == "chiller")

        # 2. Create equipment
        resp = await client.post(f"{GATEWAY_URL}/api/equipment/", json={
            "name": "Test Chiller",
            "equipment_type_id": chiller_type["id"],
        })
        assert resp.status_code == 201
        eq = resp.json()
        assert len(eq["points"]) == len(chiller_type["points"])

        # 3. Create plant from template
        resp = await client.post(f"{GATEWAY_URL}/api/plants/", json={
            "name": "Test Plant",
            "template_id": "primary_variable_flow",
            "template_params": {"N": 1, "standby": 1},
        })
        assert resp.status_code == 201

        # 4. Run simulation
        plant_id = resp.json()["plant"]["id"]
        resp = await client.post(f"{GATEWAY_URL}/api/simulation/run", json={
            "plant_id": plant_id,
            "outdoor_wb_temp": 26.0,
            "outdoor_db_temp": 33.0,
        })
        assert resp.status_code == 200
        assert "snapshot" in resp.json()

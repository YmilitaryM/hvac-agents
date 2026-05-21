import pytest
from fastapi.testclient import TestClient
from src.api.main import create_app
import src.api.monitoring as monitoring_mod
import src.api.strategy as strategy_mod
import src.api.reports as reports_mod
import src.api.plants as plants_mod
import src.api.equipment as equipment_mod


@pytest.fixture
def client():
    app = create_app(debug=True)
    return TestClient(app)


@pytest.fixture(autouse=True)
def reset_in_memory_state():
    """Reset all in-memory state before each test for isolation."""
    monitoring_mod._plant_snapshots.clear()
    monitoring_mod._alerts.clear()
    monitoring_mod._health_scores.clear()
    strategy_mod._strategies.clear()
    strategy_mod._strategy_history.clear()
    reports_mod._reports.clear()
    plants_mod._plants.clear()
    equipment_mod._equipment.clear()


class TestHealthAndStatus:
    def test_health_check(self, client):
        response = client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

    def test_system_status(self, client):
        response = client.get("/api/status")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "running"
        assert "agents" in data


class TestMonitoring:
    def test_get_snapshot_empty(self, client):
        response = client.get("/api/monitoring/snapshot")
        assert response.status_code == 200
        data = response.json()
        assert data["snapshot"] is None

    def test_ingest_and_retrieve_snapshot(self, client):
        snap = {
            "total_cooling_load_rt": 500,
            "total_power_kw": 100,
            "outdoor_wb_temp": 26.0,
            "outdoor_db_temp": 33.0,
            "system_cop": 17.6,
        }
        # Ingest
        resp = client.post("/api/monitoring/snapshot", json=snap)
        assert resp.status_code == 200

        # Retrieve
        resp = client.get("/api/monitoring/snapshot")
        assert resp.status_code == 200
        data = resp.json()
        assert data["snapshot"]["total_cooling_load_rt"] == 500

    def test_get_snapshots_with_limit(self, client):
        for i in range(5):
            client.post("/api/monitoring/snapshot", json={"total_cooling_load_rt": float(i * 100)})
        resp = client.get("/api/monitoring/snapshots?limit=3")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["snapshots"]) == 3

    def test_ingest_and_retrieve_alert(self, client):
        alert = {"level": "warning", "message": "Test alert", "device": "chiller_1"}
        resp = client.post("/api/monitoring/alerts", json=alert)
        assert resp.status_code == 200

        resp = client.get("/api/monitoring/alerts")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["alerts"]) == 1

    def test_health_scores(self, client):
        scores = {"chiller_1": 95.0, "chiller_2": 88.0}
        resp = client.post("/api/monitoring/health", json=scores)
        assert resp.status_code == 200

        resp = client.get("/api/monitoring/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["health_scores"]["chiller_1"] == 95.0

    def test_realtime_kpi_empty(self, client):
        resp = client.get("/api/monitoring/kpi")
        assert resp.status_code == 200
        data = resp.json()
        assert data["kpi"] is None


class TestStrategy:
    def test_create_and_get_strategy(self, client):
        strategy = {
            "strategy_id": "test_s1",
            "trigger_type": "scheduled",
            "current_load_rt": 500,
            "predicted_load_rt": 480,
            "actions": [{"seq": 1, "device": "chiller_1", "action": "set_load", "value": 300}],
        }
        resp = client.post("/api/strategies/", json=strategy)
        assert resp.status_code == 200

        resp = client.get("/api/strategies/test_s1")
        assert resp.status_code == 200
        data = resp.json()
        assert data["strategy"]["strategy_id"] == "test_s1"

    def test_create_strategy_missing_id(self, client):
        resp = client.post("/api/strategies/", json={"trigger_type": "scheduled"})
        assert resp.status_code == 400

    def test_get_nonexistent_strategy(self, client):
        resp = client.get("/api/strategies/nonexistent")
        assert resp.status_code == 404

    def test_update_strategy_status(self, client):
        client.post("/api/strategies/", json={"strategy_id": "test_s2", "actions": []})
        resp = client.put("/api/strategies/test_s2/status", json={"status": "approved"})
        assert resp.status_code == 200

        resp = client.get("/api/strategies/test_s2")
        assert resp.json()["strategy"]["status"] == "approved"

    def test_delete_strategy(self, client):
        client.post("/api/strategies/", json={"strategy_id": "test_s3", "actions": []})
        resp = client.delete("/api/strategies/test_s3")
        assert resp.status_code == 200

        resp = client.get("/api/strategies/test_s3")
        assert resp.status_code == 404


class TestReports:
    def test_save_and_get_daily_report(self, client):
        report = {
            "date": "2026-05-19",
            "summary": "Test daily report",
            "kpis": {"average_cop": 5.5},
        }
        resp = client.post("/api/reports/daily", json=report)
        assert resp.status_code == 200

        resp = client.get("/api/reports/daily?date=2026-05-19")
        assert resp.status_code == 200
        data = resp.json()
        assert data["report"]["summary"] == "Test daily report"

    def test_list_reports(self, client):
        client.post("/api/reports/daily", json={"date": "2026-05-19", "summary": "Day 1"})
        client.post("/api/reports/daily", json={"date": "2026-05-20", "summary": "Day 2"})
        resp = client.get("/api/reports/list")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["available_dates"]) == 2


class TestPlants:
    def test_list_plants_empty(self, client):
        resp = client.get("/api/plants/")
        assert resp.status_code == 200
        data = resp.json()
        assert data["plants"] == []

    def test_create_and_get_plant(self, client):
        plant = {
            "name": "测试制冷站",
            "equipment": [
                {"id": "eq-1", "name": "冷水机组-1", "type_code": "centrifugal_chiller", "position": {"x": 0, "y": 0, "z": 0}, "design_params": {}},
            ],
            "pipe_segments": [],
        }
        resp = client.post("/api/plants/", json=plant)
        assert resp.status_code == 200
        data = resp.json()
        assert "id" in data
        plant_id = data["id"]

        resp = client.get(f"/api/plants/{plant_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "测试制冷站"
        assert len(data["equipment"]) == 1

    def test_create_plant_generates_id(self, client):
        resp = client.post("/api/plants/", json={"name": "auto-id"})
        assert resp.status_code == 200
        assert len(resp.json()["id"]) == 16

    def test_list_plants_with_data(self, client):
        client.post("/api/plants/", json={"name": "Plant A"})
        client.post("/api/plants/", json={"name": "Plant B"})
        resp = client.get("/api/plants/")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["plants"]) == 2

    def test_get_nonexistent_plant(self, client):
        resp = client.get("/api/plants/nonexistent")
        assert resp.status_code == 404

    def test_update_plant(self, client):
        resp = client.post("/api/plants/", json={"name": "original"})
        plant_id = resp.json()["id"]

        resp = client.put(f"/api/plants/{plant_id}", json={
            "name": "updated",
            "equipment": [{"id": "eq-2", "name": "pump", "type_code": "pump", "position": {"x": 1, "y": 0, "z": 0}, "design_params": {}}],
            "pipe_segments": [],
        })
        assert resp.status_code == 200

        resp = client.get(f"/api/plants/{plant_id}")
        assert resp.json()["name"] == "updated"
        assert len(resp.json()["equipment"]) == 1

    def test_update_nonexistent_plant_upserts(self, client):
        resp = client.put("/api/plants/new-plant", json={"name": "upserted"})
        assert resp.status_code == 200
        assert resp.json()["id"] == "new-plant"

    def test_delete_plant(self, client):
        resp = client.post("/api/plants/", json={"name": "to-delete"})
        plant_id = resp.json()["id"]

        resp = client.delete(f"/api/plants/{plant_id}")
        assert resp.status_code == 200

        resp = client.get(f"/api/plants/{plant_id}")
        assert resp.status_code == 404

    def test_delete_nonexistent_plant(self, client):
        resp = client.delete("/api/plants/nonexistent")
        assert resp.status_code == 404

    def test_list_templates(self, client):
        resp = client.get("/api/plants/templates")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["templates"]) >= 1
        template_ids = [t["id"] for t in data["templates"]]
        assert "primary_variable_flow" in template_ids

    def test_create_plant_from_template(self, client):
        resp = client.post("/api/plants/", json={
            "name": "模板制冷站",
            "template_id": "primary_variable_flow",
            "N": 2,
            "standby": 1,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "模板制冷站"
        assert len(data["equipment"]) > 0
        assert len(data["pipe_segments"]) > 0

    def test_create_plant_from_nonexistent_template(self, client):
        resp = client.post("/api/plants/", json={
            "name": "bad",
            "template_id": "no_such_template",
        })
        assert resp.status_code == 404

    def test_save_and_load_pipe_segments(self, client):
        plant = {
            "name": "pipe-test",
            "equipment": [
                {"id": "e1", "name": "chiller", "type_code": "centrifugal_chiller", "position": {"x": 0, "y": 0, "z": 0}, "design_params": {}},
                {"id": "e2", "name": "pump", "type_code": "pump", "position": {"x": 6, "y": 0, "z": 0}, "design_params": {}},
            ],
            "pipe_segments": [
                {
                    "id": "pipe-1",
                    "from_equipment_id": "e2",
                    "from_point_code": "outlet_pressure",
                    "to_equipment_id": "e1",
                    "to_point_code": "chw_supply_temp",
                    "diameter_mm": 200,
                    "length_m": 6.0,
                    "waypoints": [],
                }
            ],
        }
        resp = client.post("/api/plants/", json=plant)
        plant_id = resp.json()["id"]

        resp = client.get(f"/api/plants/{plant_id}")
        data = resp.json()
        assert len(data["pipe_segments"]) == 1
        assert data["pipe_segments"][0]["diameter_mm"] == 200


class TestEquipment:
    def test_list_equipment_empty_after_reset(self, client):
        resp = client.get("/api/equipment/")
        assert resp.status_code == 200
        data = resp.json()
        assert data["equipment"] == []

    def test_create_and_list_equipment(self, client):
        eq = {
            "name": "测试冷水机",
            "type_code": "centrifugal_chiller",
            "design_params": {"capacity_rt": 500},
        }
        resp = client.post("/api/equipment/", json=eq)
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "测试冷水机"
        assert data["type_code"] == "centrifugal_chiller"

        resp = client.get("/api/equipment/")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["equipment"]) == 1

    def test_create_equipment_with_equipment_type_id(self, client):
        """Frontend sends equipment_type_id, backend should map to type_code."""
        eq = {
            "name": "test",
            "equipment_type_id": "pump",
        }
        resp = client.post("/api/equipment/", json=eq)
        assert resp.status_code == 200
        assert resp.json()["type_code"] == "pump"

    def test_list_equipment_filter_by_plant_id(self, client):
        client.post("/api/equipment/", json={"name": "free", "type_code": "pump"})
        client.post("/api/equipment/", json={"name": "assigned", "type_code": "pump", "plant_id": "plant-1"})

        resp = client.get("/api/equipment/")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["equipment"]) == 1
        assert data["equipment"][0]["name"] == "free"

    def test_delete_equipment(self, client):
        resp = client.post("/api/equipment/", json={"name": "to-delete", "type_code": "pump"})
        eq_id = resp.json()["id"]

        resp = client.delete(f"/api/equipment/{eq_id}")
        assert resp.status_code == 200

        resp = client.get("/api/equipment/")
        assert len(resp.json()["equipment"]) == 0

    def test_delete_nonexistent_equipment(self, client):
        resp = client.delete("/api/equipment/nonexistent")
        assert resp.status_code == 404

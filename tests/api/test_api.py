import pytest
from fastapi.testclient import TestClient
from src.api.main import create_app
import src.api.monitoring as monitoring_mod
import src.api.strategy as strategy_mod
import src.api.reports as reports_mod


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

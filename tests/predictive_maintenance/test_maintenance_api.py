import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from fastapi import FastAPI

from services.agent.agent_service.predictive_maintenance.api.maintenance import (
    router,
    _get_predictor,
)


@pytest.fixture
def app():
    """Create a FastAPI app with the maintenance router for testing."""
    app = FastAPI()
    app.include_router(router)
    return app


@pytest_asyncio.fixture
async def client(app):
    """Async HTTP client bound to the test app."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


class TestEvaluateEndpoint:
    """Tests for POST /evaluate."""

    @pytest.fixture
    def normal_request(self):
        """Request body for a normal-condition chiller."""
        return {
            "edge_id": "edge-test-001",
            "equipment_id": "eq-chiller-001",
            "equipment_type": "chiller",
            "design_cop": 5.5,
            "cop_window": [5.4, 5.4, 5.4, 5.3, 5.4],
            "approach_temp_avg": 1.5,
            "vibration_window": [2.0, 2.1, 1.9],
        }

    @pytest.mark.asyncio
    async def test_evaluate_returns_200(self, client, normal_request):
        """A valid request should return 200 OK."""
        response = await client.post("/evaluate", json=normal_request)
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_evaluate_contains_required_fields(self, client, normal_request):
        """Response should contain all expected top-level keys."""
        response = await client.post("/evaluate", json=normal_request)
        data = response.json()
        assert "equipment_id" in data
        assert "equipment_type" in data
        assert "severity" in data
        assert "cop_degradation_pct" in data
        assert "approach_temp_drift_k" in data
        assert "vibration_trend" in data
        assert "cusum_triggered" in data
        assert "recommended_action" in data
        assert "edge_id" in data
        assert "rule_recommendations" in data
        assert "schedule" in data

    @pytest.mark.asyncio
    async def test_evaluate_normal_severity(self, client, normal_request):
        """Normal conditions should produce 'normal' severity."""
        response = await client.post("/evaluate", json=normal_request)
        data = response.json()
        assert data["severity"] == "normal"
        assert data["recommended_action"] is None
        assert data["cusum_triggered"] is False

    @pytest.mark.asyncio
    async def test_evaluate_critical_severity(self, client):
        """High COP degradation should produce 'critical' severity."""
        critical_request = {
            "edge_id": "edge-test-002",
            "equipment_id": "eq-chiller-002",
            "equipment_type": "chiller",
            "design_cop": 5.5,
            "cop_window": [3.0, 3.0, 3.0, 3.0],  # ~45% degradation
            "approach_temp_avg": 6.0,  # critical threshold exceeded
            "vibration_window": [8.0, 8.0, 8.0],
        }
        response = await client.post("/evaluate", json=critical_request)
        data = response.json()
        assert data["severity"] == "critical"
        assert data["recommended_action"] is not None
        assert "immediate" in data["recommended_action"].lower()

    @pytest.mark.asyncio
    async def test_evaluate_rule_recommendations_present(self, client, normal_request):
        """rule_recommendations should be a list."""
        response = await client.post("/evaluate", json=normal_request)
        data = response.json()
        assert isinstance(data["rule_recommendations"], list)

    @pytest.mark.asyncio
    async def test_evaluate_critical_generates_rule_recommendations(self, client):
        """Critical conditions should generate rule recommendations."""
        critical_request = {
            "edge_id": "edge-test-003",
            "equipment_id": "eq-chiller-003",
            "equipment_type": "chiller",
            "design_cop": 5.5,
            "cop_window": [2.5, 2.5, 2.5],
            "approach_temp_avg": 6.0,
            "vibration_window": [9.0, 9.0],
        }
        response = await client.post("/evaluate", json=critical_request)
        data = response.json()
        assert len(data["rule_recommendations"]) > 0
        for rec in data["rule_recommendations"]:
            assert "action" in rec
            assert "severity" in rec

    @pytest.mark.asyncio
    async def test_evaluate_schedule_structure(self, client, normal_request):
        """The schedule field should contain recommended_start, deadline, urgency."""
        response = await client.post("/evaluate", json=normal_request)
        data = response.json()
        schedule = data["schedule"]
        assert "severity" in schedule
        assert "recommended_start" in schedule
        assert "deadline" in schedule
        assert "urgency" in schedule

    @pytest.mark.asyncio
    async def test_evaluate_schedule_urgency_for_critical(self, client):
        """Critical severity should produce 'immediate' urgency in schedule."""
        critical_request = {
            "edge_id": "edge-test-004",
            "equipment_id": "eq-chiller-004",
            "equipment_type": "chiller",
            "design_cop": 5.5,
            "cop_window": [2.0, 2.0, 2.0],
            "approach_temp_avg": 6.0,
            "vibration_window": [],
        }
        response = await client.post("/evaluate", json=critical_request)
        data = response.json()
        assert data["schedule"]["urgency"] == "immediate"

    @pytest.mark.asyncio
    async def test_evaluate_preserves_edge_id(self, client, normal_request):
        """The edge_id from the request should appear in the response."""
        response = await client.post("/evaluate", json=normal_request)
        data = response.json()
        assert data["edge_id"] == "edge-test-001"

    @pytest.mark.asyncio
    async def test_evaluate_default_design_cop(self, client):
        """Default design_cop (5.5) should be used when not provided."""
        minimal = {
            "edge_id": "e1",
            "equipment_id": "eq1",
            "equipment_type": "pump",
            "cop_window": [5.5, 5.5],
        }
        response = await client.post("/evaluate", json=minimal)
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_evaluate_empty_vibration_window(self, client):
        """Empty vibration_window should not cause an error."""
        request = {
            "edge_id": "e2",
            "equipment_id": "eq2",
            "equipment_type": "pump",
            "design_cop": 5.5,
            "cop_window": [5.4, 5.4],
            "approach_temp_avg": 0.0,
            "vibration_window": [],
        }
        response = await client.post("/evaluate", json=request)
        assert response.status_code == 200
        data = response.json()
        assert data["vibration_trend"] == 0

    @pytest.mark.asyncio
    async def test_evaluate_cusum_triggered_visible(self, client):
        """cusum_triggered should be present in response."""
        response = await client.post("/evaluate", json={
            "edge_id": "e3",
            "equipment_id": "eq3",
            "equipment_type": "chiller",
            "design_cop": 5.5,
            "cop_window": [5.4, 5.4, 5.4, 5.4, 3.0, 3.0, 3.0, 3.0],
            "approach_temp_avg": 1.0,
            "vibration_window": [],
        })
        data = response.json()
        assert "cusum_triggered" in data
        assert isinstance(data["cusum_triggered"], bool)


class TestPredictEndpoint:
    """Tests for POST /predict."""

    @pytest.mark.asyncio
    async def test_predict_returns_200(self, client):
        """Valid predict request should return 200."""
        response = await client.post("/predict", json={
            "cop_current": 5.5,
            "vibration_rms": 2.0,
            "approach_temp": 2.0,
        })
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_predict_returns_probability(self, client):
        """Response should contain a failure_probability float."""
        response = await client.post("/predict", json={
            "cop_current": 5.5,
            "vibration_rms": 2.0,
            "approach_temp": 2.0,
        })
        data = response.json()
        assert "failure_probability" in data
        assert isinstance(data["failure_probability"], float)
        assert 0.0 <= data["failure_probability"] <= 1.0

    @pytest.mark.asyncio
    async def test_predict_returns_input_features(self, client):
        """Response should echo back the input features for traceability."""
        response = await client.post("/predict", json={
            "cop_current": 4.2,
            "vibration_rms": 3.5,
            "approach_temp": 1.8,
        })
        data = response.json()
        assert data["features"]["cop_current"] == 4.2
        assert data["features"]["vibration_rms"] == 3.5
        assert data["features"]["approach_temp"] == 1.8

    @pytest.mark.asyncio
    async def test_predict_low_cop_high_risk(self, client):
        """Very low COP should produce high failure probability."""
        response = await client.post("/predict", json={
            "cop_current": 1.5,
            "vibration_rms": 3.0,
            "approach_temp": 3.0,
        })
        data = response.json()
        assert data["failure_probability"] > 0.2

    @pytest.mark.asyncio
    async def test_predict_normal_conditions_low_risk(self, client):
        """Normal conditions should produce low failure probability."""
        response = await client.post("/predict", json={
            "cop_current": 5.5,
            "vibration_rms": 2.0,
            "approach_temp": 2.0,
        })
        data = response.json()
        assert data["failure_probability"] < 0.5

    @pytest.mark.asyncio
    async def test_predict_is_deterministic(self, client):
        """Same input should produce same output."""
        payload = {"cop_current": 4.0, "vibration_rms": 3.0, "approach_temp": 4.0}
        r1 = await client.post("/predict", json=payload)
        r2 = await client.post("/predict", json=payload)
        assert r1.json() == r2.json()

    @pytest.mark.asyncio
    async def test_predict_high_vibration_high_risk(self, client):
        """High vibration should produce elevated failure probability."""
        response = await client.post("/predict", json={
            "cop_current": 5.5,
            "vibration_rms": 9.0,
            "approach_temp": 2.0,
        })
        data = response.json()
        assert data["failure_probability"] > 0.3


class TestPredictorLazyInit:
    """Verify the lazy-initialization behavior of _get_predictor."""

    def test_get_predictor_returns_same_instance(self):
        """Calling _get_predictor twice should return the same (cached) instance."""
        import services.agent.agent_service.predictive_maintenance.api.maintenance as maint
        maint._predictor = None
        p1 = maint._get_predictor()
        p2 = maint._get_predictor()
        assert p1 is p2

    def test_get_predictor_creates_trained_model(self):
        """After _get_predictor, the model should be trained."""
        import services.agent.agent_service.predictive_maintenance.api.maintenance as maint
        maint._predictor = None
        p = maint._get_predictor()
        assert p.model is not None

"""Integration tests for safety gates and RL bandit with pipeline data."""

import numpy as np
import pytest

from src.rl.safety_gates import check_rl_safety_gates, SafetyGateResult
from src.rl.bandit import ContextualBandit, BanditPrediction, TrainingExample
from src.rl.features import extract_features, FEATURE_DIM, FEATURE_NAMES
from src.schemas.strategy import (
    Strategy,
    StrategyAction,
    StrategyStatus,
    TriggerType,
    TransitionPlan,
    TransitionPhase,
)
from src.schemas.review import AdvocateOpinion, ReviewVerdict
from src.agents.safety import check_safety, SafetyCheckResult


# ---------------------------------------------------------------------------
# TestSafetyGateIntegration
# ---------------------------------------------------------------------------

class TestSafetyGateIntegration:
    """Test each of the 7 safety gates with appropriate inputs."""

    def test_gate_normal_conditions_allowed(self):
        """Normal conditions should pass all gates (allowed=True)."""
        result = check_rl_safety_gates(
            current_load_rt=500.0,
            outdoor_wb_temp=26.0,
            electricity_price=0.8,
            carbon_intensity=0.5,
            anomaly_detected=False,
        )
        assert result.allowed is True
        assert result.force_human is False
        assert result.force_reject is False
        assert result.force_approve is False

    def test_gate_critical_anomaly_forces_human(self):
        """Critical anomaly forces human review (Gate 1)."""
        result = check_rl_safety_gates(
            current_load_rt=600.0,
            anomaly_detected=True,
            anomaly_details="CRITICAL fault in chiller 1 compressor",
        )
        assert result.allowed is False
        assert result.force_human is True
        assert "critical_anomaly" in result.conditions_triggered

    def test_gate_emergency_fault_forces_reject(self):
        """Emergency or FAULT in anomaly details forces reject (Gate 7)."""
        result = check_rl_safety_gates(
            current_load_rt=600.0,
            anomaly_detected=True,
            anomaly_details="FAULT detected on CHW pump",
        )
        assert result.allowed is False
        assert result.force_reject is True
        assert "emergency_fault" in result.conditions_triggered

    def test_gate_emergency_forces_reject(self):
        """EMERGENCY keyword forces reject (Gate 7)."""
        result = check_rl_safety_gates(
            current_load_rt=600.0,
            anomaly_detected=True,
            anomaly_details="EMERGENCY shutdown initiated",
        )
        assert result.allowed is False
        assert result.force_reject is True

    def test_gate_extreme_weather_forces_human(self):
        """Extreme outdoor wet-bulb temp > 35C forces human review (Gate 2)."""
        result = check_rl_safety_gates(
            current_load_rt=600.0,
            outdoor_wb_temp=38.0,
            anomaly_detected=False,
        )
        assert result.allowed is False
        assert result.force_human is True
        assert "extreme_weather" in result.conditions_triggered

    def test_gate_extreme_load_forces_reject(self):
        """Load > 1400RT forces reject (Gate 3)."""
        result = check_rl_safety_gates(
            current_load_rt=1450.0,
            anomaly_detected=False,
        )
        assert result.allowed is False
        assert result.force_reject is True
        assert "extreme_load" in result.conditions_triggered

    def test_gate_very_low_load_forces_reject(self):
        """Load < 50RT forces reject (Gate 4)."""
        result = check_rl_safety_gates(
            current_load_rt=30.0,
            anomaly_detected=False,
        )
        assert result.allowed is False
        assert result.force_reject is True
        assert "very_low_load" in result.conditions_triggered

    def test_gate_price_spike_forces_human(self):
        """Electricity price > 3.0 forces human review (Gate 5)."""
        result = check_rl_safety_gates(
            current_load_rt=600.0,
            electricity_price=4.0,
            anomaly_detected=False,
        )
        assert result.allowed is False
        assert result.force_human is True
        assert "price_spike" in result.conditions_triggered

    def test_gate_clean_grid_forces_approve(self):
        """Carbon intensity < 0.05 forces approve (Gate 6)."""
        result = check_rl_safety_gates(
            current_load_rt=600.0,
            carbon_intensity=0.02,
            anomaly_detected=False,
        )
        assert result.allowed is True
        assert result.force_approve is True
        assert "clean_grid" in result.conditions_triggered

    def test_gate_ordering_critical_takes_priority(self):
        """Gate 1 (critical anomaly) takes priority over later gates."""
        # Even with clean grid, critical anomaly should force human
        result = check_rl_safety_gates(
            current_load_rt=600.0,
            carbon_intensity=0.02,
            anomaly_detected=True,
            anomaly_details="CRITICAL surge risk on chiller 1",
        )
        assert result.force_human is True
        assert result.force_approve is False

    def test_gate_no_detection_without_anomaly(self):
        """If anomaly_detected=False, anomaly details are ignored."""
        result = check_rl_safety_gates(
            current_load_rt=600.0,
            anomaly_detected=False,
            anomaly_details="CRITICAL failure",
        )
        # Should pass through to normal condition (not trigger critical)
        assert result.allowed is True
        assert len(result.conditions_triggered) == 0

    def test_safety_gate_result_dataclass(self):
        """SafetyGateResult dataclass fields are correct."""
        result = SafetyGateResult(
            allowed=True, force_approve=True,
            reason="Clean grid", conditions_triggered=["clean_grid"],
        )
        assert result.allowed is True
        assert result.force_approve is True
        assert result.force_reject is False
        assert result.force_human is False

    def test_safety_agent_integration_with_strategy(self):
        """SafetyAgent.check_safety validates a real Strategy."""
        actions = [
            StrategyAction(seq=1, device="ch1", action="start"),
            StrategyAction(seq=2, device="ch1", action="set_load", value=300.0),
            StrategyAction(seq=3, device="ch2", action="set_load", value=300.0),
        ]
        phase = TransitionPhase(
            seq=1, duration_sec=300.0,
            description="Ramp chillers",
            actions=actions,
        )
        plan = TransitionPlan(
            total_duration_sec=360.0,
            phases=[phase],
            abort_conditions=["FAULT", "COP < 2.0"],
        )
        strategy = Strategy(
            strategy_id="strat_safety",
            trigger_type=TriggerType.SCHEDULED,
            trigger_time=1000.0,
            current_load_rt=600.0,
            predicted_load_rt=600.0,
            actions=actions,
            transition_plan=plan,
        )

        chillers = {
            "ch1": type("Ch", (), {"capacity_rt": 500.0})(),
            "ch2": type("Ch", (), {"capacity_rt": 500.0})(),
        }

        result = check_safety(strategy, chillers=chillers, t_cw=30.0, current_time=1000.0)
        assert isinstance(result, SafetyCheckResult)
        assert result.passed is True
        assert len(result.failures) == 0
        # No warnings expected at normal conditions
        # (transition_plan has abort conditions, capacity covers load)

    def test_safety_agent_blocking_surge_violation(self):
        """Safety check blocks strategy with load below surge boundary."""
        actions = [
            StrategyAction(seq=1, device="ch1", action="set_load", value=50.0),
        ]
        phase = TransitionPhase(
            seq=1, duration_sec=300.0,
            description="Low load",
            actions=actions,
        )
        plan = TransitionPlan(
            total_duration_sec=300.0,
            phases=[phase],
            abort_conditions=["FAULT"],
        )
        strategy = Strategy(
            strategy_id="strat_low",
            trigger_type=TriggerType.SCHEDULED,
            trigger_time=1000.0,
            current_load_rt=50.0,
            actions=actions,
            transition_plan=plan,
        )

        chillers = {
            "ch1": type("Ch", (), {"capacity_rt": 500.0})(),
        }

        result = check_safety(strategy, chillers=chillers, t_cw=30.0, current_time=1000.0)
        # 50/500 = 0.1 PLR, surge boundary at t_cw=30 is 0.2
        assert result.passed is False
        assert result.blocking is True
        assert len(result.failures) > 0


# ---------------------------------------------------------------------------
# TestRLWithPipeline
# ---------------------------------------------------------------------------

class TestRLWithPipeline:
    """Contextual Bandit with pipeline-derived features."""

    def test_feature_extraction_from_strategy_dict(self):
        """Extract features from a strategy dict (as from pipeline output)."""
        strategy_dict = {
            "strategy_id": "strat_features",
            "trigger_type": "scheduled",
            "current_load_rt": 600.0,
            "predicted_load_rt": 620.0,
            "actions": [
                {"seq": 1, "device": "ch1", "action": "start"},
                {"seq": 2, "device": "ch1", "action": "set_load", "value": 300.0},
                {"seq": 3, "device": "ch2", "action": "set_load", "value": 300.0},
            ],
            "transition_plan": {"total_duration_sec": 300.0, "phases": [], "abort_conditions": []},
            "expected_cop_improvement": 0.12,
            "expected_energy_saving_kwh_per_h": 45.0,
            "expected_carbon_saving_kg_per_h": 22.0,
        }

        features = extract_features(
            strategy=strategy_dict,
            current_load_rt=600.0,
            predicted_load_rt=620.0,
            outdoor_wb_temp=28.0,
            electricity_price=0.8,
            carbon_intensity=0.5,
        )

        assert features.shape == (FEATURE_DIM,)
        assert features.dtype == np.float64

        # load_ratio = 600/1500 = 0.4
        assert features[0] == pytest.approx(0.4, rel=0.01)
        # load_change_ratio = |620-600|/600 = 0.0333
        assert features[1] == pytest.approx(0.0333, rel=0.01)
        # outdoor_wb_norm = 28/40 = 0.7
        assert features[2] == pytest.approx(0.7, rel=0.01)
        # price_norm = 0.8/2.0 = 0.4
        assert features[3] == pytest.approx(0.4, rel=0.01)
        # carbon_norm = 0.5/1.0 = 0.5
        assert features[4] == pytest.approx(0.5, rel=0.01)
        # num_actions = 3/10 = 0.3
        assert features[5] == pytest.approx(0.3, rel=0.01)
        # num_start_actions = 1/5 = 0.2
        assert features[6] == pytest.approx(0.2, rel=0.01)
        # num_stop_actions = 0/5 = 0.0
        assert features[7] == 0.0
        # has_transition_plan = 1.0
        assert features[8] == 1.0
        # expected_cop_improvement = 0.12
        assert features[9] == pytest.approx(0.12, rel=0.01)
        # energy_saving_norm = 45/500 = 0.09
        assert features[10] == pytest.approx(0.09, rel=0.01)
        # carbon_saving_norm = 22/200 = 0.11
        assert features[11] == pytest.approx(0.11, rel=0.01)

    def test_feature_extraction_boundary_clipping(self):
        """Features are clipped to normalized ranges."""
        features = extract_features(
            strategy=None,
            current_load_rt=3000.0,  # way above 1500
            predicted_load_rt=0.0,
            outdoor_wb_temp=100.0,   # way above 40
            electricity_price=10.0,   # way above 2.0
            carbon_intensity=5.0,     # way above 1.0
        )
        # load_ratio should be clipped to 1.0
        assert features[0] == 1.0
        assert features[2] == 1.0
        assert features[3] == 1.0
        assert features[4] == 1.0

    def test_feature_extraction_empty_strategy(self):
        """Features with no strategy dict use default zeros."""
        features = extract_features(
            strategy={},
            current_load_rt=300.0,
            predicted_load_rt=300.0,
        )
        assert features.shape == (FEATURE_DIM,)
        assert features[5] == 0.0  # num_actions
        assert features[6] == 0.0  # num_starts
        assert features[8] == 0.0  # no transition plan
        assert features[9] == 0.0  # cop_improvement

    def test_bandit_creates_prediction(self):
        """Bandit produces a prediction from features."""
        bandit = ContextualBandit(epsilon=0.0)  # no exploration for deterministic test

        features = extract_features(
            current_load_rt=600.0,
            predicted_load_rt=620.0,
            outdoor_wb_temp=28.0,
        )

        prediction = bandit.predict(features)
        assert isinstance(prediction, BanditPrediction)
        assert prediction.action in ("approve", "reject")
        assert 0.0 <= prediction.confidence <= 1.0
        assert prediction.features is not None

    def test_bandit_updates_weights(self):
        """Bandit.update modifies weights after observing reward."""
        bandit = ContextualBandit(epsilon=0.0, learning_rate=0.01)

        features = extract_features(current_load_rt=600.0, predicted_load_rt=600.0)

        # Get initial weights
        initial_approve_weights = bandit.weights["approve"].copy()

        # Update with positive reward for approve
        bandit.update(features, "approve", reward=1.0)

        # Weights should have changed
        assert not np.allclose(initial_approve_weights, bandit.weights["approve"])

        # Training history should have one entry
        assert len(bandit.training_history) == 1

    def test_bandit_train_batch(self):
        """Bandit trains on a batch of examples."""
        bandit = ContextualBandit(epsilon=0.0, learning_rate=0.01)

        examples = []
        for load in [400.0, 500.0, 600.0, 700.0, 800.0]:
            features = extract_features(current_load_rt=load, predicted_load_rt=load)
            # Approve for moderate loads, reject for very high loads
            if load < 750:
                examples.append(TrainingExample(
                    features=features,
                    action_taken="approve",
                    reward=1.0,
                ))
            else:
                examples.append(TrainingExample(
                    features=features,
                    action_taken="reject",
                    reward=0.5,
                ))

        losses = bandit.train_batch(examples, epochs=3)
        assert len(losses) == 3

        # Loss should generally decrease or stay low
        for loss in losses:
            assert loss >= 0.0

    def test_bandit_after_training_prefers_approve_for_normal_load(self):
        """After training, bandit should learn to prefer approve for normal loads."""
        bandit = ContextualBandit(epsilon=0.0, learning_rate=0.1)

        # Train: approve gives +1 reward for 600RT
        for _ in range(20):
            features = extract_features(current_load_rt=600.0, predicted_load_rt=600.0)
            bandit.update(features, "approve", reward=1.0)
            bandit.update(features, "reject", reward=-1.0)

        # Predict on similar load
        features = extract_features(current_load_rt=600.0, predicted_load_rt=600.0)
        prediction = bandit.predict(features)

        # With epsilon=0, should predict approve
        assert prediction.action == "approve"
        # Score for approve should be higher than reject
        assert prediction.score_approve > prediction.score_reject

    def test_bandit_train_rejects_infeasible_loads(self):
        """After training on infeasible loads, bandit learns to reject."""
        bandit = ContextualBandit(epsilon=0.0, learning_rate=0.1)

        # Train: reject gives +1 for 1500RT, approve gives -1
        for _ in range(20):
            features = extract_features(current_load_rt=1500.0, predicted_load_rt=1500.0)
            bandit.update(features, "approve", reward=-1.0)
            bandit.update(features, "reject", reward=1.0)

        features = extract_features(current_load_rt=1500.0, predicted_load_rt=1500.0)
        prediction = bandit.predict(features)

        assert prediction.action == "reject"

    def test_bandit_serialization(self):
        """Bandit weights can be serialized and loaded."""
        bandit = ContextualBandit(epsilon=0.0)

        # Train a bit
        features = extract_features(current_load_rt=600.0, predicted_load_rt=600.0)
        bandit.update(features, "approve", reward=1.0)

        # Serialize
        weights_dict = bandit.get_weights()
        assert "approve" in weights_dict
        assert "reject" in weights_dict
        assert len(weights_dict["approve"]) == FEATURE_DIM

        # Load into new bandit
        bandit2 = ContextualBandit(epsilon=0.0)
        bandit2.load_weights(weights_dict)

        # Predictions should match
        features2 = extract_features(current_load_rt=600.0, predicted_load_rt=600.0)
        p1 = bandit.predict(features2)
        p2 = bandit2.predict(features2)
        assert np.allclose(p1.score_approve, p2.score_approve, atol=1e-8)

    def test_feature_names_match_dimension(self):
        """FEATURE_NAMES and FEATURE_DIM are consistent."""
        assert len(FEATURE_NAMES) == FEATURE_DIM
        assert FEATURE_DIM == 12

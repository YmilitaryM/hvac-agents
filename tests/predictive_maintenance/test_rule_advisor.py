import pytest

from services.agent.agent_service.predictive_maintenance.rule_advisor import (
    advise,
    ACTION_RULES,
)


class TestRuleAdvisor:
    """Tests for the advise function that maps degradation results to actions."""

    # ------------------------------------------------------------------
    # Triggering rules
    # ------------------------------------------------------------------

    def test_triggers_critical_cop_degradation_rule(self):
        """When cop_degradation_pct > 15, the critical COP rule fires."""
        result = advise({
            "cop_degradation_pct": 16.0,
            "approach_temp_drift_k": 0.0,
            "vibration_trend": 0.0,
        })
        actions = [r["action"] for r in result]
        assert any("tube cleaning" in a.lower() for a in actions)
        assert any("refrigerant charge" in a.lower() for a in actions)

    def test_triggers_degrading_cop_rule(self):
        """When cop_degradation_pct is between 7 and 15, the degrading COP rule fires."""
        result = advise({
            "cop_degradation_pct": 10.0,
            "approach_temp_drift_k": 0.0,
            "vibration_trend": 0.0,
        })
        actions = [r["action"] for r in result]
        assert any("condenser coil" in a.lower() for a in actions)

        # Verify both degrading and critical are included where applicable
        severities = [r["severity"] for r in result]
        assert "degrading" in severities

    def test_triggers_critical_approach_temp_rule(self):
        """When approach_temp_drift_k > 5.0, the critical approach temp rule fires."""
        result = advise({
            "cop_degradation_pct": 2.0,
            "approach_temp_drift_k": 6.0,
            "vibration_trend": 0.0,
        })
        actions = [r["action"] for r in result]
        assert any("cooling tower fill" in a.lower() for a in actions)
        severities = [r["severity"] for r in result]
        assert "critical" in severities

    def test_triggers_degrading_approach_temp_rule(self):
        """When approach_temp_drift_k between 3-5, the degrading approach temp rule fires."""
        result = advise({
            "cop_degradation_pct": 2.0,
            "approach_temp_drift_k": 4.0,
            "vibration_trend": 0.0,
        })
        actions = [r["action"] for r in result]
        assert any("monitor approach temperature" in a.lower() for a in actions)

    def test_triggers_vibration_rule(self):
        """When vibration_trend > 7.0, the critical vibration rule fires."""
        result = advise({
            "cop_degradation_pct": 2.0,
            "approach_temp_drift_k": 1.0,
            "vibration_trend": 8.5,
        })
        actions = [r["action"] for r in result]
        assert any("pump alignment" in a.lower() for a in actions)

    def test_triggers_multiple_rules(self):
        """When multiple thresholds are exceeded, multiple recommendations are generated."""
        result = advise({
            "cop_degradation_pct": 18.0,  # triggers both critical (>15) AND degrading (>7) COP rules
            "approach_temp_drift_k": 6.0,  # triggers critical (>5) AND degrading (>3) approach_temp rules
            "vibration_trend": 8.0,  # triggers vibration rule
        })
        # All 5 rules should fire
        assert len(result) == 5

    # ------------------------------------------------------------------
    # Not triggering
    # ------------------------------------------------------------------

    def test_no_rules_triggered_for_normal_values(self):
        """When all values are below thresholds, no recommendations are generated."""
        result = advise({
            "cop_degradation_pct": 2.0,
            "approach_temp_drift_k": 1.0,
            "vibration_trend": 3.0,
        })
        assert len(result) == 0
        assert isinstance(result, list)

    def test_exactly_at_threshold_does_not_trigger(self):
        """Values exactly at the threshold should NOT trigger (strict > comparison)."""
        result = advise({
            "cop_degradation_pct": 7.0,  # exactly at degrading threshold
            "approach_temp_drift_k": 3.0,  # exactly at degrading threshold
            "vibration_trend": 7.0,  # exactly at vibration threshold
        })
        assert len(result) == 0

    # ------------------------------------------------------------------
    # Edge cases
    # ------------------------------------------------------------------

    def test_empty_result_dict(self):
        """An empty dict should not raise errors and return empty list."""
        result = advise({})
        assert result == []

    def test_partial_result_dict(self):
        """A result dict missing some fields should only evaluate available fields."""
        result = advise({
            "cop_degradation_pct": 20.0,
            # approach_temp_drift_k missing
            # vibration_trend missing
        })
        # Only COP-related rules should fire (critical >15 and degrading >7)
        assert len(result) == 2
        actions = [r["action"] for r in result]
        assert any("tube cleaning" in a.lower() for a in actions)
        assert any("condenser coil" in a.lower() for a in actions)

    def test_zero_values_do_not_trigger(self):
        """Zero values are < thresholds and should not trigger."""
        result = advise({
            "cop_degradation_pct": 0.0,
            "approach_temp_drift_k": 0.0,
            "vibration_trend": 0.0,
        })
        assert len(result) == 0

    def test_negative_values_do_not_trigger(self):
        """Negative values (e.g. better-than-design COP) should not trigger."""
        result = advise({
            "cop_degradation_pct": -5.0,
            "approach_temp_drift_k": -2.0,
            "vibration_trend": -1.0,
        })
        assert len(result) == 0

    def test_return_structure(self):
        """Each recommendation must have 'action' and 'severity' keys."""
        result = advise({
            "cop_degradation_pct": 20.0,
            "approach_temp_drift_k": 6.0,
            "vibration_trend": 8.0,
        })
        for r in result:
            assert "action" in r
            assert "severity" in r
            assert isinstance(r["action"], str)
            assert r["severity"] in ("critical", "degrading")

    def test_severity_preserved_from_rule(self):
        """The severity in the recommendation should match the rule's severity."""
        result = advise({
            "cop_degradation_pct": 10.0,  # triggers degrading
            "approach_temp_drift_k": 1.0,
            "vibration_trend": 1.0,
        })
        assert len(result) == 1
        assert result[0]["severity"] == "degrading"

    def test_very_high_values_trigger_all_relevant_rules(self):
        """Extremely high values ensure all rules fire."""
        result = advise({
            "cop_degradation_pct": 100.0,
            "approach_temp_drift_k": 100.0,
            "vibration_trend": 100.0,
        })
        assert len(result) >= 3  # At minimum, the most permissive rules fire

    def test_advise_is_deterministic(self):
        """Multiple calls with same input should return same results."""
        input_data = {
            "cop_degradation_pct": 12.0,
            "approach_temp_drift_k": 4.5,
            "vibration_trend": 6.0,
        }
        result1 = advise(input_data)
        result2 = advise(input_data)
        assert result1 == result2

    def test_advise_does_not_mutate_input(self):
        """The advise function should not modify the input dict."""
        input_data = {
            "cop_degradation_pct": 20.0,
            "approach_temp_drift_k": 6.0,
            "vibration_trend": 8.0,
        }
        original = input_data.copy()
        advise(input_data)
        assert input_data == original


class TestActionRulesConfiguration:
    """Verify the ACTION_RULES configuration is well-formed."""

    def test_every_rule_has_required_keys(self):
        """Each rule must have condition, action, and severity."""
        for rule in ACTION_RULES:
            assert "condition" in rule
            assert "action" in rule
            assert "severity" in rule

    def test_every_condition_has_required_keys(self):
        """Each condition must have field, op, and value."""
        for rule in ACTION_RULES:
            cond = rule["condition"]
            assert "field" in cond
            assert "op" in cond
            assert "value" in cond
            assert cond["op"] == ">"

    def test_severity_values_are_valid(self):
        """Severity should be one of the expected levels."""
        for rule in ACTION_RULES:
            assert rule["severity"] in ("critical", "degrading")

    def test_rules_are_non_empty(self):
        """There should be rules defined."""
        assert len(ACTION_RULES) > 0

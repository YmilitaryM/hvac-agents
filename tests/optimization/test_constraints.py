import pytest
from src.schemas.equipment import ChillerState, EquipmentStatus
from src.simulation.chiller import CentrifugalChiller
from src.optimization.constraints import (
    surge_constraint,
    min_runtime_constraint,
    motor_start_interval,
    capacity_balance,
    check_all_constraints,
)


class TestSurgeConstraint:
    def test_plr_above_surge_passes(self):
        chiller = CentrifugalChiller(name="ch1", capacity_rt=500, min_plr=0.2)
        ok, msg = surge_constraint(chiller, plr=0.6, t_cw=30.0)
        assert ok is True

    def test_plr_below_surge_fails(self):
        chiller = CentrifugalChiller(name="ch1", capacity_rt=500, min_plr=0.2)
        ok, msg = surge_constraint(chiller, plr=0.1, t_cw=30.0)
        assert ok is False
        assert "surge" in msg.lower()

    def test_plr_zero_passes(self):
        chiller = CentrifugalChiller(name="ch1", capacity_rt=500, min_plr=0.2)
        ok, msg = surge_constraint(chiller, plr=0.0, t_cw=30.0)
        assert ok is True


class TestMinRuntimeConstraint:
    def test_first_start_passes(self):
        ok, msg = min_runtime_constraint(
            device_name="ch1", action="start",
            last_start_time=None, last_stop_time=None,
            current_time=1000.0, min_runtime=1800.0, min_offtime=900.0,
        )
        assert ok is True

    def test_too_soon_after_start_fails(self):
        ok, msg = min_runtime_constraint(
            device_name="ch1", action="stop",
            last_start_time=800.0, last_stop_time=None,
            current_time=1000.0, min_runtime=1800.0, min_offtime=900.0,
        )
        assert ok is False

    def test_after_min_runtime_passes(self):
        ok, msg = min_runtime_constraint(
            device_name="ch1", action="stop",
            last_start_time=0.0, last_stop_time=None,
            current_time=3600.0, min_runtime=1800.0, min_offtime=900.0,
        )
        assert ok is True


class TestMotorStartInterval:
    def test_no_recent_starts_passes(self):
        recent_starts = []  # no recent motor starts
        ok, msg = motor_start_interval(
            device_name="ch1", current_time=1000.0,
            recent_motor_starts=recent_starts, min_interval=30.0,
        )
        assert ok is True

    def test_recent_start_fails(self):
        recent_starts = [("ch2", 985.0)]  # 15 seconds ago
        ok, msg = motor_start_interval(
            device_name="ch1", current_time=1000.0,
            recent_motor_starts=recent_starts, min_interval=30.0,
        )
        assert ok is False


class TestCapacityBalance:
    def test_capacity_covers_load_passes(self):
        chiller_capacities = {"ch1": 500, "ch2": 500}
        ok, msg = capacity_balance(chiller_capacities, total_load_rt=800, margin=0.1)
        assert ok is True

    def test_capacity_shortfall_fails(self):
        chiller_capacities = {"ch1": 500}
        ok, msg = capacity_balance(chiller_capacities, total_load_rt=600, margin=0.1)
        assert ok is False

    def test_exact_match_passes(self):
        chiller_capacities = {"ch1": 500}
        ok, msg = capacity_balance(chiller_capacities, total_load_rt=500, margin=0.0)
        assert ok is True


class TestCheckAllConstraints:
    def test_all_pass_returns_empty_list(self):
        chiller = CentrifugalChiller(name="ch1", capacity_rt=500, min_plr=0.2)
        failures = check_all_constraints(
            chiller_loads={"ch1": 300},
            chillers={"ch1": chiller},
            t_cw=30.0,
            current_time=1000.0,
            recent_motor_starts=[],
        )
        assert len(failures) == 0

    def test_surge_violation_detected(self):
        chiller = CentrifugalChiller(name="ch1", capacity_rt=500, min_plr=0.2)
        failures = check_all_constraints(
            chiller_loads={"ch1": 50},
            chillers={"ch1": chiller},
            t_cw=30.0,
            current_time=1000.0,
            recent_motor_starts=[],
        )
        assert len(failures) >= 1

import pytest
from edge.engine.controller import SafetyGate, PIDController, Interlock


class TestSafetyGate:
    def test_passes_valid_value(self):
        gate = SafetyGate(limits={"CH-1.cop": (3.0, 8.0)})
        assert gate.check("CH-1.cop", 5.5) is True

    def test_rejects_out_of_range(self):
        gate = SafetyGate(limits={"CH-1.cop": (3.0, 8.0)})
        assert gate.check("CH-1.cop", 1.0) is False

    def test_unknown_param_passes(self):
        gate = SafetyGate(limits={})
        assert gate.check("unknown.param", 999) is True


class TestPIDController:
    def test_pid_compute(self):
        pid = PIDController(kp=2.0, ki=0.1, kd=0.05, setpoint=7.0)
        output = pid.compute(6.0, dt=1.0)
        assert output > 0  # Below setpoint -> positive output

    def test_pid_converges(self):
        pid = PIDController(kp=1.0, ki=0.1, kd=0.0, setpoint=5.0, output_min=-10, output_max=10)
        value = 0.0
        for _ in range(50):
            output = pid.compute(value, dt=1.0)
            value += output * 0.1
        assert abs(value - 5.0) < 0.5


class TestInterlock:
    def test_chiller_pump_interlock(self):
        il = Interlock(rules=[
            {"if": "CH-1.status == 'off'", "then": "P-1.cmd = 0"},
        ])
        actions = il.evaluate({"CH-1.status": "off", "P-1.cmd": 1})
        assert actions == ["P-1.cmd = 0"]

    def test_no_action_when_ok(self):
        il = Interlock(rules=[
            {"if": "CH-1.status == 'off'", "then": "P-1.cmd = 0"},
        ])
        actions = il.evaluate({"CH-1.status": "on", "P-1.cmd": 1})
        assert actions == []

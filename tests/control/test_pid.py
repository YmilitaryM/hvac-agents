import pytest
from src.control.pid import PIDController, PIDParams


class TestPIDProportional:
    def test_proportional_response(self):
        """Error=5, kp=2, ki=0, kd=0 => output ~= 10."""
        params = PIDParams(kp=2.0, ki=0.0, kd=0.0, setpoint=10.0)
        pid = PIDController(params)
        output = pid.update(measurement=5.0)  # error = 10 - 5 = 5, output = 2 * 5 = 10
        assert abs(output - 10.0) < 0.01

    def test_proportional_zero_error(self):
        params = PIDParams(kp=2.0, ki=0.1, kd=0.05, setpoint=10.0)
        pid = PIDController(params)
        output = pid.update(measurement=10.0)  # error = 0
        assert output == 0.0


class TestPIDIntegral:
    def test_integral_accumulates(self):
        """Multiple updates with constant error => output increases."""
        params = PIDParams(kp=0.0, ki=0.5, kd=0.0, setpoint=10.0)
        pid = PIDController(params)
        # First call initializes; integral is set to 0, output = 0
        out1 = pid.update(measurement=5.0, dt=1.0)  # error=5, integral starts at 0 (initialized), output = 0
        # After first call: _integral = 0 + 5*1 = 5 => i_term = 0.5 * 5 = 2.5
        # BUT wait - on first call when not initialized, _integral = 0.0, p_term=0, i_term=0, d_term=0
        # After this call, _integral += 5 * 1 = 5
        out2 = pid.update(measurement=5.0, dt=1.0)  # integral now 5, i_term = 2.5
        out3 = pid.update(measurement=5.0, dt=1.0)  # integral now 10, i_term = 5.0
        assert out3 > out2

    def test_integral_term_accumulation(self):
        """Multiple updates with constant error produce increasing output."""
        params = PIDParams(kp=0.0, ki=1.0, kd=0.0, setpoint=10.0)
        pid = PIDController(params)
        out1 = pid.update(measurement=10.0, dt=1.0)  # error=0, initializes
        out2 = pid.update(measurement=0.0, dt=1.0)   # error=10, integral = 10, i_term = 10
        out3 = pid.update(measurement=0.0, dt=1.0)   # error=10, integral = 20, i_term = 20
        assert out3 > out2 > out1


class TestPIDDerivative:
    def test_derivative_response(self):
        """Rapid change => derivative term contributes."""
        params = PIDParams(kp=0.0, ki=0.0, kd=0.5, setpoint=10.0)
        pid = PIDController(params)
        # First call: prev_error = 0, error = 5, d_term = 0.5 * (5-0)/1 = 2.5
        # But on first call _initialized=False, so integral is set to 0 but derivative is still computed
        out1 = pid.update(measurement=5.0, dt=1.0)  # error=5, d_term = 0.5*(5-0)/1 = 2.5
        # Second call: prev_error=5, error=5, d_term = 0.5*(5-5)/1 = 0
        out2 = pid.update(measurement=5.0, dt=1.0)  # error same, d_term = 0
        assert out1 > out2  # derivative contributed on first call


class TestPIDClamping:
    def test_output_clamping_min(self):
        params = PIDParams(kp=1.0, ki=0.0, kd=0.0, setpoint=10.0,
                           output_min=0.0, output_max=100.0)
        pid = PIDController(params)
        output = pid.update(measurement=20.0)  # error = -10, output = -10, clamped to 0
        assert output == 0.0

    def test_output_clamping_max(self):
        params = PIDParams(kp=100.0, ki=0.0, kd=0.0, setpoint=10.0,
                           output_min=0.0, output_max=50.0)
        pid = PIDController(params)
        output = pid.update(measurement=0.0)  # error = 10, output = 1000, clamped to 50
        assert output == 50.0


class TestPIDAntiWindup:
    def test_anti_windup(self):
        """Saturated output prevents integral windup."""
        params = PIDParams(kp=1.0, ki=1.0, kd=0.0, setpoint=10.0,
                           output_min=0.0, output_max=10.0)
        pid = PIDController(params)
        # Drive output to max: measurement=0, error=10
        # First call: init, integral=0, p_term=10, output=10 (clamped)
        pid.update(measurement=0.0, dt=1.0)  # output saturated at 10
        # Second call: error=10, integral should NOT accumulate because prev_output >= output_max and error > 0
        pid.update(measurement=0.0, dt=1.0)
        # Integral should still be 0 due to anti-windup
        assert pid._integral == 0.0

    def test_no_anti_windup_when_disabled(self):
        """Without anti-windup, integral continues accumulating even when saturated."""
        params = PIDParams(kp=1.0, ki=1.0, kd=0.0, setpoint=10.0,
                           output_min=0.0, output_max=10.0, anti_windup=False)
        pid = PIDController(params)
        pid.update(measurement=0.0, dt=1.0)  # init, integral starts at 0
        pid.update(measurement=0.0, dt=1.0)  # error=10, integral += 10 = 10
        assert pid._integral == 10.0


class TestPIDReset:
    def test_reset_clears_state(self):
        """Reset then update => starts fresh."""
        params = PIDParams(kp=1.0, ki=0.5, kd=0.0, setpoint=10.0)
        pid = PIDController(params)
        pid.update(measurement=0.0, dt=1.0)  # init
        pid.update(measurement=0.0, dt=1.0)  # integral now non-zero
        assert pid._integral != 0.0

        pid.reset()
        assert pid._integral == 0.0
        assert pid._prev_error == 0.0
        assert pid._prev_output == 0.0
        assert pid._initialized is False

        # After reset, first call should initialize again
        out = pid.update(measurement=0.0, dt=1.0)
        assert pid._initialized is True


class TestPIDSetpoint:
    def test_setpoint_change(self):
        """Changing setpoint changes error."""
        params = PIDParams(kp=1.0, ki=0.0, kd=0.0, setpoint=10.0)
        pid = PIDController(params)
        out1 = pid.update(measurement=5.0)  # error=5, out=5
        pid.set_setpoint(20.0)
        out2 = pid.update(measurement=5.0)  # error=15, out=15
        assert out2 > out1


class TestPIDEdgeCases:
    def test_zero_dt_handled(self):
        """dt=0 doesn't crash."""
        params = PIDParams(kp=1.0, ki=0.1, kd=0.05, setpoint=10.0)
        pid = PIDController(params)
        output = pid.update(measurement=5.0, dt=0.0)
        # Should not crash, d_term should be 0
        assert isinstance(output, float)

    def test_default_params(self):
        pid = PIDController()
        assert pid.params.kp == 1.0
        assert pid.params.ki == 0.1
        assert pid.params.kd == 0.05

    def test_output_clamping(self):
        """Output respects min/max bounds."""
        params = PIDParams(kp=100.0, ki=100.0, kd=0.0, setpoint=10.0,
                           output_min=0.0, output_max=10.0)
        pid = PIDController(params)
        # Multiple updates should keep output within bounds
        for _ in range(10):
            output = pid.update(measurement=0.0, dt=1.0)
            assert 0.0 <= output <= 10.0

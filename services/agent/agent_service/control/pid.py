"""PID controller with anti-windup for chiller plant parameter control."""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class PIDParams:
    """PID controller parameters."""
    kp: float = 1.0  # proportional gain
    ki: float = 0.1  # integral gain
    kd: float = 0.05  # derivative gain
    setpoint: float = 0.0
    output_min: float = 0.0
    output_max: float = 100.0
    anti_windup: bool = True


class PIDController:
    """PID controller with anti-windup.

    Used for fine-tuning temperature, pressure, and flow setpoints
    in the chiller plant control layer.
    """

    def __init__(self, params: Optional[PIDParams] = None):
        self.params = params or PIDParams()
        self._integral: float = 0.0
        self._prev_error: float = 0.0
        self._prev_output: float = 0.0
        self._initialized: bool = False

    def reset(self) -> None:
        """Reset controller state."""
        self._integral = 0.0
        self._prev_error = 0.0
        self._prev_output = 0.0
        self._initialized = False

    def update(self, measurement: float, dt: float = 1.0) -> float:
        """Compute control output for a measurement.

        Args:
            measurement: Current process value.
            dt: Time step in seconds.

        Returns:
            Control output value.
        """
        error = self.params.setpoint - measurement

        # Proportional
        p_term = self.params.kp * error

        # Integral with anti-windup
        if not self._initialized:
            self._integral = 0.0
            self._initialized = True
        else:
            self._integral += error * dt

            # Anti-windup: don't accumulate integral if output is saturated
            if self.params.anti_windup:
                if self._prev_output >= self.params.output_max and error > 0:
                    self._integral -= error * dt  # unwind
                elif self._prev_output <= self.params.output_min and error < 0:
                    self._integral -= error * dt  # unwind

        i_term = self.params.ki * self._integral

        # Derivative
        if dt > 0:
            d_term = self.params.kd * (error - self._prev_error) / dt
        else:
            d_term = 0.0

        output = p_term + i_term + d_term
        output = max(self.params.output_min, min(self.params.output_max, output))

        self._prev_error = error
        self._prev_output = output

        return output

    def set_setpoint(self, setpoint: float) -> None:
        """Update the setpoint without resetting controller state."""
        self.params.setpoint = setpoint

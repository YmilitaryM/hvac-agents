"""Deadband and rate limiting for stable parameter adjustments."""

from dataclasses import dataclass
from typing import Optional, Tuple


@dataclass
class DeadbandLimiter:
    """Applies deadband filtering to a signal.

    If the change is within the deadband, returns the current value
    (no change). If outside, passes through the target value.
    """
    deadband: float = 0.5  # +/- deadband range

    def apply(self, current_value: float, target_value: float) -> Tuple[float, bool]:
        """Apply deadband filter.

        Returns:
            (output_value, was_filtered) where was_filtered is True if
            the change was suppressed by deadband.
        """
        if abs(target_value - current_value) <= self.deadband:
            return current_value, True
        return target_value, False


@dataclass
class RateLimiter:
    """Limits the rate of change of a signal.

    Ensures output changes no faster than max_rate units per second.
    """
    max_rate: float = 1.0  # max change per second
    current_value: float = 0.0

    def apply(self, target_value: float, dt: float = 1.0) -> Tuple[float, bool]:
        """Apply rate limiting.

        Args:
            target_value: Desired value.
            dt: Time since last update in seconds.

        Returns:
            (output_value, was_limited) where was_limited is True if
            the rate limiter clipped the change.
        """
        if dt <= 0:
            return target_value, False

        max_change = self.max_rate * dt
        delta = target_value - self.current_value

        if abs(delta) <= max_change:
            self.current_value = target_value
            return target_value, False
        else:
            limited = self.current_value + (max_change if delta > 0 else -max_change)
            self.current_value = limited
            return limited, True

    def reset(self, value: float = 0.0) -> None:
        """Reset the current value."""
        self.current_value = value

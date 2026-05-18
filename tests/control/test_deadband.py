import pytest
from src.control.deadband import DeadbandLimiter, RateLimiter


class TestDeadband:
    def test_deadband_within_range(self):
        """Change within deadband => filtered, returns current."""
        limiter = DeadbandLimiter(deadband=0.5)
        value, filtered = limiter.apply(current_value=10.0, target_value=10.3)
        assert value == 10.0
        assert filtered is True

    def test_deadband_outside_range(self):
        """Change outside deadband => passes through."""
        limiter = DeadbandLimiter(deadband=0.5)
        value, filtered = limiter.apply(current_value=10.0, target_value=11.0)
        assert value == 11.0
        assert filtered is False

    def test_deadband_exact_boundary(self):
        """Change == deadband => filtered."""
        limiter = DeadbandLimiter(deadband=0.5)
        value, filtered = limiter.apply(current_value=10.0, target_value=10.5)
        assert value == 10.0
        assert filtered is True

    def test_deadband_exact_boundary_negative(self):
        """Negative change at exact deadband boundary => filtered."""
        limiter = DeadbandLimiter(deadband=0.5)
        value, filtered = limiter.apply(current_value=10.0, target_value=9.5)
        assert value == 10.0
        assert filtered is True

    def test_deadband_just_outside(self):
        """Change just outside deadband => passes through."""
        limiter = DeadbandLimiter(deadband=0.5)
        value, filtered = limiter.apply(current_value=10.0, target_value=10.51)
        assert value == 10.51
        assert filtered is False

    def test_deadband_no_change(self):
        """Zero change => filtered."""
        limiter = DeadbandLimiter(deadband=0.5)
        value, filtered = limiter.apply(current_value=10.0, target_value=10.0)
        assert value == 10.0
        assert filtered is True


class TestRateLimiter:
    def test_rate_limiter_applies(self):
        """Large change => limited to max_rate."""
        limiter = RateLimiter(max_rate=1.0, current_value=0.0)
        value, limited = limiter.apply(target_value=10.0, dt=1.0)
        assert value == 1.0
        assert limited is True

    def test_rate_limiter_no_limit(self):
        """Small change => no limiting."""
        limiter = RateLimiter(max_rate=5.0, current_value=0.0)
        value, limited = limiter.apply(target_value=2.0, dt=1.0)
        assert value == 2.0
        assert limited is False

    def test_rate_limiter_reset(self):
        """Reset clears current value."""
        limiter = RateLimiter(max_rate=1.0, current_value=5.0)
        limiter.reset(0.0)
        assert limiter.current_value == 0.0

    def test_rate_limiter_reset_default(self):
        """Reset with no argument sets value to 0.0."""
        limiter = RateLimiter(max_rate=1.0, current_value=5.0)
        limiter.reset()
        assert limiter.current_value == 0.0

    def test_rate_limiter_negative_change(self):
        """Large negative change => limited in negative direction."""
        limiter = RateLimiter(max_rate=2.0, current_value=10.0)
        value, limited = limiter.apply(target_value=0.0, dt=1.0)
        assert value == 8.0
        assert limited is True

    def test_rate_limiter_zero_dt(self):
        """dt=0 should return target without modifying current_value."""
        limiter = RateLimiter(max_rate=1.0, current_value=5.0)
        value, limited = limiter.apply(target_value=10.0, dt=0.0)
        assert value == 10.0
        assert limited is False

    def test_rate_limiter_multiple_steps(self):
        """Multiple small steps eventually reach target."""
        limiter = RateLimiter(max_rate=1.0, current_value=0.0)
        for _ in range(10):
            val, _ = limiter.apply(target_value=10.0, dt=1.0)
        assert val == 10.0

    def test_rate_limiter_exact_boundary(self):
        """Change exactly at max_rate boundary => no limit."""
        limiter = RateLimiter(max_rate=1.0, current_value=0.0)
        value, limited = limiter.apply(target_value=1.0, dt=1.0)
        assert value == 1.0
        assert limited is False

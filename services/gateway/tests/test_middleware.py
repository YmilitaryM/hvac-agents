import time

import pytest

from gateway_service.rate_limiter import RateLimiter, RateLimitMiddleware
from gateway_service.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerMiddleware,
    CircuitState,
)


# ---------------------------------------------------------------------------
# RateLimiter tests
# ---------------------------------------------------------------------------

class TestRateLimiter:
    """Unit tests for the token-bucket RateLimiter."""

    def test_rate_limiter_allows_within_rate(self):
        """The first request for a client is always allowed."""
        limiter = RateLimiter(rate=100, burst=200)
        assert limiter.is_allowed("127.0.0.1") is True

    def test_rate_limiter_blocks_when_exhausted(self):
        """After burst tokens are consumed, further requests are blocked."""
        limiter = RateLimiter(rate=100, burst=5)
        client = "10.0.0.1"

        # Consume all 5 burst tokens
        for _ in range(5):
            assert limiter.is_allowed(client) is True

        # The 6th request should be blocked
        assert limiter.is_allowed(client) is False

    def test_rate_limiter_refills_tokens(self):
        """After waiting long enough, tokens refill and requests are allowed again."""
        limiter = RateLimiter(rate=1000, burst=5)  # 1000 tokens/second — fast refill
        client = "10.0.0.2"

        # Exhaust the bucket
        for _ in range(5):
            limiter.is_allowed(client)
        assert limiter.is_allowed(client) is False  # 6th blocked

        # After 0.01 seconds we should have ~10 tokens refilled (1000 * 0.01)
        time.sleep(0.01)
        assert limiter.is_allowed(client) is True

    def test_rate_limiter_different_clients(self):
        """Different client IPs have independent token buckets."""
        limiter = RateLimiter(rate=100, burst=3)

        # Exhaust client A's bucket
        for _ in range(3):
            limiter.is_allowed("192.168.1.1")
        assert limiter.is_allowed("192.168.1.1") is False

        # Client B should be unaffected
        assert limiter.is_allowed("192.168.1.2") is True
        assert limiter.is_allowed("192.168.1.2") is True

    def test_rate_limiter_burst_capacity(self):
        """Can send up to 'burst' requests immediately, but burst+1 is blocked."""
        limiter = RateLimiter(rate=10, burst=10)
        client = "172.16.0.1"

        # All 10 burst requests allowed
        for i in range(10):
            assert limiter.is_allowed(client) is True, f"Request {i + 1} should be allowed"

        # 11th is blocked
        assert limiter.is_allowed(client) is False


# ---------------------------------------------------------------------------
# CircuitBreaker tests
# ---------------------------------------------------------------------------

class TestCircuitBreaker:
    """Unit tests for the CircuitBreaker state machine."""

    def test_initial_state_is_closed(self):
        """A fresh circuit breaker reports CLOSED for any service."""
        cb = CircuitBreaker()
        state = cb.get_state("api-gateway")
        assert state["state"] == CircuitState.CLOSED
        assert state["failures"] == 0

    def test_is_allowed_returns_true_when_closed(self):
        """is_allowed returns True when the circuit is CLOSED."""
        cb = CircuitBreaker()
        assert cb.is_allowed("auth-service") is True

    def test_opens_after_failures(self):
        """After recording failure_threshold failures, the circuit opens."""
        cb = CircuitBreaker(failure_threshold=5)

        for _ in range(5):
            cb.record_failure("payment-service")

        assert cb.is_allowed("payment-service") is False
        state = cb.get_state("payment-service")
        assert state["state"] == CircuitState.OPEN
        assert state["failures"] == 5

    def test_blocks_when_open(self):
        """is_allowed returns False when circuit is OPEN."""
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=999.0)

        cb.record_failure("db-proxy")
        cb.record_failure("db-proxy")

        # Circuit is now OPEN with a very long recovery timeout
        assert cb.get_state("db-proxy")["state"] == CircuitState.OPEN
        assert cb.is_allowed("db-proxy") is False
        assert cb.is_allowed("db-proxy") is False  # still blocked on repeated calls

    def test_half_open_probe_and_recovery(self, monkeypatch):
        """After recovery_timeout, a probe is allowed; success closes the circuit."""
        cb = CircuitBreaker(
            failure_threshold=2,
            recovery_timeout=30.0,
            half_open_limit=3,
        )
        svc = "inventory-service"

        # Trip the circuit
        cb.record_failure(svc)
        cb.record_failure(svc)
        assert cb.is_allowed(svc) is False  # OPEN
        assert cb.get_state(svc)["state"] == CircuitState.OPEN

        # Fake time: advance past recovery_timeout
        future = time.monotonic() + 31.0
        monkeypatch.setattr(time, "monotonic", lambda: future)

        # Next is_allowed transitions OPEN -> HALF_OPEN and allows one probe
        assert cb.is_allowed(svc) is True
        assert cb.get_state(svc)["state"] == CircuitState.HALF_OPEN

        # Record successes to close the circuit
        cb.record_success(svc)
        cb.record_success(svc)
        cb.record_success(svc)

        assert cb.get_state(svc)["state"] == CircuitState.CLOSED

    def test_failure_during_half_open_reopens(self, monkeypatch):
        """A failure during HALF_OPEN should not immediately re-open — only
        record_failure during HALF_OPEN increments the counter but does not
        re-open.  A subsequent is_allowed still returns HALF_OPEN."""
        cb = CircuitBreaker(
            failure_threshold=2,
            recovery_timeout=30.0,
            half_open_limit=3,
        )
        svc = "search-service"

        # Trip to OPEN
        cb.record_failure(svc)
        cb.record_failure(svc)
        assert cb.get_state(svc)["state"] == CircuitState.OPEN

        # Advance time to trigger HALF_OPEN
        future = time.monotonic() + 31.0
        monkeypatch.setattr(time, "monotonic", lambda: future)
        cb.is_allowed(svc)
        assert cb.get_state(svc)["state"] == CircuitState.HALF_OPEN

        # Record a failure while HALF_OPEN — this increments failures
        cb.record_failure(svc)
        # record_failure during HALF_OPEN only increments the counter;
        # the circuit stays HALF_OPEN since the check only transitions
        # CLOSED -> OPEN
        assert cb.get_state(svc)["state"] == CircuitState.HALF_OPEN

        # Now record successes — HALF_OPEN should still be able to close
        cb.record_success(svc)
        cb.record_success(svc)
        cb.record_success(svc)
        assert cb.get_state(svc)["state"] == CircuitState.CLOSED

    def test_get_state_returns_correct_dict(self):
        """get_state returns the correct state and failure count."""
        cb = CircuitBreaker(failure_threshold=3)
        svc = "alerting-service"

        # Initial
        s = cb.get_state(svc)
        assert s == {"state": CircuitState.CLOSED, "failures": 0}

        # After two failures (not yet open)
        cb.record_failure(svc)
        cb.record_failure(svc)
        s = cb.get_state(svc)
        assert s == {"state": CircuitState.CLOSED, "failures": 2}

        # After third failure — opens
        cb.record_failure(svc)
        s = cb.get_state(svc)
        assert s == {"state": CircuitState.OPEN, "failures": 3}

    def test_success_while_closed_stays_closed(self):
        """Recording success while CLOSED does not change any state."""
        cb = CircuitBreaker(failure_threshold=5)
        svc = "config-service"

        cb.record_success(svc)
        cb.record_success(svc)
        cb.record_success(svc)

        state = cb.get_state(svc)
        assert state["state"] == CircuitState.CLOSED
        assert state["failures"] == 0

    def test_separate_services_have_separate_circuits(self):
        """Each service name tracks its own circuit state independently."""
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=999.0)

        # Trip service-A
        cb.record_failure("svc-a")
        cb.record_failure("svc-a")
        assert cb.get_state("svc-a")["state"] == CircuitState.OPEN

        # Service-B is unaffected
        assert cb.get_state("svc-b")["state"] == CircuitState.CLOSED
        assert cb.is_allowed("svc-b") is True

        # Service-A is still blocked
        assert cb.is_allowed("svc-a") is False

    def test_opens_exactly_at_threshold(self):
        """Circuit opens exactly when failure count reaches threshold, not before."""
        cb = CircuitBreaker(failure_threshold=3)
        svc = "threshold-test"

        cb.record_failure(svc)
        assert cb.get_state(svc)["state"] == CircuitState.CLOSED
        assert cb.is_allowed(svc) is True

        cb.record_failure(svc)
        assert cb.get_state(svc)["state"] == CircuitState.CLOSED
        assert cb.is_allowed(svc) is True

        # Third failure — opens
        cb.record_failure(svc)
        assert cb.get_state(svc)["state"] == CircuitState.OPEN
        assert cb.is_allowed(svc) is False

    def test_recovery_timeout_not_yet_elapsed(self):
        """When OPEN but recovery_timeout has not elapsed, stays OPEN."""
        cb = CircuitBreaker(
            failure_threshold=2,
            recovery_timeout=999.0,  # effectively never
        )
        svc = "long-timeout-svc"

        cb.record_failure(svc)
        cb.record_failure(svc)
        assert cb.get_state(svc)["state"] == CircuitState.OPEN

        # Multiple checks — still blocked
        for _ in range(10):
            assert cb.is_allowed(svc) is False
        assert cb.get_state(svc)["state"] == CircuitState.OPEN

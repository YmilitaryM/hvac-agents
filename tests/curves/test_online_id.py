import pytest
import numpy as np
from src.curves.online_id import RecursiveLeastSquares


class TestRecursiveLeastSquares:
    @pytest.fixture
    def rls(self):
        return RecursiveLeastSquares(n_params=3, forgetting_factor=0.99)

    def test_initial_parameters(self, rls):
        assert rls.theta.shape == (3,)
        assert np.allclose(rls.theta, np.zeros(3))

    def test_single_update(self, rls):
        x = np.array([1.0, 0.5, 0.3])
        y = 2.5
        rls.update(x, y)
        assert not np.allclose(rls.theta, np.zeros(3))

    def test_convergence_to_known_coeffs(self):
        np.random.seed(42)
        true_theta = np.array([1.5, -0.8, 0.3])
        rls = RecursiveLeastSquares(n_params=3, forgetting_factor=0.995)

        for _ in range(200):
            x = np.random.uniform(-1, 1, 3)
            y = true_theta @ x + np.random.normal(0, 0.01)
            rls.update(x, y)

        assert np.allclose(rls.theta, true_theta, atol=0.05)

    def test_forgetting_factor(self):
        rls_high = RecursiveLeastSquares(n_params=2, forgetting_factor=0.95)
        rls_low = RecursiveLeastSquares(n_params=2, forgetting_factor=1.0)
        x = np.array([1.0, 0.5])

        for _ in range(50):
            rls_high.update(x, 3.0)
            rls_low.update(x, 3.0)

        # Both should converge to the same steady state for static data
        rls_high.update(np.array([1.0, 2.0]), 0.0)
        rls_low.update(np.array([1.0, 2.0]), 0.0)
        # After a sudden change, high forgetting factor adapts faster
        assert not np.allclose(rls_high.theta, rls_low.theta)

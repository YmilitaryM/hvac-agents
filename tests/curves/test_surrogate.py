import pytest
import numpy as np
from src.curves.surrogate import ChillerSurrogate, fit_chiller_surrogate


class TestChillerSurrogate:
    @pytest.fixture
    def surrogate(self):
        return ChillerSurrogate(
            coeffs=[3.0, 2.0, -1.0, 0.1, -0.05, -0.002, -0.01]
        )

    def test_predict_scalar(self, surrogate):
        cop = surrogate.predict(plr=0.75, t_chw=7.0, t_cw=30.0)
        assert cop > 0

    def test_predict_batch(self, surrogate):
        plrs = np.array([0.5, 0.75, 1.0])
        t_chws = np.array([7.0, 7.0, 7.0])
        t_cws = np.array([30.0, 30.0, 30.0])
        cops = surrogate.predict(plrs, t_chws, t_cws)
        assert cops.shape == (3,)
        assert all(c > 0 for c in cops)


class TestFitChillerSurrogate:
    def test_fit_from_data(self):
        np.random.seed(42)
        n = 500
        plrs = np.random.uniform(0.3, 1.0, n)
        t_chws = np.random.uniform(5, 10, n)
        t_cws = np.random.uniform(26, 35, n)
        true_cops = (4.5 + 1.5 * plrs - 0.8 * plrs**2
                     + 0.12 * t_chws - 0.04 * t_cws
                     - 0.01 * t_cws**2 - 0.02 * plrs * t_cws)
        true_cops += np.random.normal(0, 0.05, n)

        surrogate = fit_chiller_surrogate(plrs, t_chws, t_cws, true_cops)
        predicted = surrogate.predict(plrs, t_chws, t_cws)
        rmse = np.sqrt(np.mean((predicted - true_cops) ** 2))
        assert rmse < 0.2

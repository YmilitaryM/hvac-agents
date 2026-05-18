import numpy as np


class RecursiveLeastSquares:
    """Recursive Least Squares with forgetting factor for online parameter identification"""

    def __init__(self, n_params: int, forgetting_factor: float = 0.99):
        self.n_params = n_params
        self.forgetting_factor = forgetting_factor
        self.theta = np.zeros(n_params)
        self.P = np.eye(n_params) * 1000.0

    def update(self, x: np.ndarray, y: float) -> None:
        x = np.atleast_1d(np.asarray(x, dtype=np.float64))
        lam = self.forgetting_factor

        # Gain: K = P * x / (lam + x^T * P * x)
        Px = self.P @ x
        denom = lam + x @ Px
        K = Px / denom

        # Update theta: theta += K * (y - x^T * theta)
        error = y - x @ self.theta
        self.theta += K * error

        # Update P: P = (P - K * x^T * P) / lam
        self.P = (self.P - np.outer(K, Px)) / lam

    def predict(self, x: np.ndarray) -> float:
        x = np.atleast_1d(np.asarray(x, dtype=np.float64))
        return float(x @ self.theta)

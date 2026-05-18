import numpy as np
from numpy.linalg import lstsq


class ChillerSurrogate:
    """Chiller COP polynomial surrogate model

    COP(P, T_e, T_c) = a0 + a1*P + a2*P^2 + a3*T_e + a4*T_c + a5*T_c^2 + a6*P*T_c
    P = PLR (0~1), T_e = chw supply temp, T_c = cw entering temp
    """

    def __init__(self, coeffs: list[float]):
        self.coeffs = np.array(coeffs, dtype=np.float64)
        if len(self.coeffs) != 7:
            raise ValueError(f"Expected 7 coefficients, got {len(self.coeffs)}")

    def predict(self, plr, t_chw, t_cw) -> np.ndarray:
        plr = np.atleast_1d(np.asarray(plr, dtype=np.float64))
        t_chw = np.atleast_1d(np.asarray(t_chw, dtype=np.float64))
        t_cw = np.atleast_1d(np.asarray(t_cw, dtype=np.float64))
        X = np.column_stack([
            np.ones_like(plr), plr, plr**2, t_chw, t_cw, t_cw**2, plr * t_cw,
        ])
        result = X @ self.coeffs
        return result if len(result) > 1 else result[0]

    def to_dict(self) -> dict:
        return {"coeffs": self.coeffs.tolist()}

    @classmethod
    def from_dict(cls, d: dict) -> "ChillerSurrogate":
        return cls(coeffs=d["coeffs"])


def fit_chiller_surrogate(
    plrs: np.ndarray, t_chws: np.ndarray, t_cws: np.ndarray, cops: np.ndarray,
) -> ChillerSurrogate:
    """Least-squares fit of chiller surrogate model"""
    X = np.column_stack([
        np.ones_like(plrs), plrs, plrs**2, t_chws, t_cws, t_cws**2, plrs * t_cws,
    ])
    coeffs, _, _, _ = lstsq(X, cops)
    return ChillerSurrogate(coeffs=coeffs.tolist())

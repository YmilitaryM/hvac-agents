import numpy as np
from sklearn.ensemble import IsolationForest as SklearnIF


class IsolationForestDetector:
    def __init__(self, contamination: float = 0.05):
        self._model = SklearnIF(contamination=contamination, random_state=42)
        self._fitted = False

    def fit(self, data: np.ndarray) -> None:
        self._model.fit(data)
        self._fitted = True

    def predict(self, x: np.ndarray) -> dict:
        if not self._fitted:
            return {"anomaly": False, "score": 0.0}
        score = float(self._model.decision_function(x.reshape(1, -1))[0])
        pred = self._model.predict(x.reshape(1, -1))[0]
        return {
            "anomaly": pred == -1,
            "score": score,
            "threshold": 0.0,
        }

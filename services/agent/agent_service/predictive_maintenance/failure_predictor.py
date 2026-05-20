import logging
from pathlib import Path

import numpy as np
from sklearn.ensemble import RandomForestClassifier

logger = logging.getLogger(__name__)


def build_training_data() -> tuple[list[list[float]], list[int]]:
    """Generate synthetic training data for initial model.
    In production, this is replaced by real labeled data from work order feedback loop.
    """
    np.random.seed(42)
    n_samples = 200

    features = []
    labels = []

    for _ in range(n_samples):
        cop = np.random.normal(5.5, 1.2)
        vibration = np.random.normal(3.0, 2.5)
        approach_temp = np.random.normal(3.0, 2.0)

        # Label: failure if cop < 3.0 or vibration > 7.0 or approach_temp > 5.0
        is_failure = int(cop < 3.0 or vibration > 7.0 or approach_temp > 5.0)
        features.append([cop, vibration, approach_temp])
        labels.append(is_failure)

    return features, labels


class FailurePredictor:
    def __init__(self):
        self.model = None
        self.feature_names = ["cop", "vibration_rms", "approach_temp"]

    def train(self, X: list[list[float]], y: list[int]):
        self.model = RandomForestClassifier(n_estimators=50, max_depth=5, random_state=42)
        self.model.fit(X, y)
        logger.info(f"Trained FailurePredictor on {len(X)} samples, "
                     f"classes: {dict(zip(*np.unique(y, return_counts=True)))}")

    def predict_proba(self, features: list[float]) -> float:
        if self.model is None:
            return 0.0
        return float(self.model.predict_proba([features])[0][1])

    def predict(self, features: list[float]) -> int:
        if self.model is None:
            return 0
        return int(self.model.predict([features])[0])


def export_onnx(model, path: str, n_features: int = 3):
    """Export a trained sklearn model to ONNX format."""
    try:
        from skl2onnx import to_onnx
        from skl2onnx.common.data_types import FloatTensorType

        initial_type = [("float_input", FloatTensorType([None, n_features]))]
        onx = to_onnx(model, initial_types=initial_type, target_opset=12)

        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, "wb") as f:
            f.write(onx.SerializeToString())
        logger.info(f"Exported ONNX model to {path}")
    except ImportError:
        logger.warning("skl2onnx not installed, skipping ONNX export")

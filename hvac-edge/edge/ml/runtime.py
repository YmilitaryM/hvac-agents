import logging
from pathlib import Path

import numpy as np

logger = logging.getLogger(__name__)


class ONNXInferenceRuntime:
    """Loads an ONNX model and provides predict() for edge inference."""

    def __init__(self, model_path: str):
        self.model_path = model_path
        self._session = None
        self._input_name = None
        self._load_model()

    def _load_model(self):
        if not Path(self.model_path).exists():
            logger.warning(f"ONNX model not found at {self.model_path}")
            return

        try:
            import onnxruntime as ort
            self._session = ort.InferenceSession(self.model_path)
            self._input_name = self._session.get_inputs()[0].name
            logger.info(f"Loaded ONNX model from {self.model_path}")
        except Exception as e:
            logger.error(f"Failed to load ONNX model: {e}")
            self._session = None

    @property
    def is_loaded(self) -> bool:
        return self._session is not None

    def predict(self, features: list[float]) -> float:
        """Run inference, returns probability score [0, 1]."""
        if not self._session:
            return 0.0

        try:
            arr = np.array([features], dtype=np.float32)
            result = self._session.run(None, {self._input_name: arr})
            return float(result[0][0][1]) if result[0].shape[1] > 1 else float(result[0][0][0])
        except Exception as e:
            logger.error(f"Inference failed: {e}")
            return 0.0

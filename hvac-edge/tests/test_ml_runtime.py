# hvac-edge/tests/test_ml_runtime.py
import pytest
import numpy as np
from edge.ml.runtime import ONNXInferenceRuntime

# Skip if onnxruntime not installed
pytestmark = pytest.mark.skipif(
    __import__("importlib.util").util.find_spec("onnxruntime") is None,
    reason="onnxruntime not installed"
)


@pytest.fixture
def mock_model(tmp_path):
    """Create a simple sklearn model, export to ONNX, return path."""
    from sklearn.ensemble import RandomForestClassifier
    import numpy as np

    X = np.random.randn(100, 3)
    y = (X[:, 0] + X[:, 1] - X[:, 2] > 0).astype(int)
    model = RandomForestClassifier(n_estimators=10, max_depth=3, random_state=42)
    model.fit(X, y)

    try:
        from skl2onnx import to_onnx
        from skl2onnx.common.data_types import FloatTensorType

        onx = to_onnx(model, initial_types=[("float_input", FloatTensorType([None, 3]))],
                      target_opset=12)
        path = tmp_path / "test_model.onnx"
        with open(path, "wb") as f:
            f.write(onx.SerializeToString())
        return str(path)
    except ImportError:
        pytest.skip("skl2onnx not installed")


def test_runtime_load_and_infer(mock_model):
    rt = ONNXInferenceRuntime(mock_model)
    assert rt.is_loaded

    score = rt.predict([5.0, 3.0, 1.0])
    assert 0 <= score <= 1


def test_runtime_unloaded_model():
    rt = ONNXInferenceRuntime("/nonexistent/model.onnx")
    assert not rt.is_loaded
    assert rt.predict([1.0, 2.0, 3.0]) == 0.0

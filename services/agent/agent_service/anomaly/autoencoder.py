import numpy as np

try:
    import torch
    import torch.nn as nn

    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False


class EquipmentAutoencoder(nn.Module if HAS_TORCH else object):
    """Autoencoder for equipment sensor anomaly detection."""

    def __init__(self, input_dim: int, hidden_dim: int = 8):
        if not HAS_TORCH:
            raise RuntimeError("torch is required for EquipmentAutoencoder")
        super().__init__()
        self.encoder = nn.Sequential(
            nn.Linear(input_dim, hidden_dim * 2),
            nn.ReLU(),
            nn.Linear(hidden_dim * 2, hidden_dim),
            nn.ReLU(),
        )
        self.decoder = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim * 2),
            nn.ReLU(),
            nn.Linear(hidden_dim * 2, input_dim),
        )

    def forward(self, x):
        encoded = self.encoder(x)
        decoded = self.decoder(encoded)
        return decoded

    def reconstruction_error(self, x: np.ndarray) -> float:
        with torch.no_grad():
            tensor = torch.tensor(x, dtype=torch.float32).unsqueeze(0)
            recon = self.forward(tensor)
            error = torch.mean((tensor - recon) ** 2).item()
        return error

    def is_anomaly(self, x: np.ndarray, threshold: float) -> bool:
        return self.reconstruction_error(x) > threshold


class AutoencoderAnomalyDetector:
    def __init__(self, input_dim: int, learning_rate: float = 0.001):
        self.input_dim = input_dim
        self.model = EquipmentAutoencoder(input_dim) if HAS_TORCH else None
        self.threshold = 0.05
        self._optimizer = (
            torch.optim.Adam(self.model.parameters(), lr=learning_rate)
            if HAS_TORCH and self.model
            else None
        )

    def train(self, data: np.ndarray, epochs: int = 50) -> None:
        if not HAS_TORCH or self.model is None:
            return
        self.model.train()
        tensor = torch.tensor(data, dtype=torch.float32)
        for _ in range(epochs):
            self._optimizer.zero_grad()
            recon = self.model(tensor)
            loss = nn.functional.mse_loss(recon, tensor)
            loss.backward()
            self._optimizer.step()
        errors = [self.model.reconstruction_error(data[i].numpy()) for i in range(len(data))]
        self.threshold = np.percentile(errors, 95)

    def predict(self, x: np.ndarray) -> dict:
        if self.model is None:
            return {"anomaly": False, "error": 0.0, "threshold": self.threshold, "contributing_features": []}
        error = self.model.reconstruction_error(x)
        return {
            "anomaly": error > self.threshold,
            "error": float(error),
            "threshold": float(self.threshold),
            "contributing_features": [],
        }

import numpy as np


class ColdStartTrainer:
    """Generate synthetic training data from Simulation Engine for ML model warm-up."""

    @staticmethod
    async def generate_from_simulation(sim_client, equipment_id: str, hours: int = 168) -> np.ndarray:
        synthetic_data = []
        for plr in np.linspace(0.3, 1.0, 20):
            for twb in np.linspace(20, 30, 10):
                result = await sim_client.post("/api/simulation/run", json={
                    "equipment_id": equipment_id,
                    "conditions": {"plr": float(plr), "wet_bulb": float(twb)},
                })
                if result.status_code == 200:
                    synthetic_data.append(result.json()["sensors"])
        return np.array(synthetic_data) if synthetic_data else np.zeros((0, 10))

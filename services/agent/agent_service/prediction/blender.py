"""Dynamic blending of physics and ML predictions."""

class PredictionBlender:
    """Blend physics and ML predictions with dynamic alpha.

    alpha = max(0.3, 1.0 - ml_confidence)
    - alpha=1.0: pure physics (cold start)
    - alpha=0.3: heavily ML (high confidence)
    """

    MIN_ALPHA = 0.3  # never go below 30% physics

    def blend(self, physics_load_rt: float, ml_load_rt: float, ml_confidence: float) -> dict:
        """Blend predictions and return final value."""
        alpha = max(self.MIN_ALPHA, 1.0 - ml_confidence)
        blended = alpha * physics_load_rt + (1.0 - alpha) * ml_load_rt

        return {
            "blended_load_rt": round(blended, 2),
            "alpha": round(alpha, 3),
            "physics_weight": round(alpha * 100, 1),
            "ml_weight": round((1 - alpha) * 100, 1),
            "method": "physics_only" if alpha > 0.95 else ("ml_dominant" if alpha < 0.5 else "hybrid")
        }

    def generate_forecast(self, current_load: float, hour: int, building_type: str = "office") -> dict:
        """Generate forecast for 15min, 1h, 6h, 24h based on typical daily profile.

        Uses a simple heuristic multiplier based on time of day and building type.
        """
        # Typical office load profile multipliers (relative to baseline)
        profiles = {
            "office": {0: 0.2, 1: 0.15, 2: 0.1, 3: 0.1, 4: 0.1, 5: 0.15, 6: 0.3,
                       7: 0.6, 8: 0.85, 9: 0.95, 10: 1.0, 11: 1.0, 12: 0.95,
                       13: 0.95, 14: 1.0, 15: 1.0, 16: 0.95, 17: 0.85, 18: 0.7,
                       19: 0.5, 20: 0.35, 21: 0.25, 22: 0.2, 23: 0.15},
            "hospital": {h: max(0.6, min(1.0, 0.7 + 0.3 * (1 if 8 <= h <= 20 else 0))) for h in range(24)},
            "data_center": {h: 0.95 for h in range(24)},  # flat profile
        }

        profile = profiles.get(building_type, profiles["office"])

        def _load_at(future_hour: float) -> float:
            h = int(future_hour) % 24
            return current_load * profile.get(h, 1.0)

        return {
            "forecast_15min_rt": round(_load_at(hour + 0.25), 2),
            "forecast_1h_rt": round(_load_at(hour + 1), 2),
            "forecast_6h_rt": round(_load_at(hour + 6), 2),
            "forecast_24h_rt": round(_load_at(hour + 24), 2),
        }

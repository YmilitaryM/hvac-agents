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

    def generate_forecast(self, current_load: float, hour: int, building_type: str = "office",
                          day_of_week: int = 0, is_holiday: bool = False) -> dict:
        """Generate forecast for 15min, 1h, 6h, 24h based on typical daily profile.

        Uses a simple heuristic multiplier based on time of day, building type,
        day of week, and holiday status.
        """
        # Typical office load profile multipliers (relative to baseline)
        weekday_profile = {
            0: 0.2, 1: 0.15, 2: 0.1, 3: 0.1, 4: 0.1, 5: 0.15, 6: 0.3,
            7: 0.6, 8: 0.85, 9: 0.95, 10: 1.0, 11: 1.0, 12: 0.95,
            13: 0.95, 14: 1.0, 15: 1.0, 16: 0.95, 17: 0.85, 18: 0.7,
            19: 0.5, 20: 0.35, 21: 0.25, 22: 0.2, 23: 0.15,
        }
        # Weekend/holiday: reduced occupancy
        weekend_profile = {h: max(0.05, v * 0.4) for h, v in weekday_profile.items()}

        base_profiles = {
            "office": weekday_profile,
            "hospital": {h: max(0.6, min(1.0, 0.7 + 0.3 * (1 if 8 <= h <= 20 else 0))) for h in range(24)},
            "data_center": {h: 0.95 for h in range(24)},
        }

        base = base_profiles.get(building_type, weekday_profile)
        is_weekend = day_of_week in (5, 6)  # Saturday=5, Sunday=6

        def _load_at(future_hour: float) -> float:
            h = int(future_hour) % 24
            future_day_offset = int(future_hour // 24)
            future_dow = (day_of_week + future_day_offset) % 7
            future_weekend = future_dow in (5, 6)
            if building_type == "office":
                if future_weekend:
                    return current_load * weekend_profile.get(h, 0.2)
                elif is_holiday and future_day_offset == 0:
                    return current_load * weekend_profile.get(h, 0.2)
            return current_load * base.get(h, 1.0)

        return {
            "forecast_15min_rt": round(_load_at(hour + 0.25), 2),
            "forecast_1h_rt": round(_load_at(hour + 1), 2),
            "forecast_6h_rt": round(_load_at(hour + 6), 2),
            "forecast_24h_rt": round(_load_at(hour + 24), 2),
        }

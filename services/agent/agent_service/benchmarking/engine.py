"""Multi-plant energy efficiency benchmarking engine."""
import statistics


class PlantBenchmarker:
    """Compare energy efficiency across multiple plants."""

    def compare(self, plant_data: list[dict]) -> dict:
        """Compare plants and return COP/intensity/carbon rankings."""
        if not plant_data:
            return {"rankings": [], "best_plant": None, "summary": "No data"}

        rankings = []
        for plant in plant_data:
            cop_vals = plant.get("cop_values", [])
            intensity_vals = plant.get("energy_intensity_values", [])
            carbon_vals = plant.get("carbon_values", [])

            avg_cop = sum(cop_vals) / len(cop_vals) if cop_vals else 0
            avg_intensity = sum(intensity_vals) / len(intensity_vals) if intensity_vals else 0
            avg_carbon = sum(carbon_vals) / len(carbon_vals) if carbon_vals else 0

            rankings.append({
                "plant_id": plant["plant_id"],
                "name": plant.get("name", ""),
                "location": plant.get("site_location", ""),
                "avg_cop": round(avg_cop, 2),
                "avg_energy_intensity_kw_per_rt": round(avg_intensity, 3),
                "avg_carbon_kgco2_per_rt": round(avg_carbon, 3),
                "data_points": len(cop_vals),
            })

        rankings.sort(key=lambda x: x["avg_cop"], reverse=True)
        for i, r in enumerate(rankings):
            r["rank"] = i + 1

        best = rankings[0]
        cops = [r["avg_cop"] for r in rankings if r["avg_cop"] > 0]
        avg_all = sum(cops) / len(cops) if cops else 0

        return {
            "rankings": rankings,
            "best_plant": best,
            "group_avg_cop": round(avg_all, 2),
            "total_plants": len(rankings),
            "summary": f"Best: {best['name']} (COP {best['avg_cop']}), Group avg COP: {avg_all:.2f}",
        }

    def get_trend(self, cop_history: list[dict]) -> dict:
        """Analyze COP trend over time for a single plant."""
        if len(cop_history) < 2:
            return {"trend": "insufficient_data", "slope": 0, "data_points": len(cop_history)}

        timestamps = [p["timestamp"] for p in cop_history]
        cops = [p["cop"] for p in cop_history]

        n = len(timestamps)
        t_mean = statistics.mean(timestamps)
        c_mean = statistics.mean(cops)

        numerator = sum((timestamps[i] - t_mean) * (cops[i] - c_mean) for i in range(n))
        denominator = sum((t - t_mean) ** 2 for t in timestamps)

        slope = numerator / denominator if denominator != 0 else 0

        if slope > 0.01:
            trend = "improving"
        elif slope < -0.01:
            trend = "declining"
        else:
            trend = "stable"

        return {
            "trend": trend,
            "slope_per_hour": round(slope * 3600, 6),
            "avg_cop": round(c_mean, 2),
            "data_points": n,
        }

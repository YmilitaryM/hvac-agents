class CarbonOptimizer:
    @staticmethod
    def optimal_carbon_allocation(
        stations: list[dict], total_carbon_budget: float
    ) -> dict[str, float]:
        """Allocate carbon budget across stations for minimum total cost."""
        total_capacity = sum(s.get("capacity_rt", 0) for s in stations)
        if total_capacity == 0:
            return {s["id"]: total_carbon_budget / len(stations) for s in stations}
        return {
            s["id"]: total_carbon_budget * s.get("capacity_rt", 0) / total_capacity
            for s in stations
        }

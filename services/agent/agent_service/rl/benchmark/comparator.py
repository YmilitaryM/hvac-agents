from collections.abc import Sequence
from dataclasses import dataclass


@dataclass
class BenchmarkResult:
    method: str  # mappo | milp_only | pid | manual
    total_cost: float
    avg_cop: float
    carbon_tonnes: float
    comfort_violations: int
    load_match_pct: float


class Comparator:
    """Compare DRL against baselines."""

    def compare(
        self,
        mappo_result: BenchmarkResult,
        baselines: Sequence[BenchmarkResult],
    ) -> dict:
        report = {
            "mappo": {
                "cost": mappo_result.total_cost,
                "cop": mappo_result.avg_cop,
                "carbon": mappo_result.carbon_tonnes,
                "comfort_violations": mappo_result.comfort_violations,
                "load_match_pct": mappo_result.load_match_pct,
            },
            "baselines": [],
        }

        best_cost = mappo_result.total_cost
        for bl in baselines:
            report["baselines"].append({
                "method": bl.method,
                "cost": bl.total_cost,
                "cop": bl.avg_cop,
            })
            best_cost = min(best_cost, bl.total_cost)

        savings_pct = (
            ((best_cost - mappo_result.total_cost) / best_cost * 100) if best_cost else 0
        )
        report["mappo_savings_pct"] = round(savings_pct, 2)
        return report

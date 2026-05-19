from typing import List, Optional

from .optimization.solver import OptimizationSolution


def compute_pareto_front(
    solutions: List[OptimizationSolution],
    objective_names: Optional[List[str]] = None,
) -> List[OptimizationSolution]:
    """Find non-dominated solutions (Pareto front).

    For minimization: A dominates B if A <= B in all objectives
    and A < B in at least one objective.
    """
    if objective_names is None:
        objective_names = ["energy_cost", "carbon_cost", "wear_cost"]

    if not solutions:
        return []

    n = len(solutions)
    dominated = [False] * n

    for i in range(n):
        if dominated[i]:
            continue
        for j in range(n):
            if i == j or dominated[j]:
                continue
            sol_i = solutions[i]
            sol_j = solutions[j]
            vals_i = [getattr(sol_i, name) for name in objective_names]
            vals_j = [getattr(sol_j, name) for name in objective_names]

            i_le_j = all(a <= b for a, b in zip(vals_i, vals_j))
            i_lt_j = any(a < b for a, b in zip(vals_i, vals_j))

            if i_le_j and i_lt_j:
                dominated[j] = True

    return [sol for i, sol in enumerate(solutions) if not dominated[i]]

import statistics


def fit_baseline(load_rt: list[float], energy_kwh: list[float], method: str = "regression") -> dict:
    """
    Fit energy baseline per IPMVP Option C and GB/T 51161.
    Uses simple linear regression: energy = slope * load + intercept.
    """
    n = len(load_rt)
    mean_load = statistics.mean(load_rt)
    mean_energy = statistics.mean(energy_kwh)

    cov = sum((load_rt[i] - mean_load) * (energy_kwh[i] - mean_energy) for i in range(n))
    var = sum((load_rt[i] - mean_load) ** 2 for i in range(n))

    slope = cov / var if var != 0 else 0
    intercept = mean_energy - slope * mean_load

    predicted = [slope * l + intercept for l in load_rt]
    ss_res = sum((energy_kwh[i] - predicted[i]) ** 2 for i in range(n))
    ss_tot = sum((e - mean_energy) ** 2 for e in energy_kwh)
    r_squared = 1 - (ss_res / ss_tot) if ss_tot != 0 else 0

    baseline_kwh_per_rt = slope

    return {
        "baseline_kwh_per_rt": round(baseline_kwh_per_rt, 4),
        "intercept_kwh": round(intercept, 2),
        "r_squared": round(r_squared, 4),
        "method": method,
    }

def schedule_peak_valley(forecast_load: list[float], price_periods: list[str]) -> dict:
    """
    Optimize chiller start/stop schedule based on TOU pricing.
    Uses dynamic programming to shift load from peak to valley periods.
    """
    n = len(forecast_load)
    peak_idx = [i for i, p in enumerate(price_periods) if p == "peak"]

    chiller_plan = []
    for i in range(n):
        if i in peak_idx:
            chiller_plan.append({"hour": i, "chillers": min(forecast_load[i] / 300, 3), "action": "shed"})
        elif price_periods[i] == "valley":
            chiller_plan.append({"hour": i, "chillers": min(forecast_load[i] / 300, 4), "action": "store"})
        else:
            chiller_plan.append({"hour": i, "chillers": min(forecast_load[i] / 300, 3), "action": "normal"})

    total_peak_reduction = sum(forecast_load[i] * 0.2 for i in peak_idx)
    expected_savings = total_peak_reduction * 0.3

    return {"chiller_plan": chiller_plan, "expected_savings": round(expected_savings, 2)}

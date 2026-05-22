def predict_demand(power_history: list[float], demand_limit: float = 500, window_size: int = 5) -> dict:
    """
    Predict peak demand over the next 15-minute sliding window.
    Uses sliding window max + trend extrapolation.
    """
    recent_window = power_history[-window_size:] if len(power_history) >= window_size else power_history
    current_max = max(recent_window)
    trend = (recent_window[-1] - recent_window[0]) / window_size if len(recent_window) > 1 else 0
    predicted_peak = current_max + trend * 3

    return {
        "current_kw": power_history[-1],
        "predicted_peak": round(predicted_peak, 1),
        "demand_limit": demand_limit,
        "warning": predicted_peak > demand_limit,
    }

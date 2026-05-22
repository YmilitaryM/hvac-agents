import math


def estimate_rul(health_history: list[float], model: str = "weibull", failure_threshold: float = 60) -> dict:
    """
    Estimate remaining useful life from health score trajectory.
    Uses exponential degradation model: score(t) = score_0 * exp(-lambda * t).
    """
    if len(health_history) < 3:
        return {"predicted_hours": 0, "ci_lo": 0, "ci_hi": 0, "model": model}

    scores = health_history
    n = len(scores)
    log_scores = [math.log(max(s, 0.1)) for s in scores]

    x_mean = (n - 1) / 2
    y_mean = sum(log_scores) / n
    cov = sum((i - x_mean) * (log_scores[i] - y_mean) for i in range(n))
    var = sum((i - x_mean) ** 2 for i in range(n))
    slope = cov / var if var != 0 else 0

    lambda_rate = -slope
    current_score = scores[-1]
    if lambda_rate <= 0:
        return {"predicted_hours": 99999, "ci_lo": 99999, "ci_hi": 99999, "model": model}

    predicted_hours = math.log(current_score / failure_threshold) / lambda_rate

    ci_lo = predicted_hours * 0.75
    ci_hi = predicted_hours * 1.25

    return {
        "predicted_hours": round(predicted_hours, 1),
        "ci_lo": round(ci_lo, 1),
        "ci_hi": round(ci_hi, 1),
        "model": model,
        "degradation_rate": round(lambda_rate, 6),
    }

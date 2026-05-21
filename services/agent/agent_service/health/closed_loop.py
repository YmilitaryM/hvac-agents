def validate_predictions(predictions: list[dict], retrain_threshold: float = 0.75) -> dict:
    """
    Compare RUL/diagnosis predictions against actual outcomes from work orders.
    Returns accuracy and whether retraining is needed.
    """
    if not predictions:
        return {"accuracy": 0, "should_retrain": False, "sample_count": 0}

    errors = []
    for p in predictions:
        predicted = p.get("predicted_hours", 0)
        actual = p.get("actual_hours", 0)
        if actual > 0:
            error = abs(predicted - actual) / actual
            errors.append(error)

    if not errors:
        return {"accuracy": 0, "should_retrain": False, "sample_count": 0}

    mape = sum(errors) / len(errors)
    accuracy = 1 - mape

    return {
        "accuracy": round(max(0, accuracy), 3),
        "should_retrain": accuracy < retrain_threshold,
        "sample_count": len(errors),
    }

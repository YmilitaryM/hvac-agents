def estimate_delivery_loss(
    distance_km: float,
    flow_temp: float = 7.0,
    ambient_temp: float = 30.0,
) -> float:
    """Estimate cooling loss per km of distribution piping."""
    delta_t = ambient_temp - flow_temp
    loss_per_km = 0.02 + 0.001 * delta_t  # ~2-5% per km
    return loss_per_km * distance_km


def effective_capacity(
    station_capacity: float,
    distance_km: float,
    flow_temp: float = 7.0,
    ambient_temp: float = 30.0,
) -> float:
    """Capacity after delivery losses."""
    loss = estimate_delivery_loss(distance_km, flow_temp, ambient_temp)
    return station_capacity * (1.0 - loss)

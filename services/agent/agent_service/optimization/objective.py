from typing import Dict


def compute_energy_cost(
    total_power_kw: float,
    price_per_kwh: float,
    duration_hours: float = 1.0,
) -> float:
    """Compute energy cost in yuan.

    Args:
        total_power_kw: Total system power in kW
        price_per_kwh: Electricity price per kWh
        duration_hours: Time duration in hours
    """
    if total_power_kw <= 0:
        return 0.0
    return total_power_kw * price_per_kwh * duration_hours


def compute_carbon_cost(
    total_power_kw: float,
    grid_carbon_intensity: float,  # kgCO2/kWh
    carbon_price: float,  # yuan/kgCO2
    duration_hours: float = 1.0,
) -> float:
    """Compute carbon emission cost in yuan.

    Args:
        total_power_kw: Total system power in kW
        grid_carbon_intensity: Grid emission factor (kgCO2 per kWh)
        carbon_price: Carbon price (yuan per kgCO2)
        duration_hours: Time duration in hours
    """
    if total_power_kw <= 0 or grid_carbon_intensity <= 0:
        return 0.0
    emissions_kg = total_power_kw * grid_carbon_intensity * duration_hours
    return emissions_kg * carbon_price


def compute_wear_cost(
    start_actions: Dict[str, int],
    wear_costs: Dict[str, float],
) -> float:
    """Compute equipment wear cost from start/stop actions.

    Args:
        start_actions: Dict mapping device name prefix to count of starts.
            e.g., {"chiller": 2, "pump": 3}
        wear_costs: Dict mapping device type to cost per start.
            e.g., {"chiller": 150.0, "pump": 30.0, "cooling_tower": 20.0}
    """
    total = 0.0
    for device_prefix, count in start_actions.items():
        if count <= 0:
            continue
        for cost_key, cost_per_start in wear_costs.items():
            if device_prefix.startswith(cost_key):
                total += count * cost_per_start
                break
    return total


def compute_water_cost(
    total_power_kw: float,
    water_price_per_m3: float = 3.5,
    water_usage_rate: float = 0.008,  # m3 per kW of heat rejected
    duration_hours: float = 1.0,
) -> float:
    """Compute cooling tower water consumption cost in yuan.

    Args:
        total_power_kw: Total system power in kW
        water_price_per_m3: Water price in yuan per m3
        water_usage_rate: Water consumption rate (m3 per kW rejected)
        duration_hours: Time duration in hours
    """
    if total_power_kw <= 0:
        return 0.0
    heat_rejected_kw = total_power_kw * 1.15  # ~15% more heat than power
    water_m3 = heat_rejected_kw * water_usage_rate * duration_hours
    return water_m3 * water_price_per_m3


def total_objective(
    energy_cost: float,
    carbon_cost: float,
    wear_cost: float,
    w_energy: float = 1.0,
    w_carbon: float = 1.0,
    w_wear: float = 1.0,
    water_cost: float = 0.0,
    w_water: float = 1.0,
) -> float:
    """Compute weighted total objective.

    total = w_energy * energy_cost + w_carbon * carbon_cost
          + w_wear * wear_cost + w_water * water_cost
    """
    return (
        w_energy * energy_cost
        + w_carbon * carbon_cost
        + w_wear * wear_cost
        + w_water * water_cost
    )

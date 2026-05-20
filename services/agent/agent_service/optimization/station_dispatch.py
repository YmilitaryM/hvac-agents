from dataclasses import dataclass


@dataclass
class StationStatus:
    station_id: str
    available_capacity: float  # RT
    marginal_cost: float  # 元/RT-h
    current_load: float
    cop: float
    carbon_intensity: float  # tCO2/RT


@dataclass
class DispatchResult:
    stations: dict[str, float]  # station_id -> target_load
    marginal_cost: dict[str, float]
    unused_capacity: float


def inter_station_dispatch(
    stations: list[StationStatus],
    total_load: float,
    carbon_budget: float | None = None,
) -> DispatchResult:
    """Allocate total cooling load across multiple stations by marginal cost."""
    sorted_stations = sorted(stations, key=lambda s: s.marginal_cost)

    remaining = total_load
    targets: dict[str, float] = {}
    mc: dict[str, float] = {}

    for station in sorted_stations:
        if remaining <= 0:
            targets[station.station_id] = 0.0
            mc[station.station_id] = station.marginal_cost
            continue

        alloc = min(remaining, station.available_capacity)
        targets[station.station_id] = alloc
        mc[station.station_id] = station.marginal_cost
        remaining -= alloc

    return DispatchResult(
        stations=targets,
        marginal_cost=mc,
        unused_capacity=sum(s.available_capacity for s in stations) - total_load,
    )

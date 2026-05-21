"""Emission factor registry with China regional grid factors."""
from typing import Optional

# China regional grid emission factors (tCO2/MWh)
CEA_REGIONAL_FACTORS = {
    "north": 0.525,
    "northeast": 0.554,
    "east": 0.498,
    "central": 0.420,
    "south": 0.389,
    "southwest": 0.351,
    "northwest": 0.493,
}

DEFAULT_FACTOR = 0.50


class FactorRegistry:
    """Manages emission factors with time-of-use and seasonal variants."""

    def __init__(self):
        self._overrides: dict[str, float] = {}

    def get_factor(self, region: str, hour: int = 0, month: int = 1) -> float:
        if region in self._overrides:
            return self._overrides[region]
        base = CEA_REGIONAL_FACTORS.get(region, DEFAULT_FACTOR)
        # Seasonal adjustment: summer (6-8) +5%, winter (12-2) -3%
        if month in (6, 7, 8):
            base *= 1.05
        elif month in (12, 1, 2):
            base *= 0.97
        return round(base, 4)

    def set_override(self, region: str, factor: float) -> None:
        self._overrides[region] = factor

    def clear_override(self, region: str) -> None:
        self._overrides.pop(region, None)

    def list_regions(self) -> dict:
        return dict(CEA_REGIONAL_FACTORS)

    def get_cooling_benchmark(self) -> float:
        """District cooling industry benchmark (tCO2/GJ)."""
        return 0.065

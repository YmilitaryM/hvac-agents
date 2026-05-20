from abc import ABC, abstractmethod
from datetime import datetime


class CarbonMarket(ABC):
    region: str
    carbon_price: float  # 元/tCO2
    emission_factor: float  # tCO2/MWh
    allowance_period: tuple[datetime, datetime]

    @abstractmethod
    def emission_cost(self, power_kw: float, duration_hours: float) -> float: ...

    @abstractmethod
    def allowance_remaining(self) -> float: ...

    @abstractmethod
    def purchase_deficit(self, amount_tco2: float) -> float: ...


class GenericCarbonMarket(CarbonMarket):
    """Configurable carbon market for any region."""

    def __init__(
        self,
        region: str,
        carbon_price: float,
        emission_factor: float,
        total_allowance: float,
        period_start: datetime,
        period_end: datetime,
    ):
        self.region = region
        self.carbon_price = carbon_price
        self.emission_factor = emission_factor
        self._total = total_allowance
        self._used = 0.0
        self.allowance_period = (period_start, period_end)

    def emission_cost(self, power_kw: float, duration_hours: float) -> float:
        energy_mwh = power_kw * duration_hours / 1000.0
        emissions = energy_mwh * self.emission_factor
        self._used += emissions
        overage = max(0, self._used - self._total)
        return emissions * self.carbon_price + overage * self.carbon_price * 2.0

    def allowance_remaining(self) -> float:
        return max(0, self._total - self._used)

    def purchase_deficit(self, amount_tco2: float) -> float:
        return amount_tco2 * self.carbon_price * 1.1

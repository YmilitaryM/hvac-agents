from .carbon_market import GenericCarbonMarket
from .emission.factor_registry import CEA_REGIONAL_FACTORS, DEFAULT_FACTOR


class CEAAdapter(GenericCarbonMarket):
    """China Emission Allowance (CEA) carbon market adapter."""

    def __init__(
        self,
        region: str,
        carbon_price: float,
        total_allowance_tco2: float,
        period_start,
        period_end,
    ):
        emission_factor = CEA_REGIONAL_FACTORS.get(region, DEFAULT_FACTOR)
        super().__init__(
            region=region,
            carbon_price=carbon_price,
            emission_factor=emission_factor,
            total_allowance=total_allowance_tco2,
            period_start=period_start,
            period_end=period_end,
        )

    @staticmethod
    def cooling_allowance(cooling_gj: float) -> float:
        from .emission.factor_registry import FactorRegistry
        return cooling_gj * FactorRegistry().get_cooling_benchmark()

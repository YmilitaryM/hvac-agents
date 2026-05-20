from .carbon_market import GenericCarbonMarket

# China regional grid emission factors (tCO2/MWh)
CEA_REGIONAL_FACTORS = {
    "north": 0.525,
    "northeast": 0.554,
    "east": 0.498,
    "central": 0.420,
    "south": 0.389,
    "northwest": 0.493,
}

# District cooling industry benchmark (tCO2/GJ of cooling)
CEA_COOLING_BENCHMARK = 0.065


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
        emission_factor = CEA_REGIONAL_FACTORS.get(region, 0.50)
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
        """Calculate allowance for a given amount of cooling energy (GJ)."""
        return cooling_gj * CEA_COOLING_BENCHMARK

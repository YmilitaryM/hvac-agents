class EmissionCalculator:
    @staticmethod
    def from_power(power_kw: float, duration_h: float, emission_factor: float) -> float:
        energy_mwh = power_kw * duration_h / 1000.0
        return energy_mwh * emission_factor

    @staticmethod
    def from_cooling(cooling_gj: float, benchmark: float = 0.065) -> float:
        return cooling_gj * benchmark

    @staticmethod
    def from_fuel(fuel_kg: float, emission_factor: float) -> float:
        return fuel_kg * emission_factor

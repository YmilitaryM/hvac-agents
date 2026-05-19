import math

G = 9.81  # m/s^2


class PipeSegment:
    """Pipe with Darcy-Weisbach friction + minor losses + temperature drop."""

    def __init__(self, name: str, diameter_mm: float = 200, length_m: float = 5.0,
                 roughness_mm: float = 0.045, fluid_density: float = 1000,
                 fluid_viscosity: float = 1.0e-6, insulation_u: float = 0.5):
        self.name = name
        self.diameter_m = diameter_mm / 1000.0
        self.length_m = length_m
        self.roughness_m = roughness_mm / 1000.0
        self.rho = fluid_density
        self.nu = fluid_viscosity
        self.insulation_u = insulation_u
        self.area_m2 = math.pi * (self.diameter_m / 2) ** 2

    def friction_factor(self, velocity_ms: float) -> float:
        """Colebrook equation (Swamee-Jain approximation)."""
        if velocity_ms <= 0:
            return 0.0
        re = velocity_ms * self.diameter_m / self.nu
        if re < 2300:
            return 64.0 / max(re, 1.0)
        rr = self.roughness_m / self.diameter_m
        return 0.25 / (math.log10(rr / 3.7 + 5.74 / re ** 0.9)) ** 2

    def compute_pressure_drop_pa(self, flow_lps: float, k_minor: float = 0.0) -> float:
        """Darcy-Weisbach + minor losses. Returns Pa."""
        flow_m3s = flow_lps / 1000.0
        velocity = flow_m3s / self.area_m2 if self.area_m2 > 0 else 0.0
        if velocity <= 0:
            return 0.0
        f = self.friction_factor(velocity)
        dp_major = f * (self.length_m / self.diameter_m) * (self.rho * velocity ** 2 / 2)
        dp_minor = k_minor * (self.rho * velocity ** 2 / 2)
        return dp_major + dp_minor

    def compute_temperature_drop(self, fluid_temp_c: float, ambient_temp_c: float,
                                  flow_lps: float, cp: float = 4180) -> float:
        """Temperature drop due to heat loss through insulation."""
        if flow_lps <= 0:
            return 0.0
        mass_flow = flow_lps / 1000.0 * self.rho
        if mass_flow <= 0:
            return 0.0
        perimeter = math.pi * self.diameter_m
        ua = self.insulation_u * perimeter * self.length_m
        delta_t = fluid_temp_c - ambient_temp_c
        factor = 1 - math.exp(-ua / (mass_flow * cp))
        return delta_t * factor

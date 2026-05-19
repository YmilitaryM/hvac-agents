"""Physics-based cooling load model (7 components). Output in RT (refrigeration tons)."""
import math

class CoolingLoadPhysicsModel:
    """Calculate total cooling load from building parameters and weather conditions.

    Q_total = Q_envelope + Q_solar + Q_infiltration + Q_people + Q_lighting + Q_equipment + Q_fresh_air
    All results in kW, then converted to RT (1 RT = 3.517 kW).
    """

    def predict(self, building: dict, outdoor: dict, indoor: dict, time_features: dict = None) -> dict:
        """Main prediction method.

        Args:
            building: {area_m2, floor_count, orientation, window_wall_ratio, wall_u_value, roof_u_value,
                       glass_shgc, building_type, latitude}
            outdoor: {db_temp, wb_temp, rh, solar_radiation, wind_speed, cloud_cover}
            indoor: {indoor_temp, indoor_rh, occupancy_count, lighting_power_kw, equipment_power_kw}
            time_features: {hour, day_of_week, is_holiday, month} (optional)

        Returns: {total_load_rt, components: {envelope, solar, infiltration, people, lighting, equipment, fresh_air}, unit: "RT"}
        """
        # Default values
        building = self._default_building(building)
        outdoor = self._default_outdoor(outdoor)
        indoor = self._default_indoor(indoor)

        q_envelope = self._calc_envelope(building, outdoor, indoor)
        q_solar = self._calc_solar(building, outdoor, time_features or {})
        q_infiltration = self._calc_infiltration(building, outdoor, indoor)
        q_people = self._calc_people(indoor, time_features or {})
        q_lighting = self._calc_lighting(building, indoor, time_features or {})
        q_equipment = self._calc_equipment(building, indoor, time_features or {})
        q_fresh_air = self._calc_fresh_air(indoor, outdoor, time_features or {})

        total_kw = q_envelope + q_solar + q_infiltration + q_people + q_lighting + q_equipment + q_fresh_air
        total_rt = total_kw / 3.517

        return {
            "total_load_rt": round(total_rt, 2),
            "total_load_kw": round(total_kw, 2),
            "components": {
                "envelope_kw": round(q_envelope, 2),
                "solar_kw": round(q_solar, 2),
                "infiltration_kw": round(q_infiltration, 2),
                "people_kw": round(q_people, 2),
                "lighting_kw": round(q_lighting, 2),
                "equipment_kw": round(q_equipment, 2),
                "fresh_air_kw": round(q_fresh_air, 2),
            },
            "unit": "RT"
        }

    def _calc_envelope(self, b, out, ind) -> float:
        """Q_envelope = SUM(U * A * delta_T) for walls + roof.
        U in W/m²K, A in m², delta_T in K. Returns kW."""
        area_wall = self._estimate_wall_area(b["area_m2"], b["floor_count"], b["window_wall_ratio"])
        area_roof = b["area_m2"] / b.get("floor_count", 1)
        dt = out["db_temp"] - ind.get("indoor_temp", 24.0)
        q_wall = b.get("wall_u_value", 1.5) * area_wall * dt
        q_roof = b.get("roof_u_value", 0.8) * area_roof * dt
        return max(0, (q_wall + q_roof) / 1000.0)  # W -> kW

    def _calc_solar(self, b, out, tf) -> float:
        """Q_solar = A_window * SHGC * I_solar * shading_factor. Returns kW."""
        window_area = self._estimate_wall_area(b["area_m2"], b.get("floor_count", 1), b.get("window_wall_ratio", 0.3)) * b.get("window_wall_ratio", 0.3)
        solar = out.get("solar_radiation", 500)  # W/m² default
        shgc = b.get("glass_shgc", 0.5)
        shading = 0.7  # default shading factor
        hour = tf.get("hour", 12)
        # No solar at night
        if hour < 6 or hour > 19:
            solar *= 0.1
        return (window_area * shgc * solar * shading) / 1000.0  # W -> kW

    def _calc_infiltration(self, b, out, ind) -> float:
        """Q_infiltration = rho * cp * ACH * V / 3600 * delta_T. Returns kW."""
        rho = 1.2  # kg/m³ air density
        cp = 1.005  # kJ/kg·K
        ach = 0.5  # air changes per hour
        floor_height = 3.0  # m
        volume = b["area_m2"] * floor_height
        dt = out["db_temp"] - ind.get("indoor_temp", 24.0)
        if dt < 0:
            dt = 0  # only cooling load
        return rho * cp * ach * volume / 3600.0 * dt  # already in kW

    def _calc_people(self, ind, tf) -> float:
        """Q_people = N * sensible_heat_per_person * occupancy_ratio. Returns kW."""
        sensible_heat = 0.075  # kW per person (sensible)
        n_people = ind.get("occupancy_count", 0)
        if n_people == 0:
            # Estimate from area
            n_people = 20  # default
        hour = tf.get("hour", 12)
        ratio = 1.0 if (8 <= hour <= 18) else 0.3  # occupancy schedule
        if tf.get("is_holiday"):
            ratio *= 0.3
        return n_people * sensible_heat * ratio

    def _calc_lighting(self, b, ind, tf) -> float:
        """Q_lighting = lighting_power_density * area * usage_ratio. Returns kW."""
        lpd = ind.get("lighting_power_kw", 0)
        if lpd == 0:
            lpd = 0.01 * b["area_m2"] / 1000.0  # 10 W/m² estimate
        hour = tf.get("hour", 12)
        ratio = 1.0 if (7 <= hour <= 19) else 0.2
        return lpd * ratio

    def _calc_equipment(self, b, ind, tf) -> float:
        """Q_equipment = equipment_power_density * area * usage_ratio. Returns kW."""
        epd = ind.get("equipment_power_kw", 0)
        if epd == 0:
            epd = 0.015 * b["area_m2"] / 1000.0  # 15 W/m² estimate
        hour = tf.get("hour", 12)
        ratio = 0.9 if (8 <= hour <= 18) else 0.4
        return epd * ratio

    def _calc_fresh_air(self, ind, out, tf) -> float:
        """Q_fresh_air = rho * cp * fresh_air_rate * N * delta_T / 3600. Returns kW."""
        rho = 1.2
        cp = 1.005
        fresh_air_rate = 30  # m³/h per person (typical office)
        n_people = ind.get("occupancy_count", 20)
        dt = out["db_temp"] - ind.get("indoor_temp", 24.0)
        if dt < 0:
            dt = 0
        return rho * cp * fresh_air_rate * n_people * dt / 3600.0

    def _estimate_wall_area(self, area_m2, floors, wwr) -> float:
        """Estimate total wall area from floor area."""
        # Assume square building: perimeter = 4 * sqrt(area)
        side = math.sqrt(area_m2 / max(floors, 1))
        perimeter = 4 * side
        wall_height = floors * 3.0  # 3m per floor
        return perimeter * wall_height

    def _default_building(self, b: dict) -> dict:
        defaults = {"area_m2": 5000, "floor_count": 3, "window_wall_ratio": 0.3,
                    "wall_u_value": 1.5, "roof_u_value": 0.8, "glass_shgc": 0.5, "building_type": "office"}
        return {**defaults, **b}

    def _default_outdoor(self, out: dict) -> dict:
        defaults = {"db_temp": 33.0, "wb_temp": 26.0, "rh": 60, "solar_radiation": 500, "wind_speed": 2.0, "cloud_cover": 30}
        return {**defaults, **out}

    def _default_indoor(self, ind: dict) -> dict:
        defaults = {"indoor_temp": 24.0, "indoor_rh": 50, "occupancy_count": 20,
                    "lighting_power_kw": 50, "equipment_power_kw": 75}
        return {**defaults, **ind}

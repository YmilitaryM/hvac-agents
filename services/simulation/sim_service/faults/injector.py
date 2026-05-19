"""Fault injector — manages active faults/disturbances and applies them to equipment models."""

import time
from .fault_models import (
    EquipmentFault, FaultType, ExternalDisturbance, DisturbanceType,
)


class FaultInjector:
    """Manages active faults and disturbances, and applies their effects to equipment model parameters.

    A singleton-per-process pattern is achieved by using a module-level instance in api/faults.py.
    """

    def __init__(self):
        self.active_faults: dict[str, EquipmentFault] = {}
        self.active_disturbances: dict[str, ExternalDisturbance] = {}

    # ------------------------------------------------------------------ #
    #  Fault lifecycle
    # ------------------------------------------------------------------ #

    def inject(self, fault: EquipmentFault) -> str:
        """Register a new equipment fault. Returns the fault_id."""
        self.active_faults[fault.fault_id] = fault
        return fault.fault_id

    def remove(self, fault_id: str) -> bool:
        """Remove an equipment fault by id. Returns True if it existed."""
        if fault_id in self.active_faults:
            del self.active_faults[fault_id]
            return True
        return False

    def list_active(self) -> list[EquipmentFault]:
        """Return all currently registered equipment faults."""
        return list(self.active_faults.values())

    # ------------------------------------------------------------------ #
    #  Disturbance lifecycle
    # ------------------------------------------------------------------ #

    def inject_disturbance(self, dist: ExternalDisturbance) -> str:
        """Register an external disturbance. Returns the dist_id."""
        self.active_disturbances[dist.dist_id] = dist
        return dist.dist_id

    def remove_disturbance(self, dist_id: str) -> bool:
        """Remove an external disturbance by id. Returns True if it existed."""
        if dist_id in self.active_disturbances:
            del self.active_disturbances[dist_id]
            return True
        return False

    def list_active_disturbances(self) -> list[ExternalDisturbance]:
        """Return all currently registered external disturbances."""
        return list(self.active_disturbances.values())

    # ------------------------------------------------------------------ #
    #  Activity check
    # ------------------------------------------------------------------ #

    def _is_fault_active(self, onset_time: float, duration: float | None, current_time: float) -> bool:
        """Check whether a fault/disturbance is currently active.

        Active if onset_time <= current_time AND (duration is None or not yet expired).
        """
        if current_time < onset_time:
            return False
        if duration is not None and (current_time - onset_time) > duration:
            return False
        return True

    def is_active(self, fault_id: str, current_time: float) -> bool:
        """Check if a specific fault is active at current_time."""
        fault = self.active_faults.get(fault_id)
        if fault is None:
            return False
        return self._is_fault_active(fault.onset_time, fault.duration, current_time)

    # ------------------------------------------------------------------ #
    #  Parameter modification – equipment faults
    # ------------------------------------------------------------------ #

    def modify_model_params(
        self, equipment_type: str, device_id: str, params: dict, current_time: float
    ) -> dict:
        """Apply active faults to model parameters for a specific device.

        Each fault type has a physical effect on the equipment:

        - FOULING:        design_cop reduced by 30 % * severity;
                          approach_temp increased by 2 * severity (deg C).
        - SURGE:          min_plr raised by 0.2 * severity (surge boundary moves up).
        - VALVE_STICKING: Cv reduced by 50 % * severity (stuck valve).
        - SENSOR_FAILURE: sensor marked as failed (return None values).
        - REFRIGERANT_LEAK: capacity_rt reduced progressively (1 % * severity per day).
        - DRIFT:          sensor drift_rate increased.
        - RUST:           roughness_mm increased by 0.5 * severity.
        - CAVITATION:     pump efficiency reduced by 40 % * severity.

        Returns a copy of *params* with modifications applied (or unchanged).
        """
        result = dict(params)

        for fault in self.active_faults.values():
            if fault.device_id != device_id:
                continue
            if not self._is_fault_active(fault.onset_time, fault.duration, current_time):
                continue

            sev = fault.severity

            # ---- FOULING (chiller) ----
            if fault.fault_type == FaultType.FOULING and equipment_type == "CentrifugalChiller":
                # Heat exchanger fouling reduces heat transfer
                if "design_cop" in result:
                    result["design_cop"] = result["design_cop"] * (1.0 - 0.3 * sev)
                if "approach_temp" in result:
                    result["approach_temp"] = result.get("approach_temp", 0.0) + 2.0 * sev

            # ---- SURGE (chiller) ----
            elif fault.fault_type == FaultType.SURGE and equipment_type == "CentrifugalChiller":
                # Surge boundary rises — compressor must stay at higher PLR
                if "min_plr" in result:
                    result["min_plr"] = min(1.0, result["min_plr"] + 0.2 * sev)

            # ---- VALVE STICKING (control valve) ----
            elif fault.fault_type == FaultType.VALVE_STICKING and equipment_type == "ControlValve":
                # Valve Cv is effectively reduced
                if "cv" in result:
                    result["cv"] = result["cv"] * (1.0 - 0.5 * sev)

            # ---- SENSOR FAILURE (sensor) ----
            elif fault.fault_type == FaultType.SENSOR_FAILURE and equipment_type == "Sensor":
                result["_failed"] = True

            # ---- REFRIGERANT LEAK (chiller) ----
            elif fault.fault_type == FaultType.REFRIGERANT_LEAK and equipment_type == "CentrifugalChiller":
                # Capacity degrades over time: 1 % * severity per day since injection
                days = (current_time - fault.injected_at) / 86400.0 if fault.injected_at else 0.0
                degrad_factor = max(0.0, 1.0 - 0.1 * sev * max(0, days))
                if "capacity_rt" in result:
                    result["capacity_rt"] = result["capacity_rt"] * degrad_factor

            # ---- DRIFT (sensor) ----
            elif fault.fault_type == FaultType.DRIFT and equipment_type == "Sensor":
                # Increase the effective drift rate
                if "drift_rate_per_year" in result:
                    result["drift_rate_per_year"] = result["drift_rate_per_year"] + 0.05 * sev

            # ---- RUST (pipe) ----
            elif fault.fault_type == FaultType.RUST and equipment_type == "PipeSegment":
                # Internal corrosion roughens the pipe wall
                if "roughness_mm" in result:
                    result["roughness_mm"] = result["roughness_mm"] + 0.5 * sev

            # ---- CAVITATION (pump) ----
            elif fault.fault_type == FaultType.CAVITATION and equipment_type == "Pump":
                # Pump efficiency drops; modeled as increased effective power draw
                if "rated_power_kw" in result:
                    result["rated_power_kw"] = result["rated_power_kw"] / (1.0 - 0.4 * sev)

        return result

    # ------------------------------------------------------------------ #
    #  Disturbance effects
    # ------------------------------------------------------------------ #

    def get_weather_modifier(self, outdoor_wb: float, outdoor_db: float, current_time: float) -> tuple[float, float]:
        """Apply active EXTREME_WEATHER disturbances to outdoor temperatures.

        Returns (modified_wb, modified_db).
        """
        mod_wb, mod_db = outdoor_wb, outdoor_db
        for dist in self.active_disturbances.values():
            if dist.disturbance_type != DisturbanceType.EXTREME_WEATHER:
                continue
            if not self._is_fault_active(dist.onset_time, dist.duration, current_time):
                continue
            # Magnitude adds up to 10 °C to wet-bulb and dry-bulb
            delta = dist.magnitude * 10.0
            mod_wb += delta
            mod_db += delta
        return mod_wb, mod_db

    def get_load_modifier(self, base_load_rt: float, current_time: float) -> float:
        """Apply active LOAD_SPIKE disturbances to a cooling load.

        Returns the modified load in RT.
        """
        factor = 1.0
        for dist in self.active_disturbances.values():
            if dist.disturbance_type != DisturbanceType.LOAD_SPIKE:
                continue
            if not self._is_fault_active(dist.onset_time, dist.duration, current_time):
                continue
            # Each spike adds magnitude * 50 % extra load
            factor += dist.magnitude * 0.5
        return base_load_rt * factor

    def is_comm_lost(self, current_time: float) -> bool:
        """Return True if any COMM_LOSS disturbance is active."""
        for dist in self.active_disturbances.values():
            if dist.disturbance_type != DisturbanceType.COMM_LOSS:
                continue
            if self._is_fault_active(dist.onset_time, dist.duration, current_time):
                return True
        return False

    def get_grid_voltage_factor(self, current_time: float) -> float:
        """Return voltage multiplier from active GRID_FLUCTUATION disturbances.

        1.0 = nominal; < 1.0 = sag; > 1.0 = swell (cap at +/- 20 %).
        """
        factor = 1.0
        for dist in self.active_disturbances.values():
            if dist.disturbance_type != DisturbanceType.GRID_FLUCTUATION:
                continue
            if not self._is_fault_active(dist.onset_time, dist.duration, current_time):
                continue
            # magnitude 0 … 1 maps to ± 20 %
            offset = (dist.magnitude - 0.5) * 0.4  # -0.2 … +0.2
            factor += offset
        return max(0.8, min(1.2, factor))

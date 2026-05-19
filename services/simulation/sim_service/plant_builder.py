import httpx
from .physics.chiller import CentrifugalChiller
from .physics.pump import Pump
from .physics.cooling_tower import CoolingTower
from .physics.valve import ControlValve, IsolationValve, CheckValve
from .physics.pipe import PipeSegment as PipePhysics


class PlantAssembly:
    """Container for assembled plant."""

    def __init__(self):
        self.chillers: dict[str, CentrifugalChiller] = {}
        self.pumps: dict[str, Pump] = {}
        self.cooling_towers: dict[str, CoolingTower] = {}
        self.valves: dict[str, ControlValve | IsolationValve | CheckValve] = {}
        self.pipes: dict[str, PipePhysics] = {}
        self.point_connections: list[tuple[str, str]] = []


async def build_plant_from_services(plant_id: str, asset_url: str, env_url: str) -> PlantAssembly:
    """Fetch plant topology from Asset Service, build physics models."""
    assembly = PlantAssembly()

    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{asset_url}/api/plants/{plant_id}")
        resp.raise_for_status()
        plant = resp.json()

        resp = await client.get(f"{asset_url}/api/equipment?plant_id={plant_id}")
        resp.raise_for_status()
        equipment_list = resp.json()

        for eq in equipment_list:
            dp = eq.get("design_params", {})
            resp2 = await client.get(
                f"{asset_url}/api/templates/equipment-types/{eq['equipment_type_id']}"
            )
            resp2.raise_for_status()
            etype = resp2.json()

            if etype["category"] == "chiller":
                ch = CentrifugalChiller(
                    name=eq["name"],
                    capacity_rt=dp.get("capacity_rt", 500),
                    design_cop=dp.get("design_cop", 6.0),
                    design_chw_supply_temp=dp.get("design_chw_supply_temp", 7.0),
                    design_cw_entering_temp=dp.get("design_cw_entering_temp", 30.0),
                    min_plr=dp.get("min_plr", 0.2),
                )
                assembly.chillers[eq["id"]] = ch
            elif etype["category"] == "pump":
                p = Pump(
                    name=eq["name"],
                    rated_power_kw=dp.get("rated_power_kw", 37),
                    rated_flow_lps=dp.get("rated_flow_lps", 100),
                    rated_head_m=dp.get("rated_head_m", 32),
                )
                assembly.pumps[eq["id"]] = p
            elif etype["category"] == "cooling_tower":
                ct = CoolingTower(
                    name=eq["name"],
                    design_heat_rejection_kw=dp.get("design_heat_rejection_kw", 1750),
                    design_flow_lps=dp.get("design_flow_lps", 80),
                    rated_fan_power_kw=dp.get("rated_fan_power_kw", 15),
                )
                assembly.cooling_towers[eq["id"]] = ct
            elif etype["category"] == "valve":
                v = ControlValve(
                    name=eq["name"],
                    cv=dp.get("cv", 100),
                    characteristic=dp.get("characteristic", "equal_percentage"),
                )
                assembly.valves[eq["id"]] = v

        for seg in plant.get("pipe_segments", []):
            ps = PipePhysics(
                name=seg["id"],
                diameter_mm=seg.get("diameter_mm", 200),
                length_m=seg.get("length_m", 5.0),
                roughness_mm=seg.get("roughness_mm", 0.045),
            )
            assembly.pipes[seg["id"]] = ps
            assembly.point_connections.append((seg["from_point_id"], seg["to_point_id"]))

    return assembly

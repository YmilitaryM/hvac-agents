from typing import Optional
from enum import Enum

from pydantic import BaseModel


class FluidType(str, Enum):
    CHILLED_WATER = "chilled_water"
    COOLING_WATER = "cooling_water"
    HOT_WATER = "hot_water"


class LoopType(str, Enum):
    PRIMARY = "primary"
    SECONDARY = "secondary"
    TERTIARY = "tertiary"


class DataSourceMode(str, Enum):
    SIMULATED = "simulated"
    LIVE = "live"
    HYBRID = "hybrid"


class LoopSchema(BaseModel):
    id: str
    plant_id: str
    name: str
    fluid_type: FluidType
    loop_type: LoopType
    is_active: bool = True

    model_config = {"from_attributes": True}


class PipeSegmentSchema(BaseModel):
    id: str
    loop_id: str
    from_point_id: str
    to_point_id: str
    diameter_mm: float = 200
    length_m: float = 5.0
    roughness_mm: float = 0.045
    insulation_type: str = "none"
    valve_id: Optional[str] = None

    model_config = {"from_attributes": True}


class PlantSchema(BaseModel):
    id: str
    name: str
    description: str = ""
    site_id: Optional[str] = None
    data_source_mode: DataSourceMode = DataSourceMode.SIMULATED
    is_active: bool = True
    loops: list[LoopSchema] = []
    pipe_segments: list[PipeSegmentSchema] = []

    model_config = {"from_attributes": True}

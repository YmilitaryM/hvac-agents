from enum import Enum
from typing import Optional
from datetime import datetime

from pydantic import BaseModel, Field


class IODirection(str, Enum):
    INPUT = "input"
    CALC = "calc"
    OUTPUT = "output"


class EquipmentCategory(str, Enum):
    CHILLER = "chiller"
    PUMP = "pump"
    COOLING_TOWER = "cooling_tower"
    VALVE = "valve"
    PIPE = "pipe"
    SENSOR = "sensor"


class PointTemplateSchema(BaseModel):
    id: str
    code: str
    name: str
    unit: str = ""
    data_type: str = "float"
    io_direction: IODirection
    required: bool = False
    sort_order: int = 0

    model_config = {"from_attributes": True}


class EquipmentTypeSchema(BaseModel):
    id: str
    type_code: str
    type_name: str
    category: EquipmentCategory
    points: list[PointTemplateSchema] = []

    model_config = {"from_attributes": True}


class EquipmentPointSchema(BaseModel):
    id: str
    equipment_id: str
    point_template_id: str
    code: str
    name: str
    unit: str
    io_direction: IODirection
    current_value: Optional[float] = None
    last_updated: Optional[float] = None

    model_config = {"from_attributes": True}


class EquipmentSchema(BaseModel):
    id: str
    name: str
    equipment_type_id: str
    plant_id: Optional[str] = None
    design_params: dict = {}
    is_active: bool = True
    points: list[EquipmentPointSchema] = []
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}

from pathlib import Path
from typing import Optional

import yaml
from pydantic import BaseModel


class AcquisitionConfig(BaseModel):
    poll_interval_ms: int = 1000
    protocols: list[dict] = []


class ControlConfig(BaseModel):
    safety_gate: bool = True
    pid_enabled: bool = True
    interlock_enabled: bool = True


class InspectionConfig(BaseModel):
    plans_dir: str = "/etc/hvac-edge/plans"
    default_interval_hours: int = 4


class MLConfig(BaseModel):
    onnx_model_path: str = ""
    feature_window_hours: int = 24


class EdgeConfig(BaseModel):
    edge_id: str = ""
    plant_id: str = ""
    mode: str = "hybrid"
    cloud_api_url: str = "http://localhost:8006"
    mqtt_broker_host: str = "localhost"
    mqtt_broker_port: int = 1883
    acquisition: AcquisitionConfig = AcquisitionConfig()
    control: ControlConfig = ControlConfig()
    inspection: InspectionConfig = InspectionConfig()
    ml: MLConfig = MLConfig()
    db_path: str = "edge_data.duckdb"


def load_config(path: str | Path = "edge_config.yaml") -> EdgeConfig:
    path = Path(path)
    if path.exists():
        with open(path) as f:
            data = yaml.safe_load(f) or {}
    else:
        data = {}
    return EdgeConfig(**data)

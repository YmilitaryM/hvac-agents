from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from ..poller import PollingPoint
from ..adapters.base import ProtocolBinding

router = APIRouter()


class RegisterPointRequest(BaseModel):
    point_id: str
    equipment_id: str
    plant_id: str
    point_code: str
    protocol: str
    protocol_config: dict
    poll_interval_sec: float = 10.0


@router.post("/points/register")
async def register_point(req: RegisterPointRequest, request: Request):
    poller = request.app.state.poller
    binding = ProtocolBinding(protocol=req.protocol, config=req.protocol_config)

    from ..adapters.modbus_adapter import ModbusAdapter
    from ..adapters.bacnet_adapter import BacnetAdapter
    from ..adapters.opcua_adapter import OpcUaAdapter

    adapters = {"modbus": ModbusAdapter, "bacnet": BacnetAdapter, "opc_ua": OpcUaAdapter}
    adapter_cls = adapters.get(req.protocol)
    if adapter_cls is None:
        raise HTTPException(status_code=400, detail=f"Unsupported protocol: {req.protocol}")

    adapter = adapter_cls()
    try:
        await adapter.connect(binding)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Connection failed: {e}")

    point = PollingPoint(
        point_id=req.point_id, equipment_id=req.equipment_id,
        plant_id=req.plant_id, point_code=req.point_code,
        binding=binding, poll_interval_sec=req.poll_interval_sec
    )
    poller.register_point(point, adapter)
    return {"status": "registered", "point_id": req.point_id}


@router.delete("/points/{point_id}")
async def unregister_point(point_id: str, request: Request):
    request.app.state.poller.unregister_point(point_id)
    return {"status": "unregistered", "point_id": point_id}


@router.get("/points")
async def list_points(request: Request):
    poller = request.app.state.poller
    points = []
    for pid, (pt, _) in poller._points.items():
        points.append({
            "point_id": pid, "point_code": pt.point_code,
            "equipment_id": pt.equipment_id, "plant_id": pt.plant_id,
            "protocol": pt.binding.protocol, "poll_interval_sec": pt.poll_interval_sec,
            "last_value": pt.last_value,
        })
    return {"points": points, "count": len(points)}

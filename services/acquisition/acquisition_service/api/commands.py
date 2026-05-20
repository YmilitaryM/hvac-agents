from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from ..adapters.base import WriteError

router = APIRouter()


class WriteCommandRequest(BaseModel):
    point_id: str
    value: float
    emergency: bool = False
    operator: str | None = None


class WriteCommandResponse(BaseModel):
    success: bool
    point_id: str
    value: float
    timestamp: str


_last_writes: dict[str, float] = {}
MIN_WRITE_INTERVAL = 1.0


def _check_write_rate(point_id: str) -> None:
    now = datetime.now(timezone.utc).timestamp()
    if point_id in _last_writes:
        if now - _last_writes[point_id] < MIN_WRITE_INTERVAL:
            raise HTTPException(status_code=429, detail="Write rate limit exceeded")


def _check_value_range(point_config: dict, value: float) -> None:
    min_val = point_config.get("min_value")
    max_val = point_config.get("max_value")
    if min_val is not None and value < min_val:
        raise HTTPException(status_code=400, detail=f"Value {value} below minimum {min_val}")
    if max_val is not None and value > max_val:
        raise HTTPException(status_code=400, detail=f"Value {value} above maximum {max_val}")


@router.post("/commands/write", response_model=WriteCommandResponse)
async def write_point(req: WriteCommandRequest, request: Request):
    poller = request.app.state.poller
    point_data = poller._points.get(req.point_id)

    if point_data is None:
        raise HTTPException(status_code=404, detail=f"Point {req.point_id} not registered for polling")

    pt, adapter = point_data

    if not req.emergency:
        _check_write_rate(req.point_id)

    try:
        await adapter.write_point(req.point_id, pt.binding, req.value)
    except WriteError as e:
        raise HTTPException(status_code=502, detail=str(e))

    _last_writes[req.point_id] = datetime.now(timezone.utc).timestamp()

    return WriteCommandResponse(
        success=True, point_id=req.point_id, value=req.value,
        timestamp=datetime.now(timezone.utc).isoformat()
    )


@router.get("/commands/history")
async def command_history(point_id: str | None = None):
    return {"commands": []}

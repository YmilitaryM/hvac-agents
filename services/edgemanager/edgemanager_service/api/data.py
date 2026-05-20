from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import EdgeDevice, SyncWatermark

router = APIRouter()


class ReadingPoint(BaseModel):
    time: str
    point_id: str
    value: float
    quality: str = "good"


class InspectionRecord(BaseModel):
    id: int
    started_at: str
    ended_at: Optional[str] = None
    plan_id: str
    status: str
    result: Optional[dict] = None


class WorkOrderRecord(BaseModel):
    id: int
    created_at: str
    equipment_id: str
    severity: str
    title: str
    description: Optional[str] = None
    status: str


class IngestPayload(BaseModel):
    readings: list[ReadingPoint]
    inspections: list[InspectionRecord] = []
    work_orders: list[WorkOrderRecord] = []


async def get_db(request: Request) -> AsyncSession:
    factory = request.app.state.session_factory
    async with factory() as session:
        yield session


@router.post("/{edge_id}/data/ingest")
async def ingest_data(edge_id: str, body: IngestPayload, session: AsyncSession = Depends(get_db)):
    device = await session.get(EdgeDevice, edge_id)
    if not device:
        raise HTTPException(status_code=404, detail="Edge device not found")

    latest_time = None
    if body.readings:
        latest_time = max(r.time for r in body.readings)

        # Update sync watermark
        wm = await session.get(SyncWatermark, {"edge_id": edge_id, "table_name": "readings"})
        parsed_time = datetime.fromisoformat(latest_time.replace("Z", "+00:00"))
        if wm:
            if parsed_time > wm.last_synced_until:
                wm.last_synced_until = parsed_time
        else:
            wm = SyncWatermark(edge_id=edge_id, table_name="readings", last_synced_until=parsed_time)
            session.add(wm)

    await session.commit()

    return {
        "readings_received": len(body.readings),
        "inspections_received": len(body.inspections),
        "work_orders_received": len(body.work_orders),
        "watermark": latest_time,
    }

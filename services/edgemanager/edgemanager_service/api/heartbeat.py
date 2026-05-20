from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from ..models import EdgeDevice, Heartbeat

router = APIRouter()


class HeartbeatRequest(BaseModel):
    cpu_pct: Optional[float] = None
    mem_mb: Optional[float] = None
    disk_pct: Optional[float] = None
    collector_ok: Optional[bool] = None
    controller_ok: Optional[bool] = None
    inspector_ok: Optional[bool] = None


async def get_db(request: Request) -> AsyncSession:
    factory = request.app.state.session_factory
    async with factory() as session:
        yield session


@router.post("/{edge_id}/heartbeat")
async def post_heartbeat(edge_id: str, body: HeartbeatRequest, session: AsyncSession = Depends(get_db)):
    device = await session.get(EdgeDevice, edge_id)
    if not device:
        raise HTTPException(status_code=404, detail="Edge device not found")

    now = datetime.now(timezone.utc)
    hb = Heartbeat(
        edge_id=edge_id,
        received_at=now,
        cpu_pct=body.cpu_pct,
        mem_mb=body.mem_mb,
        disk_pct=body.disk_pct,
        collector_ok=body.collector_ok,
        controller_ok=body.controller_ok,
        inspector_ok=body.inspector_ok,
    )
    device.last_seen_at = now
    session.add(hb)
    await session.commit()
    return {"status": "ok"}


@router.get("/{edge_id}/status")
async def get_status(edge_id: str, session: AsyncSession = Depends(get_db)):
    device = await session.get(EdgeDevice, edge_id)
    if not device:
        raise HTTPException(status_code=404, detail="Edge device not found")

    result = await session.execute(
        select(Heartbeat).where(Heartbeat.edge_id == edge_id).order_by(desc(Heartbeat.received_at)).limit(1)
    )
    latest = result.scalar_one_or_none()

    return {
        "device_id": edge_id,
        "online": device.last_seen_at is not None,
        "last_seen_at": device.last_seen_at.isoformat() if device.last_seen_at else None,
        "latest_heartbeat": {
            "cpu_pct": latest.cpu_pct,
            "mem_mb": latest.mem_mb,
            "disk_pct": latest.disk_pct,
            "collector_ok": latest.collector_ok,
            "controller_ok": latest.controller_ok,
            "inspector_ok": latest.inspector_ok,
        } if latest else None,
    }

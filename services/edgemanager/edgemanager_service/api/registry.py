from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import EdgeDevice

router = APIRouter()


class RegisterRequest(BaseModel):
    id: str
    name: str
    plant_id: str
    mode: str = "hybrid"
    version: str


class EdgeDeviceResponse(BaseModel):
    id: str
    name: str
    plant_id: str
    mode: str
    version: str
    registered_at: str | None = None
    last_seen_at: str | None = None


async def get_db(request: Request) -> AsyncSession:
    factory = request.app.state.session_factory
    async with factory() as session:
        yield session


@router.post("/register", status_code=201, response_model=EdgeDeviceResponse)
async def register_device(body: RegisterRequest, session: AsyncSession = Depends(get_db)):
    existing = await session.get(EdgeDevice, body.id)
    if existing:
        raise HTTPException(status_code=409, detail="Edge device already registered")

    device = EdgeDevice(
        id=body.id,
        name=body.name,
        plant_id=body.plant_id,
        mode=body.mode,
        version=body.version,
        registered_at=datetime.now(timezone.utc),
    )
    session.add(device)
    await session.commit()
    await session.refresh(device)
    return _to_response(device)


@router.get("/", response_model=list[EdgeDeviceResponse])
async def list_devices(session: AsyncSession = Depends(get_db)):
    result = await session.execute(select(EdgeDevice).order_by(EdgeDevice.registered_at.desc()))
    return [_to_response(d) for d in result.scalars().all()]


@router.get("/{edge_id}", response_model=EdgeDeviceResponse)
async def get_device(edge_id: str, session: AsyncSession = Depends(get_db)):
    device = await session.get(EdgeDevice, edge_id)
    if not device:
        raise HTTPException(status_code=404, detail="Edge device not found")
    return _to_response(device)


def _to_response(d: EdgeDevice) -> dict:
    return {
        "id": d.id,
        "name": d.name,
        "plant_id": d.plant_id,
        "mode": d.mode,
        "version": d.version,
        "registered_at": d.registered_at.isoformat() if d.registered_at else None,
        "last_seen_at": d.last_seen_at.isoformat() if d.last_seen_at else None,
    }

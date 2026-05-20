import hashlib
import json

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import EdgeDevice

router = APIRouter()


class ConfigPayload(BaseModel):
    mode: str | None = None
    acquisition: dict | None = None
    control: dict | None = None
    inspection: dict | None = None
    ml: dict | None = None


async def get_db(request: Request) -> AsyncSession:
    factory = request.app.state.session_factory
    async with factory() as session:
        yield session


def _hash_config(cfg: dict) -> str:
    raw = json.dumps(cfg, sort_keys=True)
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


@router.post("/{edge_id}/config")
async def set_config(edge_id: str, body: ConfigPayload, session: AsyncSession = Depends(get_db)):
    device = await session.get(EdgeDevice, edge_id)
    if not device:
        raise HTTPException(status_code=404, detail="Edge device not found")

    device.config_hash = _hash_config(body.model_dump(exclude_none=True))
    await session.commit()

    return {
        "edge_id": edge_id,
        "config_hash": device.config_hash,
        "config": body.model_dump(exclude_none=True),
    }


@router.get("/{edge_id}/config")
async def get_config(edge_id: str, session: AsyncSession = Depends(get_db)):
    device = await session.get(EdgeDevice, edge_id)
    if not device:
        raise HTTPException(status_code=404, detail="Edge device not found")

    return {
        "edge_id": edge_id,
        "config_hash": device.config_hash,
    }

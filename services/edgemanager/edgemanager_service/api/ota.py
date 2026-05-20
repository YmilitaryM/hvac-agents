from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..models import EdgeDevice, OTATask

router = APIRouter()


class OTACreateRequest(BaseModel):
    target_type: str
    version: str
    payload_url: str


class OTATaskResponse(BaseModel):
    id: int
    edge_id: str
    target_type: str
    version: str
    payload_url: str
    status: str
    created_at: str | None
    completed_at: str | None


async def get_db(request: Request) -> AsyncSession:
    factory = request.app.state.session_factory
    async with factory() as session:
        yield session


def _to_response(t: OTATask) -> dict:
    return {
        "id": t.id,
        "edge_id": t.edge_id,
        "target_type": t.target_type,
        "version": t.version,
        "payload_url": t.payload_url,
        "status": t.status,
        "created_at": t.created_at.isoformat() if t.created_at else None,
        "completed_at": t.completed_at.isoformat() if t.completed_at else None,
    }


@router.post("/{edge_id}/ota", status_code=201, response_model=OTATaskResponse)
async def create_ota(edge_id: str, body: OTACreateRequest, session: AsyncSession = Depends(get_db)):
    device = await session.get(EdgeDevice, edge_id)
    if not device:
        raise HTTPException(status_code=404, detail="Edge device not found")

    task = OTATask(
        edge_id=edge_id,
        target_type=body.target_type,
        version=body.version,
        payload_url=body.payload_url,
    )
    session.add(task)
    await session.commit()
    await session.refresh(task)
    return _to_response(task)


@router.get("/{edge_id}/ota/{task_id}", response_model=OTATaskResponse)
async def get_ota(edge_id: str, task_id: int, session: AsyncSession = Depends(get_db)):
    task = await session.get(OTATask, task_id)
    if not task or task.edge_id != edge_id:
        raise HTTPException(status_code=404, detail="OTA task not found")
    return _to_response(task)


@router.get("/{edge_id}/ota/", response_model=list[OTATaskResponse])
async def list_ota(edge_id: str, session: AsyncSession = Depends(get_db)):
    result = await session.execute(
        select(OTATask).where(OTATask.edge_id == edge_id).order_by(OTATask.created_at.desc())
    )
    return [_to_response(t) for t in result.scalars().all()]

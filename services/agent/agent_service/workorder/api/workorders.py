from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import WorkOrder, WorkOrderLog
from ..lifecycle import transition as do_transition

router = APIRouter()


class CreateWorkOrderRequest(BaseModel):
    edge_id: str
    equipment_id: str
    severity: str
    title: str
    description: str | None = None
    source: str = "auto"


class TransitionRequest(BaseModel):
    to_status: str
    changed_by: str = "system"
    note: str | None = None


async def get_db(request: Request) -> AsyncSession:
    factory = request.app.state.session_factory
    async with factory() as session:
        yield session


@router.post("/", status_code=201)
async def create_work_order(body: CreateWorkOrderRequest, session: AsyncSession = Depends(get_db)):
    wo = WorkOrder(
        edge_id=body.edge_id,
        equipment_id=body.equipment_id,
        severity=body.severity,
        title=body.title,
        description=body.description,
        source=body.source,
    )
    session.add(wo)
    await session.commit()
    await session.refresh(wo)
    return _to_dict(wo)


@router.get("/")
async def list_work_orders(status: str | None = None, edge_id: str | None = None,
                           session: AsyncSession = Depends(get_db)):
    q = select(WorkOrder).order_by(WorkOrder.created_at.desc())
    if status:
        q = q.where(WorkOrder.status == status)
    if edge_id:
        q = q.where(WorkOrder.edge_id == edge_id)
    result = await session.execute(q)
    return [_to_dict(wo) for wo in result.scalars().all()]


@router.get("/{wo_id}")
async def get_work_order(wo_id: int, session: AsyncSession = Depends(get_db)):
    wo = await session.get(WorkOrder, wo_id)
    if not wo:
        raise HTTPException(status_code=404, detail="Work order not found")
    return _to_dict(wo)


@router.post("/{wo_id}/transition")
async def transition_work_order(wo_id: int, body: TransitionRequest, session: AsyncSession = Depends(get_db)):
    wo = await session.get(WorkOrder, wo_id)
    if not wo:
        raise HTTPException(status_code=404, detail="Work order not found")

    try:
        log_data = do_transition(wo, body.to_status, body.changed_by, body.note)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    log = WorkOrderLog(
        work_order_id=wo_id,
        from_status=log_data["from_status"],
        to_status=log_data["to_status"],
        changed_by=log_data["changed_by"],
        note=log_data["note"],
    )
    session.add(log)
    await session.commit()
    await session.refresh(wo)
    return _to_dict(wo)


def _to_dict(wo: WorkOrder) -> dict:
    return {
        "id": wo.id,
        "edge_id": wo.edge_id,
        "equipment_id": wo.equipment_id,
        "severity": wo.severity,
        "title": wo.title,
        "description": wo.description,
        "status": wo.status,
        "assigned_to": wo.assigned_to,
        "source": wo.source,
        "created_at": wo.created_at.isoformat() if wo.created_at else None,
        "updated_at": wo.updated_at.isoformat() if wo.updated_at else None,
        "resolved_at": wo.resolved_at.isoformat() if wo.resolved_at else None,
    }

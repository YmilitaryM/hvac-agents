"""Audit log query API."""
from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import select, desc
from common.auth import require_role
from ..models import AuditLogModel

router = APIRouter()


@router.get("/logs")
async def list_audit_logs(
    request: Request,
    user_id: str = Query(None),
    action: str = Query(None),
    resource_type: str = Query(None),
    limit: int = Query(default=100, le=1000),
    _user=Depends(require_role("ADMIN", "AUDITOR")),
):
    """List audit logs with optional filters."""
    session_factory = request.app.state.session_factory
    async with session_factory() as session:
        stmt = select(AuditLogModel).order_by(desc(AuditLogModel.timestamp))
        if user_id:
            stmt = stmt.where(AuditLogModel.user_id == user_id)
        if action:
            stmt = stmt.where(AuditLogModel.action == action)
        if resource_type:
            stmt = stmt.where(AuditLogModel.resource_type == resource_type)
        stmt = stmt.limit(limit)

        result = await session.execute(stmt)
        logs = result.scalars().all()

        return {
            "logs": [
                {
                    "id": log.id,
                    "timestamp": str(log.timestamp),
                    "user_id": log.user_id,
                    "username": log.username,
                    "action": log.action,
                    "resource_type": log.resource_type,
                    "resource_id": log.resource_id,
                    "method": log.method,
                    "path": log.path,
                    "ip_address": log.ip_address,
                    "status_code": log.status_code,
                    "success": log.success,
                }
                for log in logs
            ],
            "count": len(logs),
        }


@router.get("/logs/{log_id}")
async def get_audit_log(
    log_id: str,
    request: Request,
    _user=Depends(require_role("ADMIN", "AUDITOR")),
):
    """Get a single audit log entry with full details."""
    session_factory = request.app.state.session_factory
    async with session_factory() as session:
        result = await session.execute(
            select(AuditLogModel).where(AuditLogModel.id == log_id)
        )
        log = result.scalar_one_or_none()
        if not log:
            return {"error": "Not found"}

        return {
            "id": log.id,
            "timestamp": str(log.timestamp),
            "user_id": log.user_id,
            "username": log.username,
            "action": log.action,
            "resource_type": log.resource_type,
            "resource_id": log.resource_id,
            "method": log.method,
            "path": log.path,
            "old_value": log.old_value,
            "new_value": log.new_value,
            "ip_address": log.ip_address,
            "user_agent": log.user_agent,
            "status_code": log.status_code,
            "success": log.success,
        }


@router.get("/logs/export")
async def export_audit_logs(
    request: Request,
    _user=Depends(require_role("ADMIN", "AUDITOR")),
):
    """Export audit logs as CSV."""
    session_factory = request.app.state.session_factory
    async with session_factory() as session:
        result = await session.execute(
            select(AuditLogModel).order_by(desc(AuditLogModel.timestamp)).limit(10000)
        )
        logs = result.scalars().all()

        csv_lines = [
            "timestamp,user_id,username,action,resource_type,resource_id,method,path,ip_address,status_code,success"
        ]
        for log in logs:
            csv_lines.append(
                f"{log.timestamp},{log.user_id},{log.username},{log.action},"
                f"{log.resource_type},{log.resource_id or ''},{log.method},"
                f"{log.path},{log.ip_address},{log.status_code},{log.success}"
            )

        return {"csv": "\n".join(csv_lines), "count": len(logs)}

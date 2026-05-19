"""Audit logging middleware - intercepts all write requests.

Reads request body without consuming the stream so downstream proxy can still use it.
"""
import asyncio
import json
import re
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from .models import AuditLogModel

_UUID_RE = re.compile(
    r'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$'
)


class AuditMiddleware(BaseHTTPMiddleware):
    """Log all POST/PUT/DELETE/PATCH requests to audit log."""

    async def dispatch(self, request: Request, call_next):
        if request.method in ("GET", "HEAD", "OPTIONS"):
            return await call_next(request)

        body = None
        if request.method in ("POST", "PUT", "DELETE", "PATCH"):
            try:
                body_bytes = await request.body()
                if body_bytes:
                    body = json.loads(body_bytes)
            except Exception:
                body = None

        user = getattr(request.state, "user", {})
        user_id = user.get("sub", "anonymous") if isinstance(user, dict) else "anonymous"
        username = user.get("username", user_id) if isinstance(user, dict) else user_id

        response = await call_next(request)

        if request.method in ("POST", "PUT", "DELETE", "PATCH"):
            asyncio.create_task(self._save_audit_log(
                request=request,
                user_id=user_id,
                username=username,
                request_body=body,
                status_code=response.status_code,
            ))

        return response

    async def _save_audit_log(self, request: Request, user_id: str, username: str,
                              request_body: dict, status_code: int):
        try:
            session_factory = getattr(request.app.state, "session_factory", None)
            if not session_factory:
                return

            path = request.url.path
            method = request.method
            parts = path.strip("/").split("/")
            resource_type = parts[1] if len(parts) >= 2 and parts[0] == "api" else "unknown"
            resource_id = ""
            for part in parts[2:]:
                # Match standard UUIDs first, then hex ids (8+ alnum chars)
                if _UUID_RE.match(part) or (part.isalnum() and len(part) >= 8):
                    resource_id = part
                    break

            async with session_factory() as session:
                entry = AuditLogModel(
                    user_id=user_id,
                    username=username,
                    action=f"{resource_type}.{method.lower()}",
                    resource_type=resource_type,
                    resource_id=resource_id,
                    method=method,
                    path=path,
                    new_value=request_body,
                    old_value=None,
                    ip_address=request.client.host if request.client else "",
                    user_agent=request.headers.get("user-agent", ""),
                    status_code=status_code,
                    success=200 <= status_code < 400,
                )
                session.add(entry)
                await session.commit()
        except Exception:
            pass

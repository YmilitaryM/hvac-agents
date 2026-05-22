"""FastAPI middleware that injects tenant context for every request.

Resolution order (MVP):
1. ``X-Tenant-Id`` header  -- set by the gateway after auth
2. JWT ``sub`` claim      -- fallback for direct service access
3. Default tenant_id = 1  -- no-reject MVP path

The tenant context is cleared when the request finishes so it never
leaks across requests.
"""

import logging
from typing import Optional

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response as StarletteResponse

from .config import get_settings
from .tenant import current_tenant_id, set_current_tenant

logger = logging.getLogger(__name__)

# Default tenant id used when no tenant can be resolved.
# In production this should be removed once every user is assigned a tenant.
MVP_DEFAULT_TENANT_ID = 1


class TenantMiddleware(BaseHTTPMiddleware):
    """Resolve the tenant for the current request and set the ContextVar.

    Add to any service app::

        from common.tenant_middleware import TenantMiddleware
        app.add_middleware(TenantMiddleware)
    """

    async def dispatch(
        self, request: Request, call_next
    ) -> StarletteResponse:
        tenant_id = self._resolve_tenant(request)
        token = set_current_tenant(tenant_id)
        try:
            response = await call_next(request)
            return response
        finally:
            current_tenant_id.reset(token)

    def _resolve_tenant(self, request: Request) -> int:
        """Resolve tenant_id from headers or JWT, falling back to default."""

        # 1. X-Tenant-Id header (set by gateway proxy)
        header_value = request.headers.get("X-Tenant-Id")
        if header_value is not None:
            try:
                return int(header_value)
            except (ValueError, TypeError):
                logger.warning(
                    "Invalid X-Tenant-Id header: %s", header_value
                )

        # 2. JWT token (for services called directly)
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            try:
                token_str = auth_header[7:]
                from .auth import decode_token
                claims = decode_token(token_str)
                # For now user-to-tenant mapping is 1:1 with default
                # Future: look up user.tenant_id from DB
                return MVP_DEFAULT_TENANT_ID
            except Exception:
                logger.debug(
                    "Could not decode JWT for tenant resolution",
                    exc_info=True,
                )

        # 3. Default tenant (MVP — never reject)
        logger.debug(
            "No tenant resolved for %s %s, defaulting to %d",
            request.method,
            request.url.path,
            MVP_DEFAULT_TENANT_ID,
        )
        return MVP_DEFAULT_TENANT_ID

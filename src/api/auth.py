"""API Key authentication dependency for FastAPI.

Usage:
    from src.api.auth import require_auth

    @router.post("/endpoint")
    async def my_endpoint(user=Depends(require_auth)):
        ...
"""

import logging
from typing import Optional

from fastapi import Depends, HTTPException, Security
from fastapi.security import APIKeyHeader

from src.config import get_config

logger = logging.getLogger(__name__)
_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def require_auth(api_key: str = Security(_api_key_header)) -> bool:
    """Validate API key. No-op when API_KEY is not configured."""
    expected = get_config().api_key
    if not expected:
        return True
    if api_key == expected:
        return True
    raise HTTPException(status_code=401, detail="Invalid or missing API key")

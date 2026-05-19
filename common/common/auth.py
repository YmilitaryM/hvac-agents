import time
from enum import Enum
from typing import Annotated

from fastapi import Depends, HTTPException, security
from jose import JWTError, jwt

from .config import get_settings


class Role(str, Enum):
    VIEWER = "viewer"
    OPERATOR = "operator"
    ENGINEER = "engineer"
    ADMIN = "admin"
    AUDITOR = "auditor"


def create_token(user_id: str, role: Role) -> str:
    s = get_settings()
    now = int(time.time())
    claims = {"sub": user_id, "role": role.value, "iat": now, "exp": now + s.jwt_expire_minutes * 60}
    return jwt.encode(claims, s.jwt_secret, algorithm=s.jwt_algorithm)


def decode_token(token: str) -> dict:
    s = get_settings()
    try:
        return jwt.decode(token, s.jwt_secret, algorithms=[s.jwt_algorithm])
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")


oauth2_scheme = security.OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_current_user(token: Annotated[str, Depends(oauth2_scheme)]) -> dict:
    return decode_token(token)


def require_role(*roles: Role):
    """Dependency: only allow specified roles."""
    def checker(user: dict = Depends(get_current_user)) -> dict:
        if user.get("role") not in [r.value for r in roles]:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return user
    return checker

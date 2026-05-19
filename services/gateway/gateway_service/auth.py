from fastapi import APIRouter, HTTPException, Request
from passlib.context import CryptContext
from sqlalchemy import select

from common.auth import create_token, Role
from .models import UserModel

router = APIRouter()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


@router.post("/auth/register")
async def register(data: dict, request: Request):
    async with request.app.state.session_factory() as session:
        existing = await session.execute(
            select(UserModel).where(UserModel.username == data["username"])
        )
        if existing.scalar_one_or_none():
            raise HTTPException(409, "Username already exists")
        user = UserModel(
            username=data["username"],
            hashed_password=pwd_context.hash(data["password"]),
            role=data.get("role", "viewer"),
        )
        session.add(user)
        await session.commit()
        return {"status": "ok", "user_id": user.id}


@router.post("/auth/login")
async def login(data: dict, request: Request):
    async with request.app.state.session_factory() as session:
        result = await session.execute(
            select(UserModel).where(UserModel.username == data["username"])
        )
        user = result.scalar_one_or_none()
        if not user or not pwd_context.verify(data["password"], user.hashed_password):
            raise HTTPException(401, "Invalid credentials")
        if not user.is_active:
            raise HTTPException(403, "Account disabled")
        token = create_token(user.id, Role(user.role))
        return {"access_token": token, "token_type": "bearer", "role": user.role}

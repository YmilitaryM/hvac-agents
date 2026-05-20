"""Shared test fixtures for Edge Manager service tests.

Uses SQLite in-memory database to avoid requiring a real PostgreSQL connection.
"""

import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from edgemanager_service.main import app
from edgemanager_service.models import Base


@pytest_asyncio.fixture
async def engine():
    """Create an in-memory SQLite engine and create all tables."""
    engine = create_async_engine("sqlite+aiosqlite://", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    try:
        yield engine
    finally:
        await engine.dispose()


@pytest_asyncio.fixture
async def setup_app(engine):
    """Configure the FastAPI app with the test database session factory."""
    app.state.engine = engine
    app.state.session_factory = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    yield
    # Clean up app state after tests
    app.state.session_factory = None
    app.state.engine = None

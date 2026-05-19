import asyncio
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.config import get_config

logger = logging.getLogger(__name__)

_engine = None
_sessionmaker: Optional[async_sessionmaker] = None
_init_lock = asyncio.Lock()


async def init_db(database_url: Optional[str] = None) -> None:
    """Initialize the database engine and create all tables."""
    global _engine, _sessionmaker

    url = database_url or get_config().storage.db_url
    if not url or not url.strip():
        logger.warning("No DATABASE_URL configured — using ephemeral in-memory SQLite. Data will be lost on restart.")
        url = "sqlite+aiosqlite:///:memory:"

    _engine = create_async_engine(url, echo=False, pool_size=5, max_overflow=10)
    _sessionmaker = async_sessionmaker(_engine, expire_on_commit=False)

    from src.db.base import Base

    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    logger.info("Database initialized: %s", _engine.url.render_as_string(hide_password=True))


async def close_db() -> None:
    """Close the database engine."""
    global _engine, _sessionmaker
    if _engine:
        await _engine.dispose()
        _engine = None
        _sessionmaker = None
        logger.info("Database connection closed")


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Get an async database session. Use as FastAPI Depends."""
    global _sessionmaker
    if _sessionmaker is None:
        async with _init_lock:
            if _sessionmaker is None:
                await init_db()
    async with _sessionmaker() as session:
        yield session


def is_db_available() -> bool:
    """Check if the database engine has been initialized."""
    return _engine is not None

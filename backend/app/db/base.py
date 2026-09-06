"""
Async engine and session factory.

The database is OPTIONAL. If DATABASE_URL is unset the whole persistence layer
stays dormant and /analyze keeps working exactly as before — this backend was
useful before it had a database and should not stop being useful if the database
is unreachable.
"""

from __future__ import annotations

import logging
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from app.db.models import Base
from app.utils.errors import DatabaseUnavailableError

log = logging.getLogger(__name__)

_engine: AsyncEngine | None = None
_sessionmaker: async_sessionmaker[AsyncSession] | None = None


def normalise_url(url: str) -> str:
    """
    Managed providers hand out libpq-style URLs; SQLAlchemy needs the asyncpg
    driver named explicitly. Aiven also appends ?sslmode=require, which asyncpg
    does not accept as a query parameter — it is passed via connect_args instead.
    """
    if url.startswith("postgres://"):
        url = "postgresql+asyncpg://" + url[len("postgres://"):]
    elif url.startswith("postgresql://"):
        url = "postgresql+asyncpg://" + url[len("postgresql://"):]
    # strip libpq-only params asyncpg rejects
    for junk in ("?sslmode=require", "&sslmode=require", "?ssl=true", "&ssl=true"):
        url = url.replace(junk, "")
    return url


def database_enabled(settings) -> bool:
    return bool(getattr(settings, "database_url", None))


def init_engine(settings) -> AsyncEngine | None:
    global _engine, _sessionmaker
    if not database_enabled(settings):
        log.info("DATABASE_URL not set — persistence disabled, /analyze still works")
        return None

    raw = settings.database_url
    url = normalise_url(raw)
    connect_args = {}
    # Aiven requires TLS. asyncpg takes ssl= in connect_args, not in the URL.
    if "sslmode=require" in raw or "aivencloud.com" in raw:
        connect_args["ssl"] = "require"

    _engine = create_async_engine(
        url,
        echo=False,
        pool_pre_ping=True,   # managed instances drop idle connections
        pool_size=5,
        max_overflow=5,
        connect_args=connect_args,
    )
    _sessionmaker = async_sessionmaker(_engine, expire_on_commit=False, class_=AsyncSession)
    log.info("Database engine ready (%s)", url.split("@")[-1].split("?")[0])
    return _engine


async def create_all() -> None:
    """Create tables if absent. Alembic owns migrations; this is for dev/tests."""
    if _engine is None:
        return
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def dispose_engine() -> None:
    global _engine, _sessionmaker
    if _engine is not None:
        await _engine.dispose()
    _engine, _sessionmaker = None, None


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    if _sessionmaker is None:
        raise DatabaseUnavailableError()
    async with _sessionmaker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise

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
    Turn whatever a managed provider hands out into a URL SQLAlchemy accepts.

    Handles three things that bite in practice:

    * Wrapper characters. Aiven's console renders the Service URI inside angle
      brackets and they come along with the copy, so ``<postgres://...>`` is a
      very common paste. Quotes from a shell-quoted .env line likewise.
    * Driver prefix. ``postgres://`` and ``postgresql://`` both need to become
      ``postgresql+asyncpg://``.
    * libpq-only query parameters. asyncpg rejects ``sslmode`` as a DSN
      parameter; TLS is passed through connect_args instead.
    """
    from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

    url = url.strip().strip("<>").strip("'\"").strip()

    for prefix in ("postgres://", "postgresql://"):
        if url.startswith(prefix):
            url = "postgresql+asyncpg://" + url[len(prefix):]
            break

    # Drop libpq-only params rather than string-replacing, so an unusual
    # ordering or an extra parameter does not slip through.
    parts = urlsplit(url)
    keep = [(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True)
            if k.lower() not in {"sslmode", "ssl", "sslrootcert", "channel_binding"}]
    return urlunsplit(parts._replace(query=urlencode(keep)))


def wants_tls(raw_url: str) -> bool:
    """True when the original URL asked for TLS, before it was normalised."""
    low = raw_url.lower()
    return "sslmode=require" in low or "ssl=true" in low or "aivencloud.com" in low


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
    # asyncpg takes ssl= in connect_args, not as a DSN parameter.
    if wants_tls(raw):
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

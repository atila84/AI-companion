"""Database engine, session factory, and reachability check.

Owns the single `AsyncEngine` for the process. The engine is created lazily and
cached, mirroring `config.py::get_settings`, so importing this module never
opens a connection — tests and CLI tools can import it without a live database.

SQLAlchemy's async engine pools connections by default (`QueuePool` semantics
via `AsyncAdaptedQueuePool`), so pooling is configuration here rather than
machinery of our own.

Connecting is deliberately *not* done at startup: unlike a missing
`ANTHROPIC_API_KEY`, which is a config error we can detect instantly and should
fail fast on (see `main.py`), a database that is merely slow to accept
connections is a normal transient condition. Startup validates that
`DATABASE_URL` is well-formed; `/health` reports whether the database is
actually reachable right now.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from functools import lru_cache

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.sql import text

from src.config import Settings, get_settings


def build_engine(settings: Settings) -> AsyncEngine:
    """Create a new engine from explicit settings.

    Separate from `get_engine` because the cached accessor takes no arguments:
    `Settings` is a Pydantic model and therefore unhashable, so it cannot be an
    `lru_cache` parameter. Tests use this to build a throwaway engine.

    Args:
        settings: Settings to build the engine from.

    Returns:
        A new `AsyncEngine`. The caller owns disposing of it.
    """
    return create_async_engine(
        settings.database_url,
        pool_size=settings.database_pool_size,
        max_overflow=settings.database_max_overflow,
        pool_timeout=settings.database_pool_timeout_seconds,
        # Verify a pooled connection before handing it out. Postgres drops idle
        # connections, and without this the first query after an idle period
        # fails instead of transparently reconnecting.
        pool_pre_ping=True,
        echo=False,
    )


@lru_cache
def get_engine() -> AsyncEngine:
    """Return the process-wide async engine, creating it on first use.

    Returns:
        The cached `AsyncEngine`.
    """
    return build_engine(get_settings())


@lru_cache
def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Return the process-wide session factory.

    Returns:
        A session factory bound to the cached engine.
    """
    return async_sessionmaker(
        bind=get_engine(),
        expire_on_commit=False,  # keep attributes usable after commit
        class_=AsyncSession,
    )


async def get_session() -> AsyncIterator[AsyncSession]:
    """Yield a database session, closing it afterwards.

    Intended as a FastAPI dependency. The session is rolled back on an
    exception so a failed request never leaks a dirty transaction back to the
    pool.

    Yields:
        An open `AsyncSession`.
    """
    factory = get_session_factory()
    async with factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


async def check_connection(engine: AsyncEngine | None = None) -> tuple[bool, str | None]:
    """Check whether the database is reachable right now.

    Args:
        engine: Engine to test. Defaults to the cached application engine.

    Returns:
        `(True, None)` when a trivial query succeeds, otherwise `(False, reason)`
        where `reason` is the driver's error message.
    """
    engine = engine or get_engine()
    try:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
    except (SQLAlchemyError, OSError) as exc:
        return False, str(exc)
    return True, None


async def dispose_engine() -> None:
    """Close every pooled connection.

    Called on application shutdown so the process exits without leaving
    connections open on the server.
    """
    if get_engine.cache_info().currsize:
        await get_engine().dispose()

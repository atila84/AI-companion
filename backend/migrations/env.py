"""Alembic environment.

The database URL comes from `Settings`, not from `alembic.ini`. Duplicating it
would mean two places to change and a silent chance of migrating the wrong
database — and `alembic.ini` is checked in, so a real URL must never live there.

`Settings` also validates the URL (async driver required), so `alembic` fails
with the same clear message as the app rather than a driver-level error.
"""

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy.engine import Connection

from src.config import get_settings
from src.db import Base, build_engine

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Autogenerate compares the database against this. A model is only visible once
# it subclasses Base *and* its module is imported here.
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Emit SQL to stdout instead of running it (`alembic upgrade --sql`).

    Used to review or hand off the SQL for a deploy without connecting.
    """
    context.configure(
        url=get_settings().database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        # Detect column type changes, which Alembic ignores by default.
        compare_type=True,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """Run migrations on an open connection.

    Args:
        connection: A synchronous connection provided by `run_sync`.
    """
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Connect with the application's async engine and run migrations."""
    engine = build_engine(get_settings())
    try:
        async with engine.connect() as connection:
            await connection.run_sync(do_run_migrations)
    finally:
        await engine.dispose()


def run_migrations_online() -> None:
    """Run migrations against a live database."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

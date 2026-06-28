"""
Alembic migration environment — async configuration.

This module is executed by Alembic CLI commands (e.g. `alembic upgrade head`).
It reads DATABASE_URL from the application Settings and wires up the async
migration context so that migrations run against the correct database.

All ORM models must be imported (directly or transitively) before this module
runs so that `Base.metadata` contains a complete table registry for
autogenerate to work correctly.
"""

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy.ext.asyncio import create_async_engine

# ── Import the project's Base and all models ─────────────────────────────────
# Importing app.models ensures every ORM class is registered with Base.metadata
# before Alembic inspects it for autogenerate.
from app.database.base import Base
import app.models  # noqa: F401 — side-effect import to register all models

from app.core.config import settings

# ---------------------------------------------------------------------------
# Alembic Config object (gives access to alembic.ini values)
# ---------------------------------------------------------------------------
config = context.config

# Set up Python logging from alembic.ini [loggers] section.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Override sqlalchemy.url with the value from our Settings object.
config.set_main_option("sqlalchemy.url", str(settings.DATABASE_URL))

target_metadata = Base.metadata


# ---------------------------------------------------------------------------
# Offline migrations (generate SQL without a live DB connection)
# ---------------------------------------------------------------------------

def run_migrations_offline() -> None:
    """
    Run migrations in 'offline' mode.

    In this mode Alembic emits SQL to stdout/a file instead of executing
    it against a live database.  Useful for reviewing or auditing changes.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


# ---------------------------------------------------------------------------
# Online migrations (execute against a live DB connection)
# ---------------------------------------------------------------------------

async def run_async_migrations() -> None:
    """
    Create an async engine, then run migrations inside a connection context.
    """
    connectable = create_async_engine(
        str(settings.DATABASE_URL),
        echo=False,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(_run_migrations_sync)

    await connectable.dispose()


def _run_migrations_sync(connection) -> None:  # type: ignore[no-untyped-def]
    """Configure the Alembic context and run pending migrations synchronously."""
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Entry point for online mode — runs the async coroutine via asyncio."""
    asyncio.run(run_async_migrations())


# ---------------------------------------------------------------------------
# Dispatch
# ---------------------------------------------------------------------------

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

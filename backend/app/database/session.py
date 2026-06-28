"""
Async SQLAlchemy engine and session factory.

The engine is created once at module import time.  The session factory
(`AsyncSessionLocal`) produces one `AsyncSession` per request via the
`get_db` dependency injector.
"""

import logging

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------
engine = create_async_engine(
    str(settings.DATABASE_URL),
    echo=settings.DEBUG,          # Log SQL statements when DEBUG=True
    pool_size=5,                  # Min connections kept alive
    max_overflow=15,              # Additional connections allowed (total cap = 20)
    pool_recycle=3600,            # Recycle connections older than 1 hour
    pool_pre_ping=True,           # Verify connection liveness before checkout
)

# ---------------------------------------------------------------------------
# Session factory
# ---------------------------------------------------------------------------
AsyncSessionLocal: async_sessionmaker[AsyncSession] = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,       # Prevent lazy-load errors after commit
    autoflush=False,
    autocommit=False,
)

"""
Database session dependency injector.

Provides one AsyncSession per request via FastAPI's dependency injection system.
The session is committed on success and rolled back on any exception.

Usage::

    from app.dependencies.database import get_db

    @router.get("/items")
    async def list_items(db: AsyncSession = Depends(get_db)):
        ...
"""

import logging
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import AsyncSessionLocal

logger = logging.getLogger(__name__)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Yield a database session scoped to a single HTTP request.

    - Commits automatically on successful handler completion.
    - Rolls back and re-raises on any exception to maintain consistency.
    - Always closes the session, returning the connection to the pool.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

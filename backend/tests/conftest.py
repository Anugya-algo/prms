"""
Pytest fixtures shared across the entire test suite.

Strategy
--------
- All DB-touching tests use an in-memory SQLite database via aiosqlite so
  they run without a real PostgreSQL instance.
- The HTTP-layer tests use FastAPI's TestClient via httpx with the DB
  overridden to use the same in-memory engine.
- Heavy fixtures (engine, tables) are session-scoped; lighter ones
  (db session, client) are function-scoped for isolation.
"""

from __future__ import annotations

import os
from typing import AsyncGenerator
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

# ── Force test settings before any app import ──────────────────────────────
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("SECRET_KEY", "test-secret-key-that-is-at-least-32-chars!!")
os.environ.setdefault("ENVIRONMENT", "development")
os.environ.setdefault("DEBUG", "true")

from app.database.base import Base  # noqa: E402
from app.dependencies.database import get_db  # noqa: E402
from app.main import create_application  # noqa: E402
from app.models import (  # noqa: F401, E402 — registers all tables
    Alert,
    Asset,
    AssetFieldValue,
    AuditLog,
    Document,
    ImportHistory,
    Project,
    ProjectSummary,
    ReportTemplate,
    ResourceField,
    ResourceType,
    Role,
    SheetMapping,
    Template,
    TemplateResourceType,
    User,
)


# ─────────────────────────────────────────────────────────────────────────────
# Engine & table creation  (session-scoped — created once per test run)
# ─────────────────────────────────────────────────────────────────────────────

@pytest_asyncio.fixture(scope="session")
async def engine():
    """SQLite in-memory async engine shared across the session."""
    _engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
        connect_args={"check_same_thread": False},
    )
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield _engine
    await _engine.dispose()


@pytest_asyncio.fixture(scope="session")
def session_factory(engine):
    """Async session factory bound to the test engine."""
    return async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Per-test DB session  (rolled back after each test for isolation)
# ─────────────────────────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def db(engine, session_factory) -> AsyncGenerator[AsyncSession, None]:
    """
    Provide a clean AsyncSession for each test, wrapped in a transaction
    that is rolled back at the end so tests don't pollute each other.
    """
    async with engine.connect() as conn:
        await conn.begin()
        session = AsyncSession(bind=conn, expire_on_commit=False)
        try:
            yield session
        finally:
            await session.close()
            await conn.rollback()


# ─────────────────────────────────────────────────────────────────────────────
# HTTP test client
# ─────────────────────────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def client(db: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """
    AsyncClient with the FastAPI app, DB overridden to the test session.
    """
    app = create_application()

    async def _override_get_db():
        yield db

    app.dependency_overrides[get_db] = _override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac


# ─────────────────────────────────────────────────────────────────────────────
# Domain object factories
# ─────────────────────────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def test_role(db: AsyncSession) -> Role:
    role = Role(name="manager", description="Project manager role")
    db.add(role)
    await db.flush()
    await db.refresh(role)
    return role


@pytest_asyncio.fixture
async def test_user(db: AsyncSession, test_role: Role) -> User:
    from app.core.security import hash_password

    user = User(
        email="owner@example.com",
        full_name="Project Owner",
        hashed_password=hash_password("password123"),
        is_active=True,
        is_superuser=False,
        role_id=test_role.id,
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user


@pytest_asyncio.fixture
async def superuser(db: AsyncSession) -> User:
    from app.core.security import hash_password

    user = User(
        email="admin@example.com",
        full_name="Admin User",
        hashed_password=hash_password("adminpass123"),
        is_active=True,
        is_superuser=True,
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user


@pytest_asyncio.fixture
async def test_project(db: AsyncSession, test_user: User) -> Project:
    project = Project(
        name="Test Project Alpha",
        code="TPA-001",
        description="A test project for unit tests.",
        status="draft",
        owner_id=test_user.id,
    )
    db.add(project)
    await db.flush()
    await db.refresh(project)
    return project


def make_auth_headers(user: User) -> dict[str, str]:
    """Generate a valid Bearer token header for *user*."""
    from app.core.security import create_access_token

    token = create_access_token({
        "sub": user.id,
        "email": user.email,
        "is_superuser": user.is_superuser,
    })
    return {"Authorization": f"Bearer {token}"}

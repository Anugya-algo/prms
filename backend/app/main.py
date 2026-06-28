"""
PRMS Backend — FastAPI application entry point.

This module assembles the application:
  - Configures logging
  - Registers middleware (CORS, exception handlers)
  - Mounts all routers
  - Wires up OpenAPI / Swagger documentation with JWT bearer auth

No business logic lives here.
"""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi

from app.core.config import settings
from app.core.logging import configure_logging
from app.middleware.exception_handler import register_exception_handlers

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Lifespan — startup / shutdown hooks
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifespan context manager.

    Startup:  configure logging → verify DB connectivity.
    Shutdown: dispose the connection pool gracefully.
    """
    configure_logging(settings.LOG_LEVEL, settings.ENVIRONMENT)
    logger.info(
        "Starting %s [env=%s, debug=%s]",
        settings.PROJECT_NAME,
        settings.ENVIRONMENT,
        settings.DEBUG,
    )

    from sqlalchemy import text
    from sqlalchemy.exc import SQLAlchemyError

    from app.database.session import engine

    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        logger.info("Database connection verified.")
    except SQLAlchemyError as exc:
        logger.error("Database is unreachable at startup: %s", exc)
        raise RuntimeError("Cannot connect to the database — aborting startup.") from exc

    yield

    logger.info("Shutting down %s — disposing connection pool.", settings.PROJECT_NAME)
    from app.database.session import engine as _engine
    await _engine.dispose()


# ---------------------------------------------------------------------------
# OpenAPI customisation — adds JWT bearer security scheme
# ---------------------------------------------------------------------------

def _custom_openapi(app: FastAPI):  # type: ignore[no-untyped-def]
    """
    Attach a reusable BearerAuth security scheme to the OpenAPI schema so that
    the Swagger UI "Authorize" button works for all protected endpoints.
    """
    if app.openapi_schema:
        return app.openapi_schema

    schema = get_openapi(
        title=settings.PROJECT_NAME,
        version="0.1.0",
        description=(
            "**PRMS** (Project Resource Management System) REST API.\n\n"
            "Manage projects, resources, allocations, and reporting in one place.\n\n"
            "### Authentication\n"
            "Most endpoints require a valid **Bearer JWT** token.  "
            "Obtain one via `POST /api/v1/auth/token`, then click **Authorize** above "
            "and paste the `access_token` value."
        ),
        routes=app.routes,
    )

    # Register the BearerAuth security scheme.
    schema.setdefault("components", {}).setdefault("securitySchemes", {})
    schema["components"]["securitySchemes"]["BearerAuth"] = {
        "type": "http",
        "scheme": "bearer",
        "bearerFormat": "JWT",
        "description": "Enter the access_token returned by POST /api/v1/auth/token",
    }

    app.openapi_schema = schema
    return schema


# ---------------------------------------------------------------------------
# Application factory
# ---------------------------------------------------------------------------

def create_application() -> FastAPI:
    """Construct and return the configured FastAPI application."""
    _docs_url = "/docs" if settings.ENVIRONMENT != "production" else None
    _redoc_url = "/redoc" if settings.ENVIRONMENT != "production" else None
    _openapi_url = "/openapi.json" if settings.ENVIRONMENT != "production" else None

    application = FastAPI(
        title=settings.PROJECT_NAME,
        version="0.1.0",
        docs_url=_docs_url,
        redoc_url=_redoc_url,
        openapi_url=_openapi_url,
        lifespan=lifespan,
        swagger_ui_parameters={"persistAuthorization": True},
    )

    # ── CORS ─────────────────────────────────────────────────────────────────
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Exception handlers ────────────────────────────────────────────────────
    register_exception_handlers(application)

    # ── Routers ───────────────────────────────────────────────────────────────
    # Health check (no auth, no prefix)
    from app.api.health import router as health_router
    application.include_router(health_router)

    # v1 API — auth + user management
    from app.api.v1.auth import router as auth_router
    from app.api.v1.projects import router as projects_router
    from app.api.v1.roles import router as roles_router
    from app.api.v1.users import router as users_router

    application.include_router(auth_router, prefix=settings.API_V1_STR)
    application.include_router(users_router, prefix=settings.API_V1_STR)
    application.include_router(roles_router, prefix=settings.API_V1_STR)
    application.include_router(projects_router, prefix=settings.API_V1_STR)

    # ── Custom OpenAPI schema (JWT bearer scheme) ─────────────────────────────
    application.openapi = lambda: _custom_openapi(application)  # type: ignore[method-assign]

    return application


# ---------------------------------------------------------------------------
# Application instance — referenced by uvicorn: app.main:app
# ---------------------------------------------------------------------------
app: FastAPI = create_application()

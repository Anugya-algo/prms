"""
Health check router.

GET /health — returns application and database connectivity status.
Does NOT require authentication so that load balancers can probe freely.
"""

import logging

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import settings
from app.database.session import AsyncSessionLocal
from app.schemas.common import HealthResponse

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Health"])

APP_VERSION = "0.1.0"


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health check",
    description=(
        "Returns the operational status of the API and its database connection. "
        "Returns 200 when healthy, 503 when the database is unreachable."
    ),
)
async def health_check() -> JSONResponse:
    """
    Lightweight health probe.

    Executes `SELECT 1` against the database to confirm connectivity.
    """
    db_status = "connected"
    http_status = status.HTTP_200_OK

    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        logger.error("Health check — database unreachable: %s", exc)
        db_status = "disconnected"
        http_status = status.HTTP_503_SERVICE_UNAVAILABLE

    payload = HealthResponse(
        status="healthy" if db_status == "connected" else "unhealthy",
        version=APP_VERSION,
        environment=settings.ENVIRONMENT,
        database=db_status,
    )

    return JSONResponse(
        content=payload.model_dump(),
        status_code=http_status,
    )

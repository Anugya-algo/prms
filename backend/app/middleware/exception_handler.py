"""
Global exception handlers registered with the FastAPI application.

All unhandled exceptions are caught here and converted to a uniform JSON
error envelope so that API consumers never receive a raw HTML 500 page or
an unstructured error body.

Response shape:
    {
        "detail": "<message>" | [<pydantic-error>, ...],
        "status_code": <http-status-code>
    }

In DEBUG mode, 500 responses additionally include a "traceback" field.
"""

import logging
import traceback

from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.config import settings

logger = logging.getLogger(__name__)


async def http_exception_handler(
    request: Request,
    exc: StarletteHTTPException,
) -> JSONResponse:
    """Handle FastAPI / Starlette HTTPException instances."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": exc.detail,
            "status_code": exc.status_code,
        },
    )


async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    """Handle Pydantic v2 RequestValidationError (422 Unprocessable Entity)."""
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": exc.errors(),
            "status_code": status.HTTP_422_UNPROCESSABLE_ENTITY,
        },
    )


async def unhandled_exception_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    """
    Catch-all handler for any exception not handled by more specific handlers.

    Logs the error at ERROR level (with method + path for traceability),
    then returns a sanitised 500 response.  The traceback is only included
    when DEBUG=True to avoid leaking implementation details in production.
    """
    logger.error(
        "Unhandled exception on %s %s: %s",
        request.method,
        request.url.path,
        exc,
        exc_info=True,
    )

    content: dict = {
        "detail": "Internal server error",
        "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
    }

    if settings.DEBUG:
        content["traceback"] = traceback.format_exc()

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=content,
    )


def register_exception_handlers(app) -> None:  # type: ignore[no-untyped-def]
    """
    Register all global exception handlers onto the FastAPI application instance.

    Call this once during application startup in main.py.
    """
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)

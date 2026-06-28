"""
Shared Pydantic response schemas used across multiple routers.
"""

from typing import Any

from pydantic import BaseModel


class ErrorResponse(BaseModel):
    """Standard error response envelope."""

    detail: str | list[Any]
    status_code: int


class HealthResponse(BaseModel):
    """Health check response schema."""

    status: str
    version: str
    environment: str
    database: str

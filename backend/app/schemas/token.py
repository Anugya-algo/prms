"""
JWT token request / response schemas.
"""

from pydantic import BaseModel


class Token(BaseModel):
    """Response body returned on successful login or token refresh."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    """Decoded JWT payload (validated internally)."""

    sub: str          # user UUID
    type: str         # "access" | "refresh"
    exp: int


class RefreshTokenRequest(BaseModel):
    """Request body for the token-refresh endpoint."""

    refresh_token: str

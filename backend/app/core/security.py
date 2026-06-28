"""
Security utilities — JWT token lifecycle and password hashing.

This module owns:
  - Password hashing / verification  (bcrypt via passlib)
  - Access token creation / verification
  - Refresh token creation / verification
  - The OAuth2 password-bearer scheme used by FastAPI dependencies

No user-lookup or HTTP-layer logic lives here; those belong in
services/auth.py and dependencies/auth.py respectively.
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Literal

from fastapi import HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

# ---------------------------------------------------------------------------
# Password hashing
# ---------------------------------------------------------------------------

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain_password: str) -> str:
    """Return a bcrypt hash of *plain_password*."""
    return _pwd_context.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Return True if *plain_password* matches *hashed_password*."""
    return _pwd_context.verify(plain_password, hashed_password)


# ---------------------------------------------------------------------------
# OAuth2 scheme — FastAPI dependency marker for bearer token extraction.
# ---------------------------------------------------------------------------

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/auth/token",
    # Make the scheme appear in OpenAPI so Swagger shows the Authorize button.
    scheme_name="BearerAuth",
)

# Optional variant that does NOT auto-raise 401 — used for endpoints that
# accept both authenticated and anonymous requests.
oauth2_scheme_optional = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/auth/token",
    scheme_name="BearerAuth",
    auto_error=False,
)

# ---------------------------------------------------------------------------
# Token helpers
# ---------------------------------------------------------------------------

TokenType = Literal["access", "refresh"]


def _create_token(
    data: dict[str, Any],
    token_type: TokenType,
    expires_delta: timedelta | None = None,
) -> str:
    """
    Internal helper: sign a JWT with *type* claim.

    Args:
        data:          Payload claims (must include "sub").
        token_type:    "access" or "refresh" — stored in the "type" claim.
        expires_delta: Override the default TTL.

    Returns:
        Signed JWT string.
    """
    to_encode = data.copy()
    if expires_delta is None:
        if token_type == "access":
            expires_delta = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        else:
            expires_delta = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    expire = datetime.now(timezone.utc) + expires_delta
    to_encode.update({"exp": expire, "type": token_type})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_access_token(
    data: dict[str, Any],
    expires_delta: timedelta | None = None,
) -> str:
    """
    Create and return a signed JWT access token.

    Args:
        data:          Payload claims — must include ``"sub"`` (user id).
        expires_delta: Custom TTL; falls back to ACCESS_TOKEN_EXPIRE_MINUTES.
    """
    return _create_token(data, "access", expires_delta)


def create_refresh_token(
    data: dict[str, Any],
    expires_delta: timedelta | None = None,
) -> str:
    """
    Create and return a signed JWT refresh token.

    Refresh tokens have a longer TTL and carry ``"type": "refresh"`` so they
    cannot be used directly as access tokens.

    Args:
        data:          Payload claims — must include ``"sub"`` (user id).
        expires_delta: Custom TTL; falls back to REFRESH_TOKEN_EXPIRE_DAYS.
    """
    return _create_token(data, "refresh", expires_delta)


def verify_token(token: str, expected_type: TokenType = "access") -> dict[str, Any]:
    """
    Verify signature, expiry, and token type; return the decoded payload.

    Args:
        token:         Raw JWT string.
        expected_type: ``"access"`` (default) or ``"refresh"``.

    Returns:
        Decoded payload dict.

    Raises:
        HTTPException 401: signature invalid, token expired, or wrong type.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload: dict[str, Any] = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
    except JWTError:
        raise credentials_exception

    if payload.get("type") != expected_type:
        raise credentials_exception

    if payload.get("sub") is None:
        raise credentials_exception

    return payload

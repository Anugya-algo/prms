"""
Authentication service.

Coordinates user lookup, password verification, and token issuance.
This layer is the single place that ties together the CRUD layer and the
security utilities — it contains no HTTP or FastAPI concerns.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import (
    create_access_token,
    create_refresh_token,
    verify_password,
    verify_token,
)
from app.crud.user import get_user, get_user_by_email
from app.models.user import User
from app.schemas.token import Token


async def authenticate_user(
    db: AsyncSession,
    email: str,
    password: str,
) -> User | None:
    """
    Verify *email* + *password* credentials.

    Returns:
        The matching User if credentials are valid, else None.
    """
    user = await get_user_by_email(db, email)
    if user is None:
        return None
    if not user.is_active:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


def issue_tokens(user: User) -> Token:
    """
    Create a fresh access + refresh token pair for *user*.

    The token subject (``"sub"``) is the user's UUID string.
    Extra claims (email, role) are embedded for convenience so that
    lightweight middleware can authorise without a DB round-trip.

    Args:
        user: Authenticated, active User ORM instance.

    Returns:
        Token schema with access_token, refresh_token, token_type.
    """
    claims: dict = {
        "sub": user.id,
        "email": user.email,
        "role": user.role.name if user.role else None,
        "is_superuser": user.is_superuser,
    }
    return Token(
        access_token=create_access_token(claims),
        refresh_token=create_refresh_token({"sub": user.id}),
    )


async def refresh_access_token(
    db: AsyncSession,
    refresh_token: str,
) -> Token:
    """
    Validate *refresh_token* and issue a new token pair.

    Args:
        db:            Database session (needed to re-validate user state).
        refresh_token: Raw JWT refresh token string.

    Returns:
        Fresh Token pair.

    Raises:
        HTTPException 401: token invalid, expired, or user no longer active.
    """
    from fastapi import HTTPException, status

    payload = verify_token(refresh_token, expected_type="refresh")
    user = await get_user(db, payload["sub"])
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return issue_tokens(user)

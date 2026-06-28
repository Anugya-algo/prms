"""
Authentication router  —  /api/v1/auth

Endpoints
---------
POST /auth/token       OAuth2 password flow — returns access + refresh tokens.
POST /auth/refresh     Exchange a refresh token for a new token pair.
POST /auth/logout      Client-side logout hint (stateless — no server state).
GET  /auth/me          Return the currently authenticated user's profile.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.auth import CurrentUser
from app.dependencies.database import get_db
from app.schemas.token import RefreshTokenRequest, Token
from app.schemas.user import UserMe
from app.services.auth import authenticate_user, issue_tokens, refresh_access_token

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/token",
    response_model=Token,
    summary="Login — obtain JWT tokens",
    description=(
        "Authenticate with **email** (as `username`) and **password** using the "
        "OAuth2 password flow.  Returns an access token (short-lived) and a "
        "refresh token (long-lived)."
    ),
)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
) -> Token:
    """
    OAuth2 password grant.

    `username` is the user's email address (OAuth2 spec uses the field name
    "username", but we treat it as an email).
    """
    user = await authenticate_user(db, form_data.username, form_data.password)
    if user is None:
        logger.warning("Failed login attempt for %r", form_data.username)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    logger.info("User %r logged in", user.email)
    return issue_tokens(user)


@router.post(
    "/refresh",
    response_model=Token,
    summary="Refresh — exchange refresh token for a new token pair",
    description=(
        "Submit a valid refresh token to receive a fresh access token and "
        "refresh token.  The old refresh token is invalidated on the client side."
    ),
)
async def refresh(
    body: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db),
) -> Token:
    return await refresh_access_token(db, body.refresh_token)


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Logout — invalidate session on client",
    description=(
        "Stateless logout — the server does not maintain a token blocklist. "
        "The client must discard its stored tokens on receipt of this response."
    ),
)
async def logout(current_user: CurrentUser) -> None:
    """
    Signal intent to log out.

    Because JWTs are stateless, the server cannot truly invalidate them.
    Discard the tokens on the client side.  Implement a token blocklist
    (e.g. Redis) in the auth service if server-side revocation is required.
    """
    logger.info("User %r logged out", current_user.email)


@router.get(
    "/me",
    response_model=UserMe,
    summary="Current user — return the authenticated user's profile",
)
async def me(current_user: CurrentUser) -> UserMe:
    """Return the full profile of the currently authenticated user."""
    return current_user  # type: ignore[return-value]

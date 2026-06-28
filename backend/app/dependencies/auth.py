"""
Authentication and authorisation dependency injectors.

Public API
----------
get_current_user        — resolves the bearer token to a live User row.
get_current_active_user — same + rejects inactive accounts.
get_current_superuser   — same + rejects non-superusers.
require_roles(*names)   — factory that returns a dependency enforcing ≥1 role.

Usage::

    from app.dependencies.auth import (
        get_current_active_user,
        get_current_superuser,
        require_roles,
    )

    # Any authenticated, active user:
    @router.get("/me")
    async def me(user = Depends(get_current_active_user)):
        ...

    # Superusers only:
    @router.delete("/users/{id}")
    async def delete(user = Depends(get_current_superuser)):
        ...

    # Role-based guard (admin or manager):
    @router.post("/projects")
    async def create(user = Depends(require_roles("admin", "manager"))):
        ...
"""

from typing import Annotated

from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import oauth2_scheme, verify_token
from app.crud.user import get_user
from app.dependencies.database import get_db
from app.models.user import User


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    """
    Resolve the bearer token to a User row.

    Raises:
        HTTPException 401: token invalid, expired, or user not found.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    payload = verify_token(token, expected_type="access")
    user_id: str | None = payload.get("sub")
    if not user_id:
        raise credentials_exception

    user = await get_user(db, user_id)
    if user is None:
        raise credentials_exception
    return user


async def get_current_active_user(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """
    Extends get_current_user — rejects deactivated accounts.

    Raises:
        HTTPException 403: account is inactive.
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive account",
        )
    return current_user


async def get_current_superuser(
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> User:
    """
    Extends get_current_active_user — restricts to superusers only.

    Raises:
        HTTPException 403: not a superuser.
    """
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Superuser privileges required",
        )
    return current_user


def require_roles(*role_names: str):
    """
    Dependency factory — returns a FastAPI dependency that allows only users
    whose role name is in *role_names* (or superusers, who bypass all checks).

    Args:
        *role_names: One or more allowed role name strings.

    Returns:
        A FastAPI-compatible async dependency function.

    Example::

        @router.post("/projects", dependencies=[Depends(require_roles("admin", "manager"))])
        async def create_project(...):
            ...
    """

    async def _check(
        current_user: Annotated[User, Depends(get_current_active_user)],
    ) -> User:
        # Superusers bypass role checks.
        if current_user.is_superuser:
            return current_user
        user_role = current_user.role.name if current_user.role else None
        if user_role not in role_names:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"One of these roles is required: {', '.join(role_names)}",
            )
        return current_user

    return _check


# ---------------------------------------------------------------------------
# Convenience type aliases for use in route signatures
# ---------------------------------------------------------------------------

CurrentUser = Annotated[User, Depends(get_current_active_user)]
SuperUser = Annotated[User, Depends(get_current_superuser)]

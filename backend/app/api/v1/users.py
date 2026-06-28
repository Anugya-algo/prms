"""
Users router  —  /api/v1/users

Endpoints
---------
GET    /users              List users  (superuser only)
POST   /users              Create user (superuser only)
GET    /users/{id}         Get user by id (own profile or superuser)
PATCH  /users/{id}         Update user   (own profile or superuser)
DELETE /users/{id}         Delete user   (superuser only)
PATCH  /users/{id}/password Change password (own profile or superuser)
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password, verify_password
from app.crud.user import (
    create_user,
    delete_user,
    get_user,
    get_user_by_email,
    get_users,
    update_password,
    update_user,
)
from app.dependencies.auth import CurrentUser, SuperUser, get_current_active_user
from app.dependencies.database import get_db
from app.models.user import User
from app.schemas.user import PasswordChange, UserCreate, UserRead, UserUpdate

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/users", tags=["Users"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _assert_can_access(current_user: User, target_id: str) -> None:
    """Raise 403 unless *current_user* is the target or a superuser."""
    if not current_user.is_superuser and current_user.id != target_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )


async def _get_user_or_404(db: AsyncSession, user_id: str) -> User:
    user = await get_user(db, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {user_id!r} not found",
        )
    return user


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get(
    "",
    response_model=list[UserRead],
    summary="List all users",
    description="Returns a paginated list of all users.  **Superuser only.**",
)
async def list_users(
    skip: int = 0,
    limit: int = 100,
    _current_user: SuperUser = None,  # type: ignore[assignment]
    db: AsyncSession = Depends(get_db),
) -> list[UserRead]:
    return await get_users(db, skip=skip, limit=limit)  # type: ignore[return-value]


@router.post(
    "",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new user",
    description="Create a new user account.  **Superuser only.**",
)
async def create_user_endpoint(
    payload: UserCreate,
    _current_user: SuperUser = None,  # type: ignore[assignment]
    db: AsyncSession = Depends(get_db),
) -> UserRead:
    existing = await get_user_by_email(db, payload.email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email already exists",
        )
    hashed = hash_password(payload.password)
    user = await create_user(db, payload, hashed)
    return user  # type: ignore[return-value]


@router.get(
    "/{user_id}",
    response_model=UserRead,
    summary="Get a user by id",
    description="Superusers may fetch any user; regular users may only fetch their own profile.",
)
async def get_user_endpoint(
    user_id: str,
    current_user: CurrentUser = None,  # type: ignore[assignment]
    db: AsyncSession = Depends(get_db),
) -> UserRead:
    _assert_can_access(current_user, user_id)
    return await _get_user_or_404(db, user_id)  # type: ignore[return-value]


@router.patch(
    "/{user_id}",
    response_model=UserRead,
    summary="Update a user",
    description="Partial update.  Superusers may update any user; others may only update themselves.",
)
async def update_user_endpoint(
    user_id: str,
    payload: UserUpdate,
    current_user: CurrentUser = None,  # type: ignore[assignment]
    db: AsyncSession = Depends(get_db),
) -> UserRead:
    _assert_can_access(current_user, user_id)
    # Non-superusers cannot elevate their own privileges.
    if not current_user.is_superuser:
        payload.is_superuser = None
        payload.is_active = None
        payload.role_id = None

    user = await _get_user_or_404(db, user_id)
    # Guard against email conflicts.
    if payload.email and payload.email.lower() != user.email:
        conflict = await get_user_by_email(db, payload.email)
        if conflict:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already in use by another account",
            )
    return await update_user(db, user, payload)  # type: ignore[return-value]


@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a user",
    description="Hard-delete a user account.  **Superuser only.**",
)
async def delete_user_endpoint(
    user_id: str,
    _current_user: SuperUser = None,  # type: ignore[assignment]
    db: AsyncSession = Depends(get_db),
) -> None:
    user = await _get_user_or_404(db, user_id)
    await delete_user(db, user)


@router.patch(
    "/{user_id}/password",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Change password",
    description=(
        "Update the user's password.  "
        "Regular users must supply their current password; superusers can skip it."
    ),
)
async def change_password(
    user_id: str,
    payload: PasswordChange,
    current_user: CurrentUser = None,  # type: ignore[assignment]
    db: AsyncSession = Depends(get_db),
) -> None:
    _assert_can_access(current_user, user_id)
    user = await _get_user_or_404(db, user_id)

    # Superusers can bypass the current-password check.
    if not current_user.is_superuser:
        if not verify_password(payload.current_password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is incorrect",
            )

    await update_password(db, user, hash_password(payload.new_password))

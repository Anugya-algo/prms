"""
User CRUD operations.

All functions accept an AsyncSession and return ORM objects or None.
Password hashing is NOT done here — pass in an already-hashed password.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate


async def get_user(db: AsyncSession, user_id: str) -> User | None:
    """Return a User (with role eagerly loaded) by primary key."""
    result = await db.execute(
        select(User)
        .options(selectinload(User.role))
        .where(User.id == user_id)
    )
    return result.scalar_one_or_none()


async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    """Return a User (with role eagerly loaded) by email address."""
    result = await db.execute(
        select(User)
        .options(selectinload(User.role))
        .where(User.email == email.lower())
    )
    return result.scalar_one_or_none()


async def get_users(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 100,
) -> list[User]:
    """Return a paginated list of users with roles eagerly loaded."""
    result = await db.execute(
        select(User)
        .options(selectinload(User.role))
        .order_by(User.full_name)
        .offset(skip)
        .limit(limit)
    )
    return list(result.scalars().all())


async def create_user(
    db: AsyncSession,
    payload: UserCreate,
    hashed_password: str,
) -> User:
    """
    Persist a new User.

    Args:
        db:              Database session.
        payload:         Validated UserCreate schema.
        hashed_password: Pre-hashed password (plain text must be hashed
                         by the caller before reaching this function).
    """
    user = User(
        email=payload.email.lower(),
        full_name=payload.full_name,
        hashed_password=hashed_password,
        is_active=payload.is_active,
        is_superuser=payload.is_superuser,
        role_id=payload.role_id,
    )
    db.add(user)
    await db.flush()
    await db.refresh(user, attribute_names=["role"])
    return user


async def update_user(
    db: AsyncSession,
    user: User,
    payload: UserUpdate,
) -> User:
    """Apply *payload* fields (excluding unset) to *user* and flush."""
    update_data = payload.model_dump(exclude_unset=True)
    # Normalise email to lower-case if provided.
    if "email" in update_data and update_data["email"]:
        update_data["email"] = update_data["email"].lower()
    for field, value in update_data.items():
        setattr(user, field, value)
    await db.flush()
    await db.refresh(user, attribute_names=["role"])
    return user


async def update_password(
    db: AsyncSession,
    user: User,
    hashed_password: str,
) -> User:
    """Replace the user's hashed password and flush."""
    user.hashed_password = hashed_password
    await db.flush()
    return user


async def delete_user(db: AsyncSession, user: User) -> None:
    """Hard-delete *user* from the database."""
    await db.delete(user)
    await db.flush()

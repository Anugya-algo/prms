"""
Role CRUD operations.

All functions accept an AsyncSession and return ORM objects or None.
No HTTP logic, no schema validation — that belongs in the service/router layer.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.role import Role
from app.schemas.role import RoleCreate, RoleUpdate


async def get_role(db: AsyncSession, role_id: str) -> Role | None:
    """Return a Role by primary key, or None if not found."""
    result = await db.execute(select(Role).where(Role.id == role_id))
    return result.scalar_one_or_none()


async def get_role_by_name(db: AsyncSession, name: str) -> Role | None:
    """Return a Role by its unique name, or None if not found."""
    result = await db.execute(select(Role).where(Role.name == name))
    return result.scalar_one_or_none()


async def get_roles(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 100,
) -> list[Role]:
    """Return a paginated list of all roles ordered by name."""
    result = await db.execute(
        select(Role).order_by(Role.name).offset(skip).limit(limit)
    )
    return list(result.scalars().all())


async def create_role(db: AsyncSession, payload: RoleCreate) -> Role:
    """Persist a new Role and return it with its generated id."""
    role = Role(
        name=payload.name,
        description=payload.description,
    )
    db.add(role)
    await db.flush()   # populate role.id without a full commit
    await db.refresh(role)
    return role


async def update_role(
    db: AsyncSession,
    role: Role,
    payload: RoleUpdate,
) -> Role:
    """Apply *payload* fields to *role* and persist changes."""
    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(role, field, value)
    await db.flush()
    await db.refresh(role)
    return role


async def delete_role(db: AsyncSession, role: Role) -> None:
    """Hard-delete *role* from the database."""
    await db.delete(role)
    await db.flush()

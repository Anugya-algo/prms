"""
Roles router  —  /api/v1/roles

Endpoints
---------
GET    /roles          List all roles  (any authenticated user)
POST   /roles          Create a role   (superuser only)
GET    /roles/{id}     Get role by id  (any authenticated user)
PATCH  /roles/{id}     Update a role   (superuser only)
DELETE /roles/{id}     Delete a role   (superuser only)
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.role import (
    create_role,
    delete_role,
    get_role,
    get_role_by_name,
    get_roles,
    update_role,
)
from app.dependencies.auth import CurrentUser, SuperUser
from app.dependencies.database import get_db
from app.models.role import Role
from app.schemas.role import RoleCreate, RoleRead, RoleUpdate

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/roles", tags=["Roles"])


async def _get_role_or_404(db: AsyncSession, role_id: str) -> Role:
    role = await get_role(db, role_id)
    if role is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Role {role_id!r} not found",
        )
    return role


@router.get(
    "",
    response_model=list[RoleRead],
    summary="List all roles",
    description="Returns all roles ordered by name.  Requires authentication.",
)
async def list_roles(
    skip: int = 0,
    limit: int = 100,
    _current_user: CurrentUser = None,  # type: ignore[assignment]
    db: AsyncSession = Depends(get_db),
) -> list[RoleRead]:
    return await get_roles(db, skip=skip, limit=limit)  # type: ignore[return-value]


@router.post(
    "",
    response_model=RoleRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a role",
    description="Create a new role.  **Superuser only.**",
)
async def create_role_endpoint(
    payload: RoleCreate,
    _current_user: SuperUser = None,  # type: ignore[assignment]
    db: AsyncSession = Depends(get_db),
) -> RoleRead:
    existing = await get_role_by_name(db, payload.name)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Role {payload.name!r} already exists",
        )
    return await create_role(db, payload)  # type: ignore[return-value]


@router.get(
    "/{role_id}",
    response_model=RoleRead,
    summary="Get a role by id",
    description="Fetch a single role by its UUID.  Requires authentication.",
)
async def get_role_endpoint(
    role_id: str,
    _current_user: CurrentUser = None,  # type: ignore[assignment]
    db: AsyncSession = Depends(get_db),
) -> RoleRead:
    return await _get_role_or_404(db, role_id)  # type: ignore[return-value]


@router.patch(
    "/{role_id}",
    response_model=RoleRead,
    summary="Update a role",
    description="Partial update of a role's name or description.  **Superuser only.**",
)
async def update_role_endpoint(
    role_id: str,
    payload: RoleUpdate,
    _current_user: SuperUser = None,  # type: ignore[assignment]
    db: AsyncSession = Depends(get_db),
) -> RoleRead:
    role = await _get_role_or_404(db, role_id)
    if payload.name and payload.name != role.name:
        conflict = await get_role_by_name(db, payload.name)
        if conflict:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Role {payload.name!r} already exists",
            )
    return await update_role(db, role, payload)  # type: ignore[return-value]


@router.delete(
    "/{role_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a role",
    description=(
        "Hard-delete a role.  Users assigned to this role will have their "
        "`role_id` set to NULL (ON DELETE SET NULL constraint).  **Superuser only.**"
    ),
)
async def delete_role_endpoint(
    role_id: str,
    _current_user: SuperUser = None,  # type: ignore[assignment]
    db: AsyncSession = Depends(get_db),
) -> None:
    role = await _get_role_or_404(db, role_id)
    await delete_role(db, role)

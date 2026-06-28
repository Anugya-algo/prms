"""
Project service — all business logic for the Projects module.

Rules:
  - This layer is the only place that enforces business rules.
  - It calls the CRUD layer for data access.
  - It raises HTTPException when a business rule is violated.
  - Routers ONLY call this layer; they never call CRUD directly.
"""

from __future__ import annotations

import logging
import math

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.project import (
    count_by_status,
    count_projects,
    create_project,
    delete_project,
    get_project,
    get_project_by_code,
    get_project_summary,
    get_recent_projects,
    list_projects,
    update_project,
    upsert_project_summary,
)
from app.models.project import Project, ProjectStatus
from app.models.user import User
from app.schemas.project import (
    DashboardStats,
    ProjectCreate,
    ProjectFilters,
    ProjectListItem,
    ProjectPage,
    ProjectRead,
    ProjectSummaryRead,
    ProjectUpdate,
    StatusBreakdown,
)

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────────────────────

async def _fetch_or_404(db: AsyncSession, project_id: str) -> Project:
    project = await get_project(db, project_id)
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{project_id}' not found.",
        )
    return project


def _assert_owner_or_superuser(project: Project, current_user: User) -> None:
    """Raise 403 unless the caller owns the project or is a superuser."""
    if not current_user.is_superuser and project.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to modify this project.",
        )


# ─────────────────────────────────────────────────────────────────────────────
# Business logic
# ─────────────────────────────────────────────────────────────────────────────

async def create_new_project(
    db: AsyncSession,
    payload: ProjectCreate,
    current_user: User,
) -> ProjectRead:
    """
    Create a new project owned by *current_user*.

    Business rules:
      - Project code, if provided, must be unique (case-insensitive).
    """
    if payload.code:
        existing = await get_project_by_code(db, payload.code)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Project code '{payload.code.upper()}' is already in use.",
            )

    project = await create_project(db, payload, owner_id=current_user.id)
    # Initialise an empty summary row so downstream reads never return None.
    await upsert_project_summary(
        db, project.id,
        total_assets=0, total_resources=0,
        total_documents=0, completion_percent=0.0,
    )
    logger.info("Project created: id=%s code=%s by user=%s", project.id, project.code, current_user.id)
    return ProjectRead.model_validate(project)


async def update_existing_project(
    db: AsyncSession,
    project_id: str,
    payload: ProjectUpdate,
    current_user: User,
) -> ProjectRead:
    """
    Update a project.

    Business rules:
      - Only the owner or a superuser may update.
      - New code (if changed) must be unique.
      - Status transitions are not restricted at this layer (add a state-machine
        here when stricter lifecycle enforcement is required).
    """
    project = await _fetch_or_404(db, project_id)
    _assert_owner_or_superuser(project, current_user)

    if payload.code and payload.code.upper() != project.code:
        conflict = await get_project_by_code(db, payload.code)
        if conflict:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Project code '{payload.code.upper()}' is already in use.",
            )

    project = await update_project(db, project, payload)
    logger.info("Project updated: id=%s by user=%s", project.id, current_user.id)
    return ProjectRead.model_validate(project)


async def delete_existing_project(
    db: AsyncSession,
    project_id: str,
    current_user: User,
) -> None:
    """
    Delete a project and all its cascaded children.

    Business rules:
      - Only the owner or a superuser may delete.
      - Active projects can be deleted (no status guard at service layer;
        add one here if "active" projects should require archival first).
    """
    project = await _fetch_or_404(db, project_id)
    _assert_owner_or_superuser(project, current_user)
    await delete_project(db, project)
    logger.info("Project deleted: id=%s by user=%s", project_id, current_user.id)


async def get_project_detail(
    db: AsyncSession,
    project_id: str,
    current_user: User,
) -> ProjectRead:
    """
    Fetch a single project.

    Business rules:
      - Any active user may view any project (read-all policy).
        Restrict to owner/superuser here if private projects are needed.
    """
    project = await _fetch_or_404(db, project_id)
    return ProjectRead.model_validate(project)


async def list_projects_paginated(
    db: AsyncSession,
    filters: ProjectFilters,
    current_user: User,
) -> ProjectPage:
    """
    Return a paginated, filtered, searchable list of projects.

    Non-superusers see all projects (read-all policy).  Restrict to
    ``owner_id=current_user.id`` here if per-user isolation is required.
    """
    total = await count_projects(db, filters)
    items = await list_projects(db, filters)
    pages = max(1, math.ceil(total / filters.page_size))

    return ProjectPage(
        items=[ProjectListItem.model_validate(p) for p in items],
        total=total,
        page=filters.page,
        page_size=filters.page_size,
        pages=pages,
    )


async def get_project_summary_detail(
    db: AsyncSession,
    project_id: str,
    current_user: User,
) -> ProjectSummaryRead:
    """
    Return the cached summary metrics for a project.

    Triggers a recalculation if no summary exists yet.
    """
    await _fetch_or_404(db, project_id)  # ensure project exists
    summary = await get_project_summary(db, project_id)
    if summary is None:
        # Recalculate on first access.
        summary = await recalculate_project_summary(db, project_id)
    return ProjectSummaryRead.model_validate(summary)


async def recalculate_project_summary(
    db: AsyncSession,
    project_id: str,
) -> "ProjectSummary":  # type: ignore[name-defined]  # noqa: F821
    """
    Recompute the summary metrics by querying child tables.

    This function is meant to be called:
      - After project creation (sets zeros).
      - After bulk import / asset operations.
      - On-demand via the refresh endpoint.

    Counts are kept simple; extend with real queries as modules are added.
    """
    from sqlalchemy import func, select

    from app.models.asset import Asset
    from app.models.document import Document
    from app.models.resource_type import ResourceType

    from app.database.session import AsyncSessionLocal  # noqa: avoid circular; only used here

    # Asset count
    asset_count_row = await db.execute(
        select(func.count(Asset.id)).where(Asset.project_id == project_id)
    )
    total_assets: int = asset_count_row.scalar_one() or 0

    # Resource type count (proxy for "resource rows")
    rt_count_row = await db.execute(
        select(func.count(ResourceType.id)).where(ResourceType.project_id == project_id)
    )
    total_resources: int = rt_count_row.scalar_one() or 0

    # Document count
    doc_count_row = await db.execute(
        select(func.count(Document.id)).where(Document.project_id == project_id)
    )
    total_documents: int = doc_count_row.scalar_one() or 0

    # Completion: total_assets > 0 → percentage of ACTIVE assets
    if total_assets > 0:
        active_row = await db.execute(
            select(func.count(Asset.id)).where(
                Asset.project_id == project_id,
                Asset.status == "active",
            )
        )
        active_count: int = active_row.scalar_one() or 0
        completion_percent = round((active_count / total_assets) * 100, 2)
    else:
        completion_percent = 0.0

    return await upsert_project_summary(
        db,
        project_id,
        total_assets=total_assets,
        total_resources=total_resources,
        total_documents=total_documents,
        completion_percent=completion_percent,
    )


async def get_dashboard_stats(
    db: AsyncSession,
    current_user: User,
) -> DashboardStats:
    """
    Aggregate statistics across all projects for the dashboard.

    Returns total counts by status and the 5 most recently updated projects.
    """
    by_status_map = await count_by_status(db)
    total = sum(by_status_map.values())

    breakdown = [
        StatusBreakdown(status=ProjectStatus(s), count=c)
        for s, c in by_status_map.items()
    ]

    recent = await get_recent_projects(db, limit=5)

    return DashboardStats(
        total_projects=total,
        by_status=breakdown,
        active_count=by_status_map.get(ProjectStatus.ACTIVE.value, 0),
        draft_count=by_status_map.get(ProjectStatus.DRAFT.value, 0),
        completed_count=by_status_map.get(ProjectStatus.COMPLETED.value, 0),
        archived_count=by_status_map.get(ProjectStatus.ARCHIVED.value, 0),
        on_hold_count=by_status_map.get(ProjectStatus.ON_HOLD.value, 0),
        recent_projects=[ProjectListItem.model_validate(p) for p in recent],
    )

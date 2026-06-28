"""
Project CRUD — pure async SQLAlchemy 2.0 data access.

No business logic, no HTTP concerns, no schema validation.
All functions accept an AsyncSession and return ORM objects.
"""

from __future__ import annotations

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.project import Project, ProjectStatus
from app.models.project_summary import ProjectSummary
from app.schemas.project import ProjectCreate, ProjectFilters, ProjectSortField, ProjectUpdate, SortOrder


# ─────────────────────────────────────────────────────────────────────────────
# Read helpers
# ─────────────────────────────────────────────────────────────────────────────

def _base_query(with_owner: bool = False):
    """Return a SELECT statement, optionally eager-loading the owner."""
    q = select(Project)
    if with_owner:
        q = q.options(selectinload(Project.owner))
    return q


def _apply_filters(q, filters: ProjectFilters):
    """
    Mutate *q* by appending WHERE clauses derived from *filters*.
    Returns the modified query.
    """
    if filters.search:
        term = f"%{filters.search.lower()}%"
        q = q.where(
            or_(
                func.lower(Project.name).like(term),
                func.lower(func.coalesce(Project.code, "")).like(term),
                func.lower(func.coalesce(Project.description, "")).like(term),
            )
        )
    if filters.status is not None:
        q = q.where(Project.status == filters.status)
    if filters.owner_id is not None:
        q = q.where(Project.owner_id == filters.owner_id)
    if filters.template_id is not None:
        q = q.where(Project.template_id == filters.template_id)
    if filters.start_date_from is not None:
        q = q.where(Project.start_date >= filters.start_date_from)
    if filters.start_date_to is not None:
        q = q.where(Project.start_date <= filters.start_date_to)
    if filters.end_date_from is not None:
        q = q.where(Project.end_date >= filters.end_date_from)
    if filters.end_date_to is not None:
        q = q.where(Project.end_date <= filters.end_date_to)
    return q


def _apply_sort(q, sort_by: ProjectSortField, sort_order: SortOrder):
    """Append ORDER BY clause."""
    col = getattr(Project, sort_by.value)
    order_col = col.desc() if sort_order == SortOrder.DESC else col.asc()
    return q.order_by(order_col)


# ─────────────────────────────────────────────────────────────────────────────
# CRUD functions
# ─────────────────────────────────────────────────────────────────────────────

async def get_project(db: AsyncSession, project_id: str) -> Project | None:
    """Return a single Project with owner eagerly loaded, or None."""
    result = await db.execute(
        _base_query(with_owner=True).where(Project.id == project_id)
    )
    return result.scalar_one_or_none()


async def get_project_by_code(db: AsyncSession, code: str) -> Project | None:
    """Return a Project by its unique code, or None."""
    result = await db.execute(
        select(Project).where(Project.code == code.upper())
    )
    return result.scalar_one_or_none()


async def count_projects(db: AsyncSession, filters: ProjectFilters) -> int:
    """Return the total count of projects matching *filters*."""
    q = select(func.count()).select_from(Project)
    q = _apply_filters(q, filters)
    result = await db.execute(q)
    return result.scalar_one()


async def list_projects(
    db: AsyncSession,
    filters: ProjectFilters,
) -> list[Project]:
    """Return a filtered, sorted, paginated list of Projects."""
    q = _base_query(with_owner=False)
    q = _apply_filters(q, filters)
    q = _apply_sort(q, filters.sort_by, filters.sort_order)
    q = q.offset(filters.offset).limit(filters.page_size)
    result = await db.execute(q)
    return list(result.scalars().all())


async def create_project(
    db: AsyncSession,
    payload: ProjectCreate,
    owner_id: str,
) -> Project:
    """Persist a new Project and return it with owner loaded."""
    project = Project(
        name=payload.name,
        code=payload.code.upper() if payload.code else None,
        description=payload.description,
        status=payload.status,
        start_date=payload.start_date,
        end_date=payload.end_date,
        owner_id=owner_id,
        template_id=payload.template_id,
    )
    db.add(project)
    await db.flush()
    await db.refresh(project, attribute_names=["owner"])
    return project


async def update_project(
    db: AsyncSession,
    project: Project,
    payload: ProjectUpdate,
) -> Project:
    """Apply *payload* fields (exclude_unset) to *project* and flush."""
    data = payload.model_dump(exclude_unset=True)
    if "code" in data and data["code"]:
        data["code"] = data["code"].upper()
    for field, value in data.items():
        setattr(project, field, value)
    await db.flush()
    await db.refresh(project, attribute_names=["owner"])
    return project


async def delete_project(db: AsyncSession, project: Project) -> None:
    """Hard-delete *project* (cascades to all child rows via FK constraints)."""
    await db.delete(project)
    await db.flush()


# ─────────────────────────────────────────────────────────────────────────────
# Project summary
# ─────────────────────────────────────────────────────────────────────────────

async def get_project_summary(
    db: AsyncSession,
    project_id: str,
) -> ProjectSummary | None:
    """Return the ProjectSummary for *project_id*, or None."""
    result = await db.execute(
        select(ProjectSummary).where(ProjectSummary.project_id == project_id)
    )
    return result.scalar_one_or_none()


async def upsert_project_summary(
    db: AsyncSession,
    project_id: str,
    total_assets: int,
    total_resources: int,
    total_documents: int,
    completion_percent: float,
) -> ProjectSummary:
    """
    Create or update the ProjectSummary for *project_id*.

    Uses INSERT … ON CONFLICT logic via Python-level get-or-create
    to stay ORM-agnostic.
    """
    from datetime import datetime, timezone

    summary = await get_project_summary(db, project_id)
    if summary is None:
        summary = ProjectSummary(
            project_id=project_id,
            total_assets=total_assets,
            total_resources=total_resources,
            total_documents=total_documents,
            completion_percent=completion_percent,
            last_calculated_at=datetime.now(timezone.utc),
        )
        db.add(summary)
    else:
        summary.total_assets = total_assets
        summary.total_resources = total_resources
        summary.total_documents = total_documents
        summary.completion_percent = completion_percent
        summary.last_calculated_at = datetime.now(timezone.utc)
    await db.flush()
    await db.refresh(summary)
    return summary


# ─────────────────────────────────────────────────────────────────────────────
# Dashboard aggregate queries
# ─────────────────────────────────────────────────────────────────────────────

async def count_by_status(db: AsyncSession) -> dict[str, int]:
    """Return a {status_value: count} mapping across all projects."""
    rows = await db.execute(
        select(Project.status, func.count(Project.id).label("cnt"))
        .group_by(Project.status)
    )
    return {str(row.status.value): row.cnt for row in rows}


async def get_recent_projects(
    db: AsyncSession,
    limit: int = 5,
) -> list[Project]:
    """Return the *limit* most recently updated projects."""
    result = await db.execute(
        select(Project).order_by(Project.updated_at.desc()).limit(limit)
    )
    return list(result.scalars().all())

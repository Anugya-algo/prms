"""
Projects router  —  /api/v1/projects

Endpoints
---------
GET    /projects              Paginated list with filtering & search
GET    /projects/stats        Dashboard aggregate statistics
GET    /projects/{id}         Get single project
POST   /projects              Create project
PATCH  /projects/{id}         Update project
DELETE /projects/{id}         Delete project
GET    /projects/{id}/summary Cached metrics summary
POST   /projects/{id}/summary/refresh  Recalculate summary on-demand

Design rule: routers contain ZERO business logic.
Every route body is a thin wrapper that calls the service layer.
"""

import logging

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.auth import CurrentUser
from app.dependencies.database import get_db
from app.schemas.project import (
    DashboardStats,
    ProjectCreate,
    ProjectFilters,
    ProjectPage,
    ProjectRead,
    ProjectSortField,
    ProjectSummaryRead,
    ProjectUpdate,
    SortOrder,
)
from app.models.project import ProjectStatus
from app.services.project import (
    create_new_project,
    delete_existing_project,
    get_dashboard_stats,
    get_project_detail,
    get_project_summary_detail,
    list_projects_paginated,
    recalculate_project_summary,
    update_existing_project,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/projects", tags=["Projects"])


# ─────────────────────────────────────────────────────────────────────────────
# Routes
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/stats",
    response_model=DashboardStats,
    summary="Dashboard statistics",
    description=(
        "Returns aggregate project counts by status and the 5 most recently "
        "updated projects.  Useful for dashboard widgets."
    ),
)
async def dashboard_stats(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> DashboardStats:
    return await get_dashboard_stats(db, current_user)


@router.get(
    "",
    response_model=ProjectPage,
    summary="List projects",
    description=(
        "Returns a paginated, filterable, searchable list of projects.  "
        "Use `search` for free-text search across name, code, and description.  "
        "Combine with `status`, `owner_id`, date range filters, and custom sorting."
    ),
)
async def list_projects_endpoint(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    # Search & filter
    search: str | None = Query(None, max_length=200, description="Search across name, code, description"),
    filter_status: ProjectStatus | None = Query(None, alias="status", description="Filter by status"),
    owner_id: str | None = Query(None, description="Filter by owner UUID"),
    template_id: str | None = Query(None, description="Filter by template UUID"),
    start_date_from: str | None = Query(None, description="start_date ≥ YYYY-MM-DD"),
    start_date_to: str | None = Query(None, description="start_date ≤ YYYY-MM-DD"),
    end_date_from: str | None = Query(None, description="end_date ≥ YYYY-MM-DD"),
    end_date_to: str | None = Query(None, description="end_date ≤ YYYY-MM-DD"),
    # Pagination
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    page_size: int = Query(20, ge=1, le=200, description="Items per page"),
    # Sorting
    sort_by: ProjectSortField = Query(ProjectSortField.CREATED_AT),
    sort_order: SortOrder = Query(SortOrder.DESC),
) -> ProjectPage:
    from datetime import date

    def _parse_date(s: str | None) -> date | None:
        if s is None:
            return None
        try:
            return date.fromisoformat(s)
        except ValueError:
            from fastapi import HTTPException
            raise HTTPException(status_code=400, detail=f"Invalid date format: '{s}'. Use YYYY-MM-DD.")

    filters = ProjectFilters(
        search=search,
        status=filter_status,
        owner_id=owner_id,
        template_id=template_id,
        start_date_from=_parse_date(start_date_from),
        start_date_to=_parse_date(start_date_to),
        end_date_from=_parse_date(end_date_from),
        end_date_to=_parse_date(end_date_to),
        page=page,
        page_size=page_size,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    return await list_projects_paginated(db, filters, current_user)


@router.post(
    "",
    response_model=ProjectRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a project",
    description="Create a new project. The authenticated user becomes the project owner.",
)
async def create_project_endpoint(
    payload: ProjectCreate,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> ProjectRead:
    return await create_new_project(db, payload, current_user)


@router.get(
    "/{project_id}",
    response_model=ProjectRead,
    summary="Get a project",
    description="Fetch a single project by its UUID.",
)
async def get_project_endpoint(
    project_id: str,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> ProjectRead:
    return await get_project_detail(db, project_id, current_user)


@router.patch(
    "/{project_id}",
    response_model=ProjectRead,
    summary="Update a project",
    description=(
        "Partial update.  Only the project owner or a superuser may update.  "
        "Supply only the fields you want to change."
    ),
)
async def update_project_endpoint(
    project_id: str,
    payload: ProjectUpdate,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> ProjectRead:
    return await update_existing_project(db, project_id, payload, current_user)


@router.delete(
    "/{project_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a project",
    description=(
        "Permanently delete a project and all its associated data "
        "(assets, documents, alerts, audit logs, etc.).  "
        "Only the owner or a superuser may delete."
    ),
)
async def delete_project_endpoint(
    project_id: str,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> None:
    await delete_existing_project(db, project_id, current_user)


@router.get(
    "/{project_id}/summary",
    response_model=ProjectSummaryRead,
    summary="Get project summary",
    description=(
        "Returns cached aggregate metrics (asset count, document count, "
        "completion %).  Triggers a recalculation if no summary exists yet."
    ),
)
async def get_summary_endpoint(
    project_id: str,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> ProjectSummaryRead:
    return await get_project_summary_detail(db, project_id, current_user)


@router.post(
    "/{project_id}/summary/refresh",
    response_model=ProjectSummaryRead,
    summary="Refresh project summary",
    description=(
        "Trigger a live recalculation of the project's summary metrics.  "
        "Use after bulk imports or large data changes."
    ),
)
async def refresh_summary_endpoint(
    project_id: str,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> ProjectSummaryRead:
    from app.services.project import recalculate_project_summary as _recalc
    # Ensure project exists (raises 404 if not)
    from app.services.project import _fetch_or_404
    await _fetch_or_404(db, project_id)
    summary = await _recalc(db, project_id)
    from app.schemas.project import ProjectSummaryRead
    return ProjectSummaryRead.model_validate(summary)

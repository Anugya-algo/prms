"""
Project Pydantic schemas.

Naming convention
-----------------
ProjectBase         — shared fields (validation lives here)
ProjectCreate       — POST /projects request body
ProjectUpdate       — PATCH /projects/{id} request body (all optional)
ProjectRead         — response body for single project
ProjectListItem     — lightweight response for list views (no nested objects)
ProjectPage         — paginated response envelope
ProjectFilters      — query-parameter model for list/search filtering
ProjectSummaryRead  — response body for GET /projects/{id}/summary
DashboardStats      — response body for GET /projects/stats
"""

from __future__ import annotations

import enum
from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.project import ProjectStatus


# ─────────────────────────────────────────────────────────────────────────────
# Enumerations (re-exported so routers only import from schemas)
# ─────────────────────────────────────────────────────────────────────────────

class ProjectSortField(str, enum.Enum):
    NAME = "name"
    CODE = "code"
    STATUS = "status"
    START_DATE = "start_date"
    END_DATE = "end_date"
    CREATED_AT = "created_at"
    UPDATED_AT = "updated_at"


class SortOrder(str, enum.Enum):
    ASC = "asc"
    DESC = "desc"


# ─────────────────────────────────────────────────────────────────────────────
# Core project schemas
# ─────────────────────────────────────────────────────────────────────────────

class ProjectBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, examples=["Bridge Rehabilitation Q1"])
    code: str | None = Field(
        None,
        max_length=50,
        pattern=r"^[A-Z0-9_\-]+$",
        examples=["BRQR-001"],
        description="Uppercase alphanumeric short code, unique across all projects.",
    )
    description: str | None = Field(None, max_length=5000)
    status: ProjectStatus = ProjectStatus.DRAFT
    start_date: date | None = None
    end_date: date | None = None
    template_id: str | None = Field(
        None,
        description="UUID of the template to derive this project from.",
    )

    @model_validator(mode="after")
    def end_after_start(self) -> "ProjectBase":
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValueError("end_date must be on or after start_date")
        return self


class ProjectCreate(ProjectBase):
    """Request body for POST /projects."""
    pass


class ProjectUpdate(BaseModel):
    """Request body for PATCH /projects/{id} — all fields optional."""

    name: str | None = Field(None, min_length=1, max_length=255)
    code: str | None = Field(
        None,
        max_length=50,
        pattern=r"^[A-Z0-9_\-]+$",
    )
    description: str | None = None
    status: ProjectStatus | None = None
    start_date: date | None = None
    end_date: date | None = None
    template_id: str | None = None

    @model_validator(mode="after")
    def end_after_start(self) -> "ProjectUpdate":
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValueError("end_date must be on or after start_date")
        return self


# ─────────────────────────────────────────────────────────────────────────────
# Response schemas
# ─────────────────────────────────────────────────────────────────────────────

class OwnerBrief(BaseModel):
    """Embedded owner info to avoid full UserRead nesting."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    full_name: str
    email: str


class ProjectRead(ProjectBase):
    """Full project response — used for single-project GET."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    owner_id: str
    owner: OwnerBrief
    created_at: datetime
    updated_at: datetime


class ProjectListItem(BaseModel):
    """Lightweight row for list views — avoids loading nested owner."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    code: str | None
    status: ProjectStatus
    owner_id: str
    start_date: date | None
    end_date: date | None
    created_at: datetime
    updated_at: datetime


class ProjectPage(BaseModel):
    """Paginated list response envelope."""

    items: list[ProjectListItem]
    total: int
    page: int
    page_size: int
    pages: int


# ─────────────────────────────────────────────────────────────────────────────
# Query / filter parameters
# ─────────────────────────────────────────────────────────────────────────────

class ProjectFilters(BaseModel):
    """
    Query-parameter model injected via Depends().

    All filters are AND-combined.  Omit a field to skip that filter.
    """

    search: str | None = Field(
        None,
        max_length=200,
        description="Full-text search across project name, code, and description.",
    )
    status: ProjectStatus | None = Field(None, description="Filter by exact status.")
    owner_id: str | None = Field(None, description="Filter by owner UUID.")
    template_id: str | None = Field(None, description="Filter by template UUID.")
    start_date_from: date | None = Field(None, description="start_date ≥ this value.")
    start_date_to: date | None = Field(None, description="start_date ≤ this value.")
    end_date_from: date | None = Field(None, description="end_date ≥ this value.")
    end_date_to: date | None = Field(None, description="end_date ≤ this value.")

    # Pagination
    page: int = Field(1, ge=1, description="1-based page number.")
    page_size: int = Field(20, ge=1, le=200, description="Rows per page (max 200).")

    # Sorting
    sort_by: ProjectSortField = ProjectSortField.CREATED_AT
    sort_order: SortOrder = SortOrder.DESC

    @field_validator("page_size")
    @classmethod
    def cap_page_size(cls, v: int) -> int:
        return min(v, 200)

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size


# ─────────────────────────────────────────────────────────────────────────────
# Project summary
# ─────────────────────────────────────────────────────────────────────────────

class ProjectSummaryRead(BaseModel):
    """Response body for GET /projects/{id}/summary."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    total_assets: int
    total_resources: int
    total_documents: int
    completion_percent: float
    last_calculated_at: datetime | None
    created_at: datetime
    updated_at: datetime


# ─────────────────────────────────────────────────────────────────────────────
# Dashboard statistics
# ─────────────────────────────────────────────────────────────────────────────

class StatusBreakdown(BaseModel):
    status: ProjectStatus
    count: int


class DashboardStats(BaseModel):
    """Response body for GET /projects/stats."""

    total_projects: int
    by_status: list[StatusBreakdown]
    active_count: int
    draft_count: int
    completed_count: int
    archived_count: int
    on_hold_count: int
    recent_projects: list[ProjectListItem]
    """The 5 most recently updated projects."""

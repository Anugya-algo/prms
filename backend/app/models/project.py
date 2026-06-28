"""
Project model.

A Project is the top-level container for all resource, asset, document, and
reporting data.  Every project belongs to an owner (User) and may optionally
be derived from a Template.
"""

from __future__ import annotations

import enum
from typing import TYPE_CHECKING

from sqlalchemy import Date, Enum, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.base import TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.alert import Alert
    from app.models.asset import Asset
    from app.models.audit_log import AuditLog
    from app.models.document import Document
    from app.models.import_history import ImportHistory
    from app.models.project_summary import ProjectSummary
    from app.models.report_template import ReportTemplate
    from app.models.resource_type import ResourceType
    from app.models.template import Template
    from app.models.user import User


class ProjectStatus(str, enum.Enum):
    """Lifecycle states of a project."""

    DRAFT = "draft"
    ACTIVE = "active"
    ON_HOLD = "on_hold"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class Project(UUIDMixin, TimestampMixin, Base):
    """
    Top-level project container.

    Columns
    -------
    name        Human-readable project name.
    code        Short unique identifier used in reports (e.g. "PRMS-001").
    description Long-form description.
    status      Current lifecycle state (draft / active / on_hold / ...).
    start_date  Planned or actual project start date.
    end_date    Planned or actual project end date.
    owner_id    FK → users.id — the user responsible for the project.
    template_id FK → templates.id — optional blueprint the project was created from.
    """

    __tablename__ = "projects"
    __table_args__ = (
        Index("ix_projects_owner_id", "owner_id"),
        Index("ix_projects_template_id", "template_id"),
        Index("ix_projects_status", "status"),
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    code: Mapped[str | None] = mapped_column(String(50), nullable=True, unique=True, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[ProjectStatus] = mapped_column(
        Enum(ProjectStatus, name="project_status"),
        nullable=False,
        default=ProjectStatus.DRAFT,
        index=True,
    )
    start_date: Mapped[Date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[Date | None] = mapped_column(Date, nullable=True)

    owner_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    template_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("templates.id", ondelete="SET NULL"),
        nullable=True,
    )

    # ── Relationships ────────────────────────────────────────────────────────
    owner: Mapped[User] = relationship(
        "User",
        back_populates="projects",
        lazy="select",
    )
    template: Mapped[Template | None] = relationship(
        "Template",
        back_populates="projects",
        lazy="select",
    )
    summary: Mapped[ProjectSummary | None] = relationship(
        "ProjectSummary",
        back_populates="project",
        uselist=False,
        lazy="select",
        cascade="all, delete-orphan",
    )
    resource_types: Mapped[list[ResourceType]] = relationship(
        "ResourceType",
        back_populates="project",
        lazy="select",
        cascade="all, delete-orphan",
    )
    assets: Mapped[list[Asset]] = relationship(
        "Asset",
        back_populates="project",
        lazy="select",
        cascade="all, delete-orphan",
    )
    documents: Mapped[list[Document]] = relationship(
        "Document",
        back_populates="project",
        lazy="select",
        cascade="all, delete-orphan",
    )
    alerts: Mapped[list[Alert]] = relationship(
        "Alert",
        back_populates="project",
        lazy="select",
        cascade="all, delete-orphan",
    )
    audit_logs: Mapped[list[AuditLog]] = relationship(
        "AuditLog",
        back_populates="project",
        lazy="select",
        cascade="all, delete-orphan",
    )
    import_histories: Mapped[list[ImportHistory]] = relationship(
        "ImportHistory",
        back_populates="project",
        lazy="select",
        cascade="all, delete-orphan",
    )
    report_templates: Mapped[list[ReportTemplate]] = relationship(
        "ReportTemplate",
        back_populates="project",
        lazy="select",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Project id={self.id!r} code={self.code!r} status={self.status!r}>"

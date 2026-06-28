"""
ReportTemplate model.

Defines the configuration for a reusable report format within a project.
The template stores the report type, column selection, filters, and layout
settings as a JSON blob so that users can regenerate the same report on
demand without reconfiguring it each time.
"""

from __future__ import annotations

import enum
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Enum, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.base import TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.project import Project


class ReportFormat(str, enum.Enum):
    """Output format produced by the report template."""

    PDF = "pdf"
    EXCEL = "excel"
    CSV = "csv"
    JSON = "json"


class ReportTemplate(UUIDMixin, TimestampMixin, Base):
    """
    Saved report configuration for a project.

    Columns
    -------
    project_id      FK → projects.id.
    name            Unique report name within the project.
    description     Purpose / audience of the report.
    report_format   Target output format (pdf / excel / csv / json).
    is_default      Whether this template is the project's default report.
    is_active       Soft-disable flag.
    config          JSON blob storing column selection, filters, sorting,
                    grouping, and layout settings.
    """

    __tablename__ = "report_templates"
    __table_args__ = (
        UniqueConstraint(
            "project_id",
            "name",
            name="uq_report_templates_project_name",
        ),
        Index("ix_report_templates_project_id", "project_id"),
        Index("ix_report_templates_is_active", "is_active"),
    )

    project_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    report_format: Mapped[ReportFormat] = mapped_column(
        Enum(ReportFormat, name="report_format"),
        nullable=False,
        default=ReportFormat.EXCEL,
    )
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    config: Mapped[str | None] = mapped_column(Text, nullable=True)   # JSON

    # ── Relationships ────────────────────────────────────────────────────────
    project: Mapped[Project] = relationship(
        "Project",
        back_populates="report_templates",
        lazy="select",
    )

    def __repr__(self) -> str:
        return (
            f"<ReportTemplate id={self.id!r} name={self.name!r} "
            f"format={self.report_format!r}>"
        )

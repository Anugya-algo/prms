"""
ProjectSummary model.

Stores pre-computed / cached aggregate metrics for a project so that
dashboards can read them without running expensive queries each time.
A ProjectSummary has a strict one-to-one relationship with its Project.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, Integer, Numeric, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.base import TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.project import Project


class ProjectSummary(UUIDMixin, TimestampMixin, Base):
    """
    Cached aggregate metrics for a project.

    Columns
    -------
    project_id          FK → projects.id (unique — one summary per project).
    total_assets        Count of assets associated with the project.
    total_resources     Count of resource rows across all resource types.
    total_documents     Count of uploaded documents.
    completion_percent  Calculated completion percentage (0.00 – 100.00).
    last_calculated_at  Timestamp of the last recalculation run.
    """

    __tablename__ = "project_summaries"
    __table_args__ = (
        UniqueConstraint("project_id", name="uq_project_summaries_project_id"),
        Index("ix_project_summaries_project_id", "project_id"),
    )

    project_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )

    total_assets: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_resources: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_documents: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    completion_percent: Mapped[float] = mapped_column(
        Numeric(5, 2), nullable=False, default=0.00
    )
    last_calculated_at: Mapped[DateTime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        onupdate=func.now(),
    )

    # ── Relationships ────────────────────────────────────────────────────────
    project: Mapped[Project] = relationship(
        "Project",
        back_populates="summary",
        lazy="select",
    )

    def __repr__(self) -> str:
        return (
            f"<ProjectSummary id={self.id!r} project_id={self.project_id!r} "
            f"completion={self.completion_percent}%>"
        )

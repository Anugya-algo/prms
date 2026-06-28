"""
ResourceType model.

A ResourceType defines a category of resources within a project
(e.g. "Labour", "Equipment", "Materials").  Each ResourceType belongs to
one Project and optionally to a Template via TemplateResourceType.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.base import TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.project import Project
    from app.models.resource_field import ResourceField
    from app.models.sheet_mapping import SheetMapping
    from app.models.template_resource_type import TemplateResourceType


class ResourceType(UUIDMixin, TimestampMixin, Base):
    """
    Category of resource within a project.

    Columns
    -------
    project_id  FK → projects.id  — the owning project.
    name        Name of the resource type (unique within a project).
    description Description / notes.
    color       Optional hex colour code for UI display (e.g. "#3B82F6").
    icon        Optional icon slug for UI display.
    sort_order  Display order relative to other resource types in the project.
    is_active   Soft-disable flag.
    """

    __tablename__ = "resource_types"
    __table_args__ = (
        # Name must be unique within a project.
        UniqueConstraint("project_id", "name", name="uq_resource_types_project_name"),
        Index("ix_resource_types_project_id", "project_id"),
    )

    project_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    color: Mapped[str | None] = mapped_column(String(7), nullable=True)   # "#RRGGBB"
    icon: Mapped[str | None] = mapped_column(String(100), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # ── Relationships ────────────────────────────────────────────────────────
    project: Mapped[Project] = relationship(
        "Project",
        back_populates="resource_types",
        lazy="select",
    )
    resource_fields: Mapped[list[ResourceField]] = relationship(
        "ResourceField",
        back_populates="resource_type",
        lazy="select",
        cascade="all, delete-orphan",
    )
    sheet_mappings: Mapped[list[SheetMapping]] = relationship(
        "SheetMapping",
        back_populates="resource_type",
        lazy="select",
        cascade="all, delete-orphan",
    )
    template_resource_types: Mapped[list[TemplateResourceType]] = relationship(
        "TemplateResourceType",
        back_populates="resource_type",
        lazy="select",
    )

    def __repr__(self) -> str:
        return f"<ResourceType id={self.id!r} name={self.name!r} project_id={self.project_id!r}>"

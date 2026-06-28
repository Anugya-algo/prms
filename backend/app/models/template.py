"""
Template model.

A Template is a reusable project blueprint that defines which resource
types, sheet mappings, and resource fields are expected.  Projects can
be created from a template to inherit its structure.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.base import TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.project import Project
    from app.models.resource_type import ResourceType
    from app.models.template_resource_type import TemplateResourceType


class Template(UUIDMixin, TimestampMixin, Base):
    """
    Project template / blueprint.

    Columns
    -------
    name        Unique template name.
    description Long-form description of the template's purpose.
    is_active   Whether the template is available for new projects.
    version     Semantic version string for template evolution tracking.
    """

    __tablename__ = "templates"
    __table_args__ = (
        UniqueConstraint("name", name="uq_templates_name"),
        Index("ix_templates_is_active", "is_active"),
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    version: Mapped[str] = mapped_column(String(50), nullable=False, default="1.0.0")

    # ── Relationships ────────────────────────────────────────────────────────
    projects: Mapped[list[Project]] = relationship(
        "Project",
        back_populates="template",
        lazy="select",
    )
    template_resource_types: Mapped[list[TemplateResourceType]] = relationship(
        "TemplateResourceType",
        back_populates="template",
        lazy="select",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Template id={self.id!r} name={self.name!r} version={self.version!r}>"

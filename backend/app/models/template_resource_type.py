"""
TemplateResourceType model.

Association / join table that records which ResourceTypes belong to a Template.
Carries extra payload (default_fields, sort_order) beyond the bare FK pair so
it is modelled as an explicit association object rather than a secondary table.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Index, Integer, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.base import TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.resource_type import ResourceType
    from app.models.template import Template


class TemplateResourceType(UUIDMixin, TimestampMixin, Base):
    """
    Many-to-many link between Template and ResourceType.

    Columns
    -------
    template_id      FK → templates.id.
    resource_type_id FK → resource_types.id.
    sort_order       Display order within the template's resource type list.
    """

    __tablename__ = "template_resource_types"
    __table_args__ = (
        UniqueConstraint(
            "template_id",
            "resource_type_id",
            name="uq_template_resource_types",
        ),
        Index("ix_trt_template_id", "template_id"),
        Index("ix_trt_resource_type_id", "resource_type_id"),
    )

    template_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("templates.id", ondelete="CASCADE"),
        nullable=False,
    )
    resource_type_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("resource_types.id", ondelete="CASCADE"),
        nullable=False,
    )
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # ── Relationships ────────────────────────────────────────────────────────
    template: Mapped[Template] = relationship(
        "Template",
        back_populates="template_resource_types",
        lazy="select",
    )
    resource_type: Mapped[ResourceType] = relationship(
        "ResourceType",
        back_populates="template_resource_types",
        lazy="select",
    )

    def __repr__(self) -> str:
        return (
            f"<TemplateResourceType template={self.template_id!r} "
            f"resource_type={self.resource_type_id!r}>"
        )

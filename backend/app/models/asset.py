"""
Asset model.

An Asset is a single resource row within a Project, classified under a
ResourceType.  Its dynamic field values are stored as AssetFieldValue rows.
"""

from __future__ import annotations

import enum
from typing import TYPE_CHECKING

from sqlalchemy import Enum, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.base import TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.asset_field_value import AssetFieldValue
    from app.models.document import Document
    from app.models.project import Project
    from app.models.resource_type import ResourceType


class AssetStatus(str, enum.Enum):
    """Lifecycle / availability status of an asset."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    PENDING = "pending"
    RETIRED = "retired"


class Asset(UUIDMixin, TimestampMixin, Base):
    """
    A single resource row within a project.

    Columns
    -------
    project_id       FK → projects.id.
    resource_type_id FK → resource_types.id.
    name             Display name of the asset.
    code             Optional short reference code (unique within project).
    status           Current lifecycle state.
    notes            Free-form notes.
    external_ref     Optional reference to an external system (e.g. ERP ID).
    """

    __tablename__ = "assets"
    __table_args__ = (
        Index("ix_assets_project_id", "project_id"),
        Index("ix_assets_resource_type_id", "resource_type_id"),
        Index("ix_assets_status", "status"),
        # code uniqueness scoped to a project
        Index("ix_assets_project_code", "project_id", "code", unique=True),
    )

    project_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    resource_type_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("resource_types.id", ondelete="RESTRICT"),
        nullable=False,
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status: Mapped[AssetStatus] = mapped_column(
        Enum(AssetStatus, name="asset_status"),
        nullable=False,
        default=AssetStatus.ACTIVE,
        index=True,
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    external_ref: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)

    # ── Relationships ────────────────────────────────────────────────────────
    project: Mapped[Project] = relationship(
        "Project",
        back_populates="assets",
        lazy="select",
    )
    resource_type: Mapped[ResourceType] = relationship(
        "ResourceType",
        lazy="select",
    )
    field_values: Mapped[list[AssetFieldValue]] = relationship(
        "AssetFieldValue",
        back_populates="asset",
        lazy="select",
        cascade="all, delete-orphan",
    )
    documents: Mapped[list[Document]] = relationship(
        "Document",
        back_populates="asset",
        lazy="select",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Asset id={self.id!r} name={self.name!r} status={self.status!r}>"

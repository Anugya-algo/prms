"""
ResourceField model.

Defines a custom column / field schema for a ResourceType.
Each ResourceField describes one column that every Asset row belonging
to that ResourceType will have (captured via AssetFieldValue).
"""

from __future__ import annotations

import enum
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Enum, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.base import TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.asset_field_value import AssetFieldValue
    from app.models.resource_type import ResourceType


class FieldDataType(str, enum.Enum):
    """Supported data types for a resource field."""

    TEXT = "text"
    INTEGER = "integer"
    DECIMAL = "decimal"
    BOOLEAN = "boolean"
    DATE = "date"
    DATETIME = "datetime"
    SELECT = "select"       # Single choice from a predefined list
    MULTI_SELECT = "multi_select"  # Multiple choices
    URL = "url"
    EMAIL = "email"


class ResourceField(UUIDMixin, TimestampMixin, Base):
    """
    Dynamic column definition for a ResourceType.

    Columns
    -------
    resource_type_id  FK → resource_types.id.
    name              Machine-readable field key (unique within a resource type).
    label             Human-readable column header shown in the UI.
    data_type         Expected value type (text, integer, decimal, …).
    is_required       Whether the field must have a value.
    is_filterable     Whether the UI should expose this field as a filter option.
    default_value     Optional default value stored as a string.
    options           JSON-encoded list of allowed values for SELECT / MULTI_SELECT.
    sort_order        Display order relative to other fields in the same resource type.
    help_text         Short hint displayed below the field in the UI.
    """

    __tablename__ = "resource_fields"
    __table_args__ = (
        # Field name must be unique within a resource type.
        UniqueConstraint(
            "resource_type_id",
            "name",
            name="uq_resource_fields_rt_name",
        ),
        Index("ix_resource_fields_resource_type_id", "resource_type_id"),
    )

    resource_type_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("resource_types.id", ondelete="CASCADE"),
        nullable=False,
    )

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    data_type: Mapped[FieldDataType] = mapped_column(
        Enum(FieldDataType, name="field_data_type"),
        nullable=False,
        default=FieldDataType.TEXT,
    )
    is_required: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_filterable: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    default_value: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    options: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON array
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    help_text: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # ── Relationships ────────────────────────────────────────────────────────
    resource_type: Mapped[ResourceType] = relationship(
        "ResourceType",
        back_populates="resource_fields",
        lazy="select",
    )
    asset_field_values: Mapped[list[AssetFieldValue]] = relationship(
        "AssetFieldValue",
        back_populates="field",
        lazy="select",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return (
            f"<ResourceField id={self.id!r} name={self.name!r} "
            f"data_type={self.data_type!r}>"
        )

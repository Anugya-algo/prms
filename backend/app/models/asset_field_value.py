"""
AssetFieldValue model.

Stores the concrete value of a ResourceField for a specific Asset.
This is the Entity-Attribute-Value (EAV) row that makes the field
schema dynamic without requiring schema migrations per new field.

All values are stored as strings; the service layer casts them to
the correct type using the field's `data_type` metadata.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Index, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.base import TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.asset import Asset
    from app.models.resource_field import ResourceField


class AssetFieldValue(UUIDMixin, TimestampMixin, Base):
    """
    Dynamic field value for an asset (EAV row).

    Columns
    -------
    asset_id    FK → assets.id.
    field_id    FK → resource_fields.id.
    value       Serialised string representation of the field value.
                Null when the field has not been populated for this asset.
    """

    __tablename__ = "asset_field_values"
    __table_args__ = (
        # One value per (asset, field) pair.
        UniqueConstraint("asset_id", "field_id", name="uq_asset_field_values"),
        Index("ix_afv_asset_id", "asset_id"),
        Index("ix_afv_field_id", "field_id"),
    )

    asset_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("assets.id", ondelete="CASCADE"),
        nullable=False,
    )
    field_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("resource_fields.id", ondelete="CASCADE"),
        nullable=False,
    )
    value: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ── Relationships ────────────────────────────────────────────────────────
    asset: Mapped[Asset] = relationship(
        "Asset",
        back_populates="field_values",
        lazy="select",
    )
    field: Mapped[ResourceField] = relationship(
        "ResourceField",
        back_populates="asset_field_values",
        lazy="select",
    )

    def __repr__(self) -> str:
        return (
            f"<AssetFieldValue asset={self.asset_id!r} "
            f"field={self.field_id!r} value={self.value!r}>"
        )

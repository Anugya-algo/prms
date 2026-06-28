"""
SheetMapping model.

Maps a spreadsheet sheet (tab) to a ResourceType within a project.
Used during import to know which sheet's rows correspond to which
resource category.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.base import TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.resource_type import ResourceType


class SheetMapping(UUIDMixin, TimestampMixin, Base):
    """
    Spreadsheet sheet → ResourceType mapping.

    Columns
    -------
    resource_type_id    FK → resource_types.id.
    sheet_name          Exact name of the spreadsheet tab (case-sensitive).
    header_row          Zero-based row index of the header row (default 0).
    data_start_row      Zero-based row index where data begins (default 1).
    is_active           Whether this mapping is currently enabled.
    column_mapping      JSON blob stored as text: {"sheet_col": "field_name", ...}.
                        Kept as a plain string here; cast to JSON in the service layer
                        to avoid a hard dependency on the PostgreSQL JSON type at the
                        model layer.
    """

    __tablename__ = "sheet_mappings"
    __table_args__ = (
        # One sheet name per resource type.
        UniqueConstraint(
            "resource_type_id",
            "sheet_name",
            name="uq_sheet_mappings_rt_sheet",
        ),
        Index("ix_sheet_mappings_resource_type_id", "resource_type_id"),
    )

    resource_type_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("resource_types.id", ondelete="CASCADE"),
        nullable=False,
    )

    sheet_name: Mapped[str] = mapped_column(String(255), nullable=False)
    header_row: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    data_start_row: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    column_mapping: Mapped[str | None] = mapped_column(String(4096), nullable=True)

    # ── Relationships ────────────────────────────────────────────────────────
    resource_type: Mapped[ResourceType] = relationship(
        "ResourceType",
        back_populates="sheet_mappings",
        lazy="select",
    )

    def __repr__(self) -> str:
        return (
            f"<SheetMapping id={self.id!r} sheet_name={self.sheet_name!r} "
            f"resource_type_id={self.resource_type_id!r}>"
        )

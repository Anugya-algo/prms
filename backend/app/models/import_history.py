"""
ImportHistory model.

Tracks every spreadsheet / file import operation performed against a project.
Provides a log of what was imported, by whom, when, and the outcome
(success / partial failure / error).
"""

from __future__ import annotations

import enum
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Enum, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.base import TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.project import Project
    from app.models.user import User


class ImportStatus(str, enum.Enum):
    """Terminal state of an import operation."""

    PENDING = "pending"
    PROCESSING = "processing"
    SUCCESS = "success"
    PARTIAL = "partial"     # Some rows imported, some skipped / errored
    FAILED = "failed"


class ImportHistory(UUIDMixin, TimestampMixin, Base):
    """
    Record of a single file import operation.

    Columns
    -------
    project_id       FK → projects.id.
    imported_by_id   FK → users.id — the user who triggered the import.
    file_name        Original file name of the uploaded file.
    file_size        File size in bytes.
    status           Outcome of the import.
    total_rows       Total data rows found in the file.
    imported_rows    Rows successfully imported.
    skipped_rows     Rows skipped (duplicate / filtered).
    error_rows       Rows that caused an error.
    error_log        Structured log of per-row errors (JSON text).
    notes            Optional free-form notes added by the user or system.
    """

    __tablename__ = "import_histories"
    __table_args__ = (
        Index("ix_import_histories_project_id", "project_id"),
        Index("ix_import_histories_imported_by_id", "imported_by_id"),
        Index("ix_import_histories_status", "status"),
    )

    project_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    imported_by_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    file_name: Mapped[str] = mapped_column(String(512), nullable=False)
    file_size: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    status: Mapped[ImportStatus] = mapped_column(
        Enum(ImportStatus, name="import_status"),
        nullable=False,
        default=ImportStatus.PENDING,
    )
    total_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    imported_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    skipped_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_log: Mapped[str | None] = mapped_column(Text, nullable=True)   # JSON
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ── Relationships ────────────────────────────────────────────────────────
    project: Mapped[Project] = relationship(
        "Project",
        back_populates="import_histories",
        lazy="select",
    )
    imported_by: Mapped[User | None] = relationship(
        "User",
        back_populates="import_histories",
        lazy="select",
    )

    def __repr__(self) -> str:
        return (
            f"<ImportHistory id={self.id!r} file_name={self.file_name!r} "
            f"status={self.status!r}>"
        )

"""
Document model.

Represents a file attachment that can be linked to a Project or to a
specific Asset.  The physical file is stored in an external object store
(e.g. S3); this record holds the metadata and the storage reference key.
"""

from __future__ import annotations

import enum
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Enum, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.base import TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.asset import Asset
    from app.models.project import Project


class DocumentCategory(str, enum.Enum):
    """High-level classification of a document."""

    REPORT = "report"
    CONTRACT = "contract"
    SPECIFICATION = "specification"
    PHOTO = "photo"
    OTHER = "other"


class Document(UUIDMixin, TimestampMixin, Base):
    """
    File attachment metadata.

    Columns
    -------
    project_id      FK → projects.id — every document belongs to a project.
    asset_id        FK → assets.id   — optional: link to a specific asset.
    file_name       Original uploaded file name.
    file_size       File size in bytes.
    mime_type       MIME type (e.g. "application/pdf").
    storage_key     Path / key in the object store (S3 key, GCS blob name, etc.).
    category        Document classification.
    version         Monotonic version counter for the same logical document.
    checksum        SHA-256 hex digest of the file content for integrity checks.
    """

    __tablename__ = "documents"
    __table_args__ = (
        Index("ix_documents_project_id", "project_id"),
        Index("ix_documents_asset_id", "asset_id"),
        Index("ix_documents_category", "category"),
    )

    project_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    asset_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("assets.id", ondelete="CASCADE"),
        nullable=True,
    )

    file_name: Mapped[str] = mapped_column(String(512), nullable=False)
    file_size: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    mime_type: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(1024), nullable=False, unique=True)
    category: Mapped[DocumentCategory] = mapped_column(
        Enum(DocumentCategory, name="document_category"),
        nullable=False,
        default=DocumentCategory.OTHER,
    )
    version: Mapped[int] = mapped_column(BigInteger, nullable=False, default=1)
    checksum: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # ── Relationships ────────────────────────────────────────────────────────
    project: Mapped[Project] = relationship(
        "Project",
        back_populates="documents",
        lazy="select",
    )
    asset: Mapped[Asset | None] = relationship(
        "Asset",
        back_populates="documents",
        lazy="select",
    )

    def __repr__(self) -> str:
        return f"<Document id={self.id!r} file_name={self.file_name!r}>"

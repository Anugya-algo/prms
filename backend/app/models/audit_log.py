"""
AuditLog model.

Immutable append-only record of every significant action performed in the
system.  Rows are never updated or soft-deleted — they form the permanent
audit trail.
"""

from __future__ import annotations

import enum
from typing import TYPE_CHECKING

from sqlalchemy import Enum, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import INET, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.base import TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.project import Project
    from app.models.user import User


class AuditAction(str, enum.Enum):
    """Verb describing what happened."""

    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    LOGIN = "login"
    LOGOUT = "logout"
    EXPORT = "export"
    IMPORT = "import"


class AuditLog(UUIDMixin, TimestampMixin, Base):
    """
    Immutable audit trail entry.

    Columns
    -------
    user_id       FK → users.id  — actor who performed the action (nullable
                  to support system-generated events with no authenticated user).
    project_id    FK → projects.id — optional: the project context.
    action        Verb (create / update / delete / …).
    resource_type Name of the ORM entity type affected (e.g. "Asset").
    resource_id   UUID of the affected row.
    old_values    JSON snapshot of the entity state before the change.
    new_values    JSON snapshot of the entity state after the change.
    ip_address    Originating IP address of the request.
    user_agent    HTTP User-Agent header of the request.
    """

    __tablename__ = "audit_logs"
    __table_args__ = (
        Index("ix_audit_logs_user_id", "user_id"),
        Index("ix_audit_logs_project_id", "project_id"),
        Index("ix_audit_logs_resource_type_id", "resource_type", "resource_id"),
        Index("ix_audit_logs_created_at", "created_at"),
    )

    user_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    project_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=True,
    )

    action: Mapped[AuditAction] = mapped_column(
        Enum(AuditAction, name="audit_action"),
        nullable=False,
    )
    resource_type: Mapped[str] = mapped_column(String(100), nullable=False)
    resource_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    old_values: Mapped[str | None] = mapped_column(Text, nullable=True)   # JSON
    new_values: Mapped[str | None] = mapped_column(Text, nullable=True)   # JSON
    ip_address: Mapped[str | None] = mapped_column(INET, nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(512), nullable=True)

    # ── Relationships ────────────────────────────────────────────────────────
    user: Mapped[User | None] = relationship(
        "User",
        back_populates="audit_logs",
        lazy="select",
    )
    project: Mapped[Project | None] = relationship(
        "Project",
        back_populates="audit_logs",
        lazy="select",
    )

    def __repr__(self) -> str:
        return (
            f"<AuditLog id={self.id!r} action={self.action!r} "
            f"resource_type={self.resource_type!r}>"
        )

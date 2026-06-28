"""
User model.

Represents a system user.  Passwords are stored as bcrypt hashes — the raw
password is never persisted.  Each user belongs to exactly one Role.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.base import TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.alert import Alert
    from app.models.audit_log import AuditLog
    from app.models.import_history import ImportHistory
    from app.models.project import Project
    from app.models.role import Role


class User(UUIDMixin, TimestampMixin, Base):
    """
    System user.

    Columns
    -------
    email           Unique login identifier.
    full_name       Display name.
    hashed_password bcrypt hash of the user's password.
    is_active       Soft-disable flag — inactive users cannot log in.
    is_superuser    Bypass all permission checks when True.
    role_id         FK → roles.id  (nullable: users can exist without a role).
    """

    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("email", name="uq_users_email"),
        Index("ix_users_role_id", "role_id"),
    )

    email: Mapped[str] = mapped_column(String(320), nullable=False, index=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    role_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("roles.id", ondelete="SET NULL"),
        nullable=True,
    )

    # ── Relationships ────────────────────────────────────────────────────────
    role: Mapped[Role | None] = relationship(
        "Role",
        back_populates="users",
        lazy="select",
    )
    projects: Mapped[list[Project]] = relationship(
        "Project",
        back_populates="owner",
        lazy="select",
        cascade="all, delete-orphan",
    )
    alerts: Mapped[list[Alert]] = relationship(
        "Alert",
        back_populates="user",
        lazy="select",
        cascade="all, delete-orphan",
    )
    audit_logs: Mapped[list[AuditLog]] = relationship(
        "AuditLog",
        back_populates="user",
        lazy="select",
    )
    import_histories: Mapped[list[ImportHistory]] = relationship(
        "ImportHistory",
        back_populates="imported_by",
        lazy="select",
    )

    def __repr__(self) -> str:
        return f"<User id={self.id!r} email={self.email!r}>"

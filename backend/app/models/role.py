"""
Role model.

Defines the set of named roles that can be assigned to users
(e.g. "Admin", "Project Manager", "Viewer").
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.base import TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.user import User


class Role(UUIDMixin, TimestampMixin, Base):
    """
    Application role.

    Columns
    -------
    name        Unique role identifier (e.g. "admin", "manager", "viewer").
    description Optional human-readable description.
    """

    __tablename__ = "roles"
    __table_args__ = (
        UniqueConstraint("name", name="uq_roles_name"),
    )

    name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ── Relationships ────────────────────────────────────────────────────────
    users: Mapped[list[User]] = relationship(
        "User",
        back_populates="role",
        lazy="select",
    )

    def __repr__(self) -> str:
        return f"<Role id={self.id!r} name={self.name!r}>"

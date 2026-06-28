"""
Reusable ORM mixins — every table gets consistent audit columns for free.

Usage::

    from app.models.base import UUIDMixin, TimestampMixin
    from app.database.base import Base

    class Project(UUIDMixin, TimestampMixin, Base):
        __tablename__ = "projects"
        name: Mapped[str] = mapped_column(String(255))
"""

from uuid import uuid4

from sqlalchemy import DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column


class UUIDMixin:
    """Provides a UUID v4 primary key column named `id`."""

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
        index=True,
    )


class TimestampMixin:
    """
    Provides `created_at` and `updated_at` audit timestamp columns.

    - `created_at` is set by the database server on INSERT.
    - `updated_at` is automatically updated by the database server on UPDATE.
    """

    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

"""
Alert model.

Represents a system or user-generated notification.  Alerts are scoped to
a Project and optionally addressed to a specific User.
"""

from __future__ import annotations

import enum
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.base import TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.project import Project
    from app.models.user import User


class AlertSeverity(str, enum.Enum):
    """Severity level of an alert."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AlertType(str, enum.Enum):
    """Classification of what triggered the alert."""

    SYSTEM = "system"
    DATA_QUALITY = "data_quality"
    THRESHOLD = "threshold"
    IMPORT = "import"
    USER_ACTION = "user_action"


class Alert(UUIDMixin, TimestampMixin, Base):
    """
    Notification or warning associated with a project.

    Columns
    -------
    project_id    FK → projects.id.
    user_id       FK → users.id  — optional: target user for the alert.
    title         Short summary headline.
    message       Full alert message body.
    severity      INFO / WARNING / ERROR / CRITICAL.
    alert_type    Categorisation of the alert source.
    is_read       Whether the target user has acknowledged the alert.
    is_resolved   Whether the underlying condition has been addressed.
    resolved_at   Timestamp when the alert was marked resolved.
    """

    __tablename__ = "alerts"
    __table_args__ = (
        Index("ix_alerts_project_id", "project_id"),
        Index("ix_alerts_user_id", "user_id"),
        Index("ix_alerts_is_read", "is_read"),
        Index("ix_alerts_severity", "severity"),
    )

    project_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
    )

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[AlertSeverity] = mapped_column(
        Enum(AlertSeverity, name="alert_severity"),
        nullable=False,
        default=AlertSeverity.INFO,
    )
    alert_type: Mapped[AlertType] = mapped_column(
        Enum(AlertType, name="alert_type"),
        nullable=False,
        default=AlertType.SYSTEM,
    )
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_resolved: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    resolved_at: Mapped[DateTime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # ── Relationships ────────────────────────────────────────────────────────
    project: Mapped[Project] = relationship(
        "Project",
        back_populates="alerts",
        lazy="select",
    )
    user: Mapped[User | None] = relationship(
        "User",
        back_populates="alerts",
        lazy="select",
    )

    def __repr__(self) -> str:
        return f"<Alert id={self.id!r} severity={self.severity!r} title={self.title!r}>"

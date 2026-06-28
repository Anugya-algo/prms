"""
ORM model registry.

Import every model module here so that:
  1. All Table objects are registered with Base.metadata before Alembic
     inspects it for autogenerate.
  2. SQLAlchemy relationship resolution works correctly at startup.

Import order follows the FK dependency graph (parents before children)
to make the module self-documenting.
"""

# ── Tier 0: no FK dependencies ──────────────────────────────────────────────
from app.models.role import Role  # noqa: F401

# ── Tier 1: depends on Role ──────────────────────────────────────────────────
from app.models.user import User  # noqa: F401

# ── Tier 2: top-level domain objects ─────────────────────────────────────────
from app.models.template import Template  # noqa: F401
from app.models.project import Project  # noqa: F401

# ── Tier 3: project-scoped objects ────────────────────────────────────────────
from app.models.project_summary import ProjectSummary  # noqa: F401
from app.models.resource_type import ResourceType  # noqa: F401

# ── Tier 4: resource-type-scoped objects ──────────────────────────────────────
from app.models.template_resource_type import TemplateResourceType  # noqa: F401
from app.models.sheet_mapping import SheetMapping  # noqa: F401
from app.models.resource_field import ResourceField  # noqa: F401

# ── Tier 5: asset-level objects ───────────────────────────────────────────────
from app.models.asset import Asset  # noqa: F401
from app.models.asset_field_value import AssetFieldValue  # noqa: F401

# ── Tier 6: cross-cutting / project-level objects ─────────────────────────────
from app.models.document import Document  # noqa: F401
from app.models.alert import Alert  # noqa: F401
from app.models.audit_log import AuditLog  # noqa: F401
from app.models.import_history import ImportHistory  # noqa: F401
from app.models.report_template import ReportTemplate  # noqa: F401

__all__ = [
    "Role",
    "User",
    "Template",
    "Project",
    "ProjectSummary",
    "ResourceType",
    "TemplateResourceType",
    "SheetMapping",
    "ResourceField",
    "Asset",
    "AssetFieldValue",
    "Document",
    "Alert",
    "AuditLog",
    "ImportHistory",
    "ReportTemplate",
]

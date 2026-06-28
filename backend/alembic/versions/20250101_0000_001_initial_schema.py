"""initial_schema

Revision ID: 001_initial_schema
Revises:
Create Date: 2025-01-01 00:00:00.000000

Creates the full initial database schema for PRMS including:
  - roles
  - users
  - templates
  - projects
  - project_summaries
  - resource_types
  - template_resource_types
  - sheet_mappings
  - resource_fields
  - assets
  - asset_field_values
  - documents
  - alerts
  - audit_logs
  - import_histories
  - report_templates

All ENUM types are created before the tables that depend on them.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _create_enums() -> None:
    """Create all ENUM types used across the schema."""
    op.execute("CREATE TYPE project_status AS ENUM ('draft','active','on_hold','completed','archived')")
    op.execute("CREATE TYPE field_data_type AS ENUM ('text','integer','decimal','boolean','date','datetime','select','multi_select','url','email')")
    op.execute("CREATE TYPE asset_status AS ENUM ('active','inactive','pending','retired')")
    op.execute("CREATE TYPE document_category AS ENUM ('report','contract','specification','photo','other')")
    op.execute("CREATE TYPE alert_severity AS ENUM ('info','warning','error','critical')")
    op.execute("CREATE TYPE alert_type AS ENUM ('system','data_quality','threshold','import','user_action')")
    op.execute("CREATE TYPE audit_action AS ENUM ('create','read','update','delete','login','logout','export','import')")
    op.execute("CREATE TYPE import_status AS ENUM ('pending','processing','success','partial','failed')")
    op.execute("CREATE TYPE report_format AS ENUM ('pdf','excel','csv','json')")


def _drop_enums() -> None:
    """Drop all ENUM types (called during downgrade after tables are dropped)."""
    op.execute("DROP TYPE IF EXISTS project_status")
    op.execute("DROP TYPE IF EXISTS field_data_type")
    op.execute("DROP TYPE IF EXISTS asset_status")
    op.execute("DROP TYPE IF EXISTS document_category")
    op.execute("DROP TYPE IF EXISTS alert_severity")
    op.execute("DROP TYPE IF EXISTS alert_type")
    op.execute("DROP TYPE IF EXISTS audit_action")
    op.execute("DROP TYPE IF EXISTS import_status")
    op.execute("DROP TYPE IF EXISTS report_format")


# ---------------------------------------------------------------------------
# Upgrade
# ---------------------------------------------------------------------------

def upgrade() -> None:
    _create_enums()

    # ── roles ────────────────────────────────────────────────────────────────
    op.create_table(
        "roles",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), onupdate=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_roles_name", "roles", ["name"])
    op.create_unique_constraint("uq_roles_name", "roles", ["name"])

    # ── users ────────────────────────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("is_superuser", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("role_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("roles.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), onupdate=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_users_email", "users", ["email"])
    op.create_index("ix_users_role_id", "users", ["role_id"])
    op.create_unique_constraint("uq_users_email", "users", ["email"])

    # ── templates ────────────────────────────────────────────────────────────
    op.create_table(
        "templates",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("version", sa.String(50), nullable=False, server_default="1.0.0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), onupdate=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_templates_name", "templates", ["name"])
    op.create_index("ix_templates_is_active", "templates", ["is_active"])
    op.create_unique_constraint("uq_templates_name", "templates", ["name"])

    # ── projects ─────────────────────────────────────────────────────────────
    op.create_table(
        "projects",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("code", sa.String(50), nullable=True, unique=True),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("status", sa.Enum("draft", "active", "on_hold", "completed", "archived", name="project_status"), nullable=False, server_default="draft"),
        sa.Column("start_date", sa.Date, nullable=True),
        sa.Column("end_date", sa.Date, nullable=True),
        sa.Column("owner_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("template_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("templates.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), onupdate=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_projects_name", "projects", ["name"])
    op.create_index("ix_projects_code", "projects", ["code"], unique=True)
    op.create_index("ix_projects_owner_id", "projects", ["owner_id"])
    op.create_index("ix_projects_template_id", "projects", ["template_id"])
    op.create_index("ix_projects_status", "projects", ["status"])

    # ── project_summaries ────────────────────────────────────────────────────
    op.create_table(
        "project_summaries",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("project_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("total_assets", sa.Integer, nullable=False, server_default="0"),
        sa.Column("total_resources", sa.Integer, nullable=False, server_default="0"),
        sa.Column("total_documents", sa.Integer, nullable=False, server_default="0"),
        sa.Column("completion_percent", sa.Numeric(5, 2), nullable=False, server_default="0.00"),
        sa.Column("last_calculated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), onupdate=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_project_summaries_project_id", "project_summaries", ["project_id"])
    op.create_unique_constraint("uq_project_summaries_project_id", "project_summaries", ["project_id"])

    # ── resource_types ───────────────────────────────────────────────────────
    op.create_table(
        "resource_types",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("project_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("color", sa.String(7), nullable=True),
        sa.Column("icon", sa.String(100), nullable=True),
        sa.Column("sort_order", sa.Integer, nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), onupdate=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_resource_types_project_id", "resource_types", ["project_id"])
    op.create_unique_constraint("uq_resource_types_project_name", "resource_types", ["project_id", "name"])

    # ── template_resource_types ──────────────────────────────────────────────
    op.create_table(
        "template_resource_types",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("template_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("templates.id", ondelete="CASCADE"), nullable=False),
        sa.Column("resource_type_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("resource_types.id", ondelete="CASCADE"), nullable=False),
        sa.Column("sort_order", sa.Integer, nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), onupdate=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_trt_template_id", "template_resource_types", ["template_id"])
    op.create_index("ix_trt_resource_type_id", "template_resource_types", ["resource_type_id"])
    op.create_unique_constraint("uq_template_resource_types", "template_resource_types", ["template_id", "resource_type_id"])

    # ── sheet_mappings ───────────────────────────────────────────────────────
    op.create_table(
        "sheet_mappings",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("resource_type_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("resource_types.id", ondelete="CASCADE"), nullable=False),
        sa.Column("sheet_name", sa.String(255), nullable=False),
        sa.Column("header_row", sa.Integer, nullable=False, server_default="0"),
        sa.Column("data_start_row", sa.Integer, nullable=False, server_default="1"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("column_mapping", sa.String(4096), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), onupdate=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_sheet_mappings_resource_type_id", "sheet_mappings", ["resource_type_id"])
    op.create_unique_constraint("uq_sheet_mappings_rt_sheet", "sheet_mappings", ["resource_type_id", "sheet_name"])

    # ── resource_fields ──────────────────────────────────────────────────────
    op.create_table(
        "resource_fields",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("resource_type_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("resource_types.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("label", sa.String(255), nullable=False),
        sa.Column("data_type", sa.Enum("text", "integer", "decimal", "boolean", "date", "datetime", "select", "multi_select", "url", "email", name="field_data_type"), nullable=False, server_default="text"),
        sa.Column("is_required", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("is_filterable", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("default_value", sa.String(1024), nullable=True),
        sa.Column("options", sa.Text, nullable=True),
        sa.Column("sort_order", sa.Integer, nullable=False, server_default="0"),
        sa.Column("help_text", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), onupdate=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_resource_fields_resource_type_id", "resource_fields", ["resource_type_id"])
    op.create_unique_constraint("uq_resource_fields_rt_name", "resource_fields", ["resource_type_id", "name"])

    # ── assets ───────────────────────────────────────────────────────────────
    op.create_table(
        "assets",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("project_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("resource_type_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("resource_types.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("code", sa.String(100), nullable=True),
        sa.Column("status", sa.Enum("active", "inactive", "pending", "retired", name="asset_status"), nullable=False, server_default="active"),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("external_ref", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), onupdate=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_assets_name", "assets", ["name"])
    op.create_index("ix_assets_project_id", "assets", ["project_id"])
    op.create_index("ix_assets_resource_type_id", "assets", ["resource_type_id"])
    op.create_index("ix_assets_status", "assets", ["status"])
    op.create_index("ix_assets_external_ref", "assets", ["external_ref"])
    op.create_index("ix_assets_project_code", "assets", ["project_id", "code"], unique=True)

    # ── asset_field_values ───────────────────────────────────────────────────
    op.create_table(
        "asset_field_values",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("asset_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("assets.id", ondelete="CASCADE"), nullable=False),
        sa.Column("field_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("resource_fields.id", ondelete="CASCADE"), nullable=False),
        sa.Column("value", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), onupdate=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_afv_asset_id", "asset_field_values", ["asset_id"])
    op.create_index("ix_afv_field_id", "asset_field_values", ["field_id"])
    op.create_unique_constraint("uq_asset_field_values", "asset_field_values", ["asset_id", "field_id"])

    # ── documents ────────────────────────────────────────────────────────────
    op.create_table(
        "documents",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("project_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("asset_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("assets.id", ondelete="CASCADE"), nullable=True),
        sa.Column("file_name", sa.String(512), nullable=False),
        sa.Column("file_size", sa.BigInteger, nullable=False, server_default="0"),
        sa.Column("mime_type", sa.String(255), nullable=False),
        sa.Column("storage_key", sa.String(1024), nullable=False, unique=True),
        sa.Column("category", sa.Enum("report", "contract", "specification", "photo", "other", name="document_category"), nullable=False, server_default="other"),
        sa.Column("version", sa.BigInteger, nullable=False, server_default="1"),
        sa.Column("checksum", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), onupdate=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_documents_project_id", "documents", ["project_id"])
    op.create_index("ix_documents_asset_id", "documents", ["asset_id"])
    op.create_index("ix_documents_category", "documents", ["category"])

    # ── alerts ───────────────────────────────────────────────────────────────
    op.create_table(
        "alerts",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("project_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("message", sa.Text, nullable=False),
        sa.Column("severity", sa.Enum("info", "warning", "error", "critical", name="alert_severity"), nullable=False, server_default="info"),
        sa.Column("alert_type", sa.Enum("system", "data_quality", "threshold", "import", "user_action", name="alert_type"), nullable=False, server_default="system"),
        sa.Column("is_read", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("is_resolved", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), onupdate=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_alerts_project_id", "alerts", ["project_id"])
    op.create_index("ix_alerts_user_id", "alerts", ["user_id"])
    op.create_index("ix_alerts_is_read", "alerts", ["is_read"])
    op.create_index("ix_alerts_severity", "alerts", ["severity"])

    # ── audit_logs ───────────────────────────────────────────────────────────
    op.create_table(
        "audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("project_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=True),
        sa.Column("action", sa.Enum("create", "read", "update", "delete", "login", "logout", "export", "import", name="audit_action"), nullable=False),
        sa.Column("resource_type", sa.String(100), nullable=False),
        sa.Column("resource_id", sa.String(36), nullable=True),
        sa.Column("old_values", sa.Text, nullable=True),
        sa.Column("new_values", sa.Text, nullable=True),
        sa.Column("ip_address", postgresql.INET, nullable=True),
        sa.Column("user_agent", sa.String(512), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), onupdate=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_audit_logs_user_id", "audit_logs", ["user_id"])
    op.create_index("ix_audit_logs_project_id", "audit_logs", ["project_id"])
    op.create_index("ix_audit_logs_resource_type_id", "audit_logs", ["resource_type", "resource_id"])
    op.create_index("ix_audit_logs_created_at", "audit_logs", ["created_at"])

    # ── import_histories ─────────────────────────────────────────────────────
    op.create_table(
        "import_histories",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("project_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("imported_by_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("file_name", sa.String(512), nullable=False),
        sa.Column("file_size", sa.BigInteger, nullable=False, server_default="0"),
        sa.Column("status", sa.Enum("pending", "processing", "success", "partial", "failed", name="import_status"), nullable=False, server_default="pending"),
        sa.Column("total_rows", sa.Integer, nullable=False, server_default="0"),
        sa.Column("imported_rows", sa.Integer, nullable=False, server_default="0"),
        sa.Column("skipped_rows", sa.Integer, nullable=False, server_default="0"),
        sa.Column("error_rows", sa.Integer, nullable=False, server_default="0"),
        sa.Column("error_log", sa.Text, nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), onupdate=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_import_histories_project_id", "import_histories", ["project_id"])
    op.create_index("ix_import_histories_imported_by_id", "import_histories", ["imported_by_id"])
    op.create_index("ix_import_histories_status", "import_histories", ["status"])

    # ── report_templates ─────────────────────────────────────────────────────
    op.create_table(
        "report_templates",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("project_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("report_format", sa.Enum("pdf", "excel", "csv", "json", name="report_format"), nullable=False, server_default="excel"),
        sa.Column("is_default", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("config", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), onupdate=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_report_templates_project_id", "report_templates", ["project_id"])
    op.create_index("ix_report_templates_is_active", "report_templates", ["is_active"])
    op.create_unique_constraint("uq_report_templates_project_name", "report_templates", ["project_id", "name"])


# ---------------------------------------------------------------------------
# Downgrade
# ---------------------------------------------------------------------------

def downgrade() -> None:
    # Drop in reverse FK dependency order.
    op.drop_table("report_templates")
    op.drop_table("import_histories")
    op.drop_table("audit_logs")
    op.drop_table("alerts")
    op.drop_table("documents")
    op.drop_table("asset_field_values")
    op.drop_table("assets")
    op.drop_table("resource_fields")
    op.drop_table("sheet_mappings")
    op.drop_table("template_resource_types")
    op.drop_table("resource_types")
    op.drop_table("project_summaries")
    op.drop_table("projects")
    op.drop_table("templates")
    op.drop_table("users")
    op.drop_table("roles")
    _drop_enums()

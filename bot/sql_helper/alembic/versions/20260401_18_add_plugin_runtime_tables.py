"""add plugin runtime tables

Revision ID: 20260401_18
Revises: 20260331_17
Create Date: 2026-04-01 12:00:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260401_18"
down_revision = "20260331_17"
branch_labels = None
depends_on = None


def _has_table(inspector, table_name: str) -> bool:
    return table_name in inspector.get_table_names()


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not _has_table(inspector, "plugin_installations"):
        op.create_table(
            "plugin_installations",
            sa.Column("plugin_id", sa.String(length=96), primary_key=True, nullable=False),
            sa.Column("name", sa.String(length=128), nullable=False),
            sa.Column("version", sa.String(length=64), nullable=False, server_default="0.0.0"),
            sa.Column("install_scope", sa.String(length=16), nullable=False, server_default="runtime"),
            sa.Column("plugin_type", sa.String(length=16), nullable=False, server_default="runtime"),
            sa.Column("install_path", sa.String(length=512), nullable=False),
            sa.Column("source_filename", sa.String(length=255), nullable=True),
            sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("requires_restart", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("requires_container_rebuild", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("permissions", sa.JSON(), nullable=False),
            sa.Column("python_dependencies", sa.JSON(), nullable=False),
            sa.Column("manifest", sa.JSON(), nullable=False),
            sa.Column("last_error", sa.Text(), nullable=True),
            sa.Column("installed_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("last_loaded_at", sa.DateTime(), nullable=True),
        )

    if not _has_table(inspector, "plugin_migration_records"):
        op.create_table(
            "plugin_migration_records",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("plugin_id", sa.String(length=96), nullable=False),
            sa.Column("migration_name", sa.String(length=255), nullable=False),
            sa.Column("checksum", sa.String(length=96), nullable=False),
            sa.Column("applied_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.UniqueConstraint("plugin_id", "migration_name", name="uq_plugin_migration_plugin_name"),
        )
        op.create_index("ix_plugin_migration_plugin_id", "plugin_migration_records", ["plugin_id"], unique=False)
        op.create_index("ix_plugin_migration_applied_at", "plugin_migration_records", ["applied_at"], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if _has_table(inspector, "plugin_migration_records"):
        op.drop_index("ix_plugin_migration_applied_at", table_name="plugin_migration_records")
        op.drop_index("ix_plugin_migration_plugin_id", table_name="plugin_migration_records")
        op.drop_table("plugin_migration_records")

    if _has_table(inspector, "plugin_installations"):
        op.drop_table("plugin_installations")

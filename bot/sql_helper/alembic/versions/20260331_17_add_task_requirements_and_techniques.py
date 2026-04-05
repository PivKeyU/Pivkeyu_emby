"""add xiuxian task requirements and techniques

Revision ID: 20260331_17
Revises: 20260330_16
Create Date: 2026-03-31 17:30:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260331_17"
down_revision = "20260330_16"
branch_labels = None
depends_on = None


def _has_table(inspector, table_name: str) -> bool:
    return table_name in inspector.get_table_names()


def _has_column(inspector, table_name: str, column_name: str) -> bool:
    return column_name in {column["name"] for column in inspector.get_columns(table_name)}


def _add_column_if_missing(inspector, table_name: str, column: sa.Column) -> None:
    if _has_table(inspector, table_name) and not _has_column(inspector, table_name, column.name):
        op.add_column(table_name, column)


def _drop_column_if_exists(inspector, table_name: str, column_name: str) -> None:
    if _has_table(inspector, table_name) and _has_column(inspector, table_name, column_name):
        op.drop_column(table_name, column_name)


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    _add_column_if_missing(inspector, "xiuxian_profiles", sa.Column("current_technique_id", sa.Integer(), nullable=True))

    _add_column_if_missing(inspector, "xiuxian_tasks", sa.Column("required_item_kind", sa.String(length=16), nullable=True))
    _add_column_if_missing(inspector, "xiuxian_tasks", sa.Column("required_item_ref_id", sa.Integer(), nullable=True))
    _add_column_if_missing(
        inspector,
        "xiuxian_tasks",
        sa.Column("required_item_quantity", sa.Integer(), nullable=False, server_default="0"),
    )

    if not _has_table(inspector, "xiuxian_techniques"):
        op.create_table(
            "xiuxian_techniques",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("name", sa.String(length=64), nullable=False, unique=True),
            sa.Column("rarity", sa.String(length=32), nullable=False, server_default="凡品"),
            sa.Column("technique_type", sa.String(length=16), nullable=False, server_default="balanced"),
            sa.Column("image_url", sa.String(length=512), nullable=True),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("attack_bonus", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("defense_bonus", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("bone_bonus", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("comprehension_bonus", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("divine_sense_bonus", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("fortune_bonus", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("qi_blood_bonus", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("true_yuan_bonus", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("body_movement_bonus", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("duel_rate_bonus", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("cultivation_bonus", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("breakthrough_bonus", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("min_realm_stage", sa.String(length=32), nullable=True),
            sa.Column("min_realm_layer", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if _has_table(inspector, "xiuxian_techniques"):
        op.drop_table("xiuxian_techniques")

    _drop_column_if_exists(inspector, "xiuxian_tasks", "required_item_quantity")
    _drop_column_if_exists(inspector, "xiuxian_tasks", "required_item_ref_id")
    _drop_column_if_exists(inspector, "xiuxian_tasks", "required_item_kind")
    _drop_column_if_exists(inspector, "xiuxian_profiles", "current_technique_id")

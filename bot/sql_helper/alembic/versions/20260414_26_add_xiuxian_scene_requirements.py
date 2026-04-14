"""add xiuxian scene requirements

Revision ID: 20260414_26
Revises: 20260414_25
Create Date: 2026-04-14 23:40:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260414_26"
down_revision = "20260414_25"
branch_labels = None
depends_on = None


def _inspector():
    return sa.inspect(op.get_bind())


def _has_table(table_name: str) -> bool:
    return table_name in _inspector().get_table_names()


def _has_column(table_name: str, column_name: str) -> bool:
    if not _has_table(table_name):
        return False
    return any(column.get("name") == column_name for column in _inspector().get_columns(table_name))


def upgrade() -> None:
    if _has_table("xiuxian_scenes"):
        with op.batch_alter_table("xiuxian_scenes") as batch_op:
            if not _has_column("xiuxian_scenes", "min_realm_stage"):
                batch_op.add_column(sa.Column("min_realm_stage", sa.String(length=32), nullable=True))
            if not _has_column("xiuxian_scenes", "min_realm_layer"):
                batch_op.add_column(sa.Column("min_realm_layer", sa.Integer(), nullable=False, server_default="1"))
            if not _has_column("xiuxian_scenes", "min_combat_power"):
                batch_op.add_column(sa.Column("min_combat_power", sa.Integer(), nullable=False, server_default="0"))


def downgrade() -> None:
    if _has_table("xiuxian_scenes"):
        with op.batch_alter_table("xiuxian_scenes") as batch_op:
            if _has_column("xiuxian_scenes", "min_combat_power"):
                batch_op.drop_column("min_combat_power")
            if _has_column("xiuxian_scenes", "min_realm_layer"):
                batch_op.drop_column("min_realm_layer")
            if _has_column("xiuxian_scenes", "min_realm_stage"):
                batch_op.drop_column("min_realm_stage")

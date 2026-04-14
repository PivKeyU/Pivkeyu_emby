"""add xiuxian talisman effect uses

Revision ID: 20260414_25
Revises: 20260414_24
Create Date: 2026-04-14 22:10:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260414_25"
down_revision = "20260414_24"
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
    if _has_table("xiuxian_talismans") and not _has_column("xiuxian_talismans", "effect_uses"):
        with op.batch_alter_table("xiuxian_talismans") as batch_op:
            batch_op.add_column(sa.Column("effect_uses", sa.Integer(), nullable=False, server_default="1"))


def downgrade() -> None:
    if _has_table("xiuxian_talismans") and _has_column("xiuxian_talismans", "effect_uses"):
        with op.batch_alter_table("xiuxian_talismans") as batch_op:
            batch_op.drop_column("effect_uses")

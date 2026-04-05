"""rename xiuxian power bonus columns to attack bonus

Revision ID: 20260330_10
Revises: 20260330_09
Create Date: 2026-03-30 12:40:00
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20260330_10"
down_revision = "20260330_09"
branch_labels = None
depends_on = None


def _table_names() -> set[str]:
    return set(sa.inspect(op.get_bind()).get_table_names())


def _column_names(table_name: str) -> set[str]:
    inspector = sa.inspect(op.get_bind())
    return {column["name"] for column in inspector.get_columns(table_name)}


def _rename_column_if_needed(table_name: str, old_name: str, new_name: str) -> None:
    if table_name not in _table_names():
        return

    columns = _column_names(table_name)
    if new_name in columns or old_name not in columns:
        return

    op.alter_column(
        table_name,
        old_name,
        new_column_name=new_name,
        existing_type=sa.Integer(),
        existing_nullable=False,
    )


def upgrade() -> None:
    _rename_column_if_needed("xiuxian_artifacts", "power_bonus", "attack_bonus")
    _rename_column_if_needed("xiuxian_talismans", "power_bonus", "attack_bonus")


def downgrade() -> None:
    _rename_column_if_needed("xiuxian_artifacts", "attack_bonus", "power_bonus")
    _rename_column_if_needed("xiuxian_talismans", "attack_bonus", "power_bonus")

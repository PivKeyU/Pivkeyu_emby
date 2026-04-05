"""add effect formula fields for xiuxian items

Revision ID: 20260329_07
Revises: 20260329_06
Create Date: 2026-03-29 23:10:00
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20260329_07"
down_revision = "20260329_06"
branch_labels = None
depends_on = None


def _column_names(table_name: str) -> set[str]:
    inspector = sa.inspect(op.get_bind())
    return {column["name"] for column in inspector.get_columns(table_name)}


def upgrade() -> None:
    for table_name in ("xiuxian_artifacts", "xiuxian_pills", "xiuxian_talismans"):
        columns = _column_names(table_name)
        if "effect_formula" not in columns:
            op.add_column(table_name, sa.Column("effect_formula", sa.Text(), nullable=True))


def downgrade() -> None:
    for table_name in ("xiuxian_talismans", "xiuxian_pills", "xiuxian_artifacts"):
        columns = _column_names(table_name)
        if "effect_formula" in columns:
            op.drop_column(table_name, "effect_formula")

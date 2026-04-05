"""drop unused xiuxian effect formula columns

Revision ID: 20260330_09
Revises: 20260330_08
Create Date: 2026-03-30 12:10:00
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20260330_09"
down_revision = "20260330_08"
branch_labels = None
depends_on = None


def _table_names() -> set[str]:
    return set(sa.inspect(op.get_bind()).get_table_names())


def _column_names(table_name: str) -> set[str]:
    inspector = sa.inspect(op.get_bind())
    return {column["name"] for column in inspector.get_columns(table_name)}


def upgrade() -> None:
    for table_name in ("xiuxian_artifacts", "xiuxian_pills", "xiuxian_talismans"):
        if table_name not in _table_names():
            continue
        columns = _column_names(table_name)
        if "effect_formula" in columns:
            op.drop_column(table_name, "effect_formula")


def downgrade() -> None:
    if "xiuxian_artifacts" in _table_names():
        columns = _column_names("xiuxian_artifacts")
        if "effect_formula" not in columns:
            op.add_column("xiuxian_artifacts", sa.Column("effect_formula", sa.Text(), nullable=True))

    if "xiuxian_pills" in _table_names():
        columns = _column_names("xiuxian_pills")
        if "effect_formula" not in columns:
            op.add_column("xiuxian_pills", sa.Column("effect_formula", sa.Text(), nullable=True))

    if "xiuxian_talismans" in _table_names():
        columns = _column_names("xiuxian_talismans")
        if "effect_formula" not in columns:
            op.add_column("xiuxian_talismans", sa.Column("effect_formula", sa.Text(), nullable=True))

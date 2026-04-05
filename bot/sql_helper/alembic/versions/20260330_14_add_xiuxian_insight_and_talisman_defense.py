"""add xiuxian insight and talisman defense

Revision ID: 20260330_14
Revises: 20260330_13
Create Date: 2026-03-30 23:55:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260330_14"
down_revision = "20260330_13"
branch_labels = None
depends_on = None


def _has_table(inspector, table_name: str) -> bool:
    return table_name in inspector.get_table_names()


def _has_column(inspector, table_name: str, column_name: str) -> bool:
    return column_name in {column["name"] for column in inspector.get_columns(table_name)}


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if _has_table(inspector, "xiuxian_profiles") and not _has_column(inspector, "xiuxian_profiles", "insight_bonus"):
        op.add_column(
            "xiuxian_profiles",
            sa.Column("insight_bonus", sa.Integer(), nullable=False, server_default="0"),
        )

    if _has_table(inspector, "xiuxian_talismans") and not _has_column(inspector, "xiuxian_talismans", "defense_bonus"):
        op.add_column(
            "xiuxian_talismans",
            sa.Column("defense_bonus", sa.Integer(), nullable=False, server_default="0"),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if _has_table(inspector, "xiuxian_talismans") and _has_column(inspector, "xiuxian_talismans", "defense_bonus"):
        op.drop_column("xiuxian_talismans", "defense_bonus")

    if _has_table(inspector, "xiuxian_profiles") and _has_column(inspector, "xiuxian_profiles", "insight_bonus"):
        op.drop_column("xiuxian_profiles", "insight_bonus")

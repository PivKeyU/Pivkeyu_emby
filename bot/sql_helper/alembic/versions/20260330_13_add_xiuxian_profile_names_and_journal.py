"""add xiuxian profile names and journal

Revision ID: 20260330_13
Revises: 20260330_12
Create Date: 2026-03-30 23:30:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260330_13"
down_revision = "20260330_12"
branch_labels = None
depends_on = None


def _has_table(inspector, table_name: str) -> bool:
    return table_name in inspector.get_table_names()


def _has_column(inspector, table_name: str, column_name: str) -> bool:
    return column_name in {column["name"] for column in inspector.get_columns(table_name)}


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if _has_table(inspector, "xiuxian_profiles"):
        profile_columns = {
            "display_name": sa.Column("display_name", sa.String(length=128), nullable=True),
            "username": sa.Column("username", sa.String(length=64), nullable=True),
            "sect_contribution": sa.Column("sect_contribution", sa.Integer(), nullable=False, server_default="0"),
        }
        for column_name, column in profile_columns.items():
            if not _has_column(inspector, "xiuxian_profiles", column_name):
                op.add_column("xiuxian_profiles", column)

    if not _has_table(inspector, "xiuxian_journals"):
        op.create_table(
            "xiuxian_journals",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("tg", sa.BigInteger(), nullable=False),
            sa.Column("action_type", sa.String(length=32), nullable=False),
            sa.Column("title", sa.String(length=128), nullable=False),
            sa.Column("detail", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            mysql_charset="utf8mb4",
            mysql_collate="utf8mb4_unicode_ci",
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if _has_table(inspector, "xiuxian_journals"):
        op.drop_table("xiuxian_journals")

    if _has_table(inspector, "xiuxian_profiles"):
        for column_name in ("sect_contribution", "username", "display_name"):
            if _has_column(inspector, "xiuxian_profiles", column_name):
                op.drop_column("xiuxian_profiles", column_name)

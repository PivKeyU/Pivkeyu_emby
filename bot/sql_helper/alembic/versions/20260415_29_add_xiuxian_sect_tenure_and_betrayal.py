"""add xiuxian sect tenure and betrayal cooldown

Revision ID: 20260415_29
Revises: 20260415_28
Create Date: 2026-04-15 16:20:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260415_29"
down_revision = "20260415_28"
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
    if _has_table("xiuxian_profiles"):
        with op.batch_alter_table("xiuxian_profiles") as batch_op:
            if not _has_column("xiuxian_profiles", "sect_joined_at"):
                batch_op.add_column(sa.Column("sect_joined_at", sa.DateTime(), nullable=True))
            if not _has_column("xiuxian_profiles", "sect_betrayal_until"):
                batch_op.add_column(sa.Column("sect_betrayal_until", sa.DateTime(), nullable=True))

        profiles = sa.table(
            "xiuxian_profiles",
            sa.column("sect_id", sa.Integer()),
            sa.column("sect_joined_at", sa.DateTime()),
            sa.column("last_salary_claim_at", sa.DateTime()),
            sa.column("created_at", sa.DateTime()),
            sa.column("updated_at", sa.DateTime()),
        )
        bind = op.get_bind()
        bind.execute(
            profiles.update()
            .where(profiles.c.sect_id.is_not(None))
            .where(profiles.c.sect_joined_at.is_(None))
            .values(
                sect_joined_at=sa.func.coalesce(
                    profiles.c.last_salary_claim_at,
                    profiles.c.created_at,
                    profiles.c.updated_at,
                    sa.func.now(),
                )
            )
        )


def downgrade() -> None:
    if _has_table("xiuxian_profiles"):
        with op.batch_alter_table("xiuxian_profiles") as batch_op:
            if _has_column("xiuxian_profiles", "sect_betrayal_until"):
                batch_op.drop_column("sect_betrayal_until")
            if _has_column("xiuxian_profiles", "sect_joined_at"):
                batch_op.drop_column("sect_joined_at")

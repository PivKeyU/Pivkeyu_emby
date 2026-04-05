"""add multi-use fields to Rcode

Revision ID: 20260329_03
Revises: 20260315_02
Create Date: 2026-03-29 14:00:00
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20260329_03"
down_revision = "20260315_02"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    column_names = {column["name"] for column in inspector.get_columns("Rcode")}

    if "use_limit" not in column_names:
        op.add_column(
            "Rcode",
            sa.Column("use_limit", sa.Integer(), nullable=False, server_default="1"),
        )

    if "use_count" not in column_names:
        op.add_column(
            "Rcode",
            sa.Column("use_count", sa.Integer(), nullable=False, server_default="0"),
        )

    op.execute("UPDATE `Rcode` SET `use_limit` = COALESCE(`use_limit`, 1)")
    op.execute(
        """
        UPDATE `Rcode`
        SET `use_count` = CASE
            WHEN `used` IS NULL THEN COALESCE(`use_count`, 0)
            ELSE GREATEST(COALESCE(`use_count`, 0), 1)
        END
        """
    )
    op.execute("UPDATE `Rcode` SET `use_limit` = 1 WHERE `use_limit` < 1")
    op.alter_column("Rcode", "use_limit", server_default=None)
    op.alter_column("Rcode", "use_count", server_default=None)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    column_names = {column["name"] for column in inspector.get_columns("Rcode")}

    if "use_count" in column_names:
        op.drop_column("Rcode", "use_count")

    if "use_limit" in column_names:
        op.drop_column("Rcode", "use_limit")

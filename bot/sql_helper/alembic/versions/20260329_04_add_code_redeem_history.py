"""add redeem history table for codes

Revision ID: 20260329_04
Revises: 20260329_03
Create Date: 2026-03-29 18:20:00
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20260329_04"
down_revision = "20260329_03"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    table_names = set(inspector.get_table_names())

    if "RcodeRedeem" not in table_names:
        op.create_table(
            "RcodeRedeem",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("code", sa.String(length=50), nullable=False),
            sa.Column("user_id", sa.BigInteger(), nullable=False),
            sa.Column("owner_tg", sa.BigInteger(), nullable=True),
            sa.Column("code_days", sa.Integer(), nullable=True),
            sa.Column("use_index", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("redeemed_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.ForeignKeyConstraint(["code"], ["Rcode.code"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("code", "user_id", name="uq_rcode_redeem_code_user"),
        )
        op.create_index("ix_rcode_redeem_user_id", "RcodeRedeem", ["user_id"], unique=False)
        op.create_index("ix_rcode_redeem_redeemed_at", "RcodeRedeem", ["redeemed_at"], unique=False)

    op.execute(
        """
        INSERT INTO `RcodeRedeem` (`code`, `user_id`, `owner_tg`, `code_days`, `use_index`, `redeemed_at`)
        SELECT
            r.`code`,
            r.`used`,
            r.`tg`,
            r.`us`,
            GREATEST(COALESCE(r.`use_count`, 1), 1),
            COALESCE(r.`usedtime`, CURRENT_TIMESTAMP)
        FROM `Rcode` r
        WHERE r.`used` IS NOT NULL
          AND NOT EXISTS (
            SELECT 1
            FROM `RcodeRedeem` h
            WHERE h.`code` = r.`code`
              AND h.`user_id` = r.`used`
          )
        """
    )

    op.alter_column("RcodeRedeem", "use_index", server_default=None)
    op.alter_column("RcodeRedeem", "redeemed_at", server_default=None)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    table_names = set(inspector.get_table_names())

    if "RcodeRedeem" in table_names:
        op.drop_index("ix_rcode_redeem_redeemed_at", table_name="RcodeRedeem")
        op.drop_index("ix_rcode_redeem_user_id", table_name="RcodeRedeem")
        op.drop_table("RcodeRedeem")

"""add advanced xiuxian fields and talisman tables

Revision ID: 20260329_06
Revises: 20260329_05
Create Date: 2026-03-29 22:30:00
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20260329_06"
down_revision = "20260329_05"
branch_labels = None
depends_on = None


def _table_names() -> set[str]:
    return set(sa.inspect(op.get_bind()).get_table_names())


def _column_names(table_name: str) -> set[str]:
    inspector = sa.inspect(op.get_bind())
    return {column["name"] for column in inspector.get_columns(table_name)}


def _index_names(table_name: str) -> set[str]:
    inspector = sa.inspect(op.get_bind())
    return {index["name"] for index in inspector.get_indexes(table_name)}


def upgrade() -> None:
    table_names = _table_names()

    if "xiuxian_profiles" in table_names:
        columns = _column_names("xiuxian_profiles")
        if "active_talisman_id" not in columns:
            op.add_column(
                "xiuxian_profiles",
                sa.Column("active_talisman_id", sa.Integer(), nullable=True),
            )
        if "retreat_started_at" not in columns:
            op.add_column(
                "xiuxian_profiles",
                sa.Column("retreat_started_at", sa.DateTime(), nullable=True),
            )
        if "retreat_end_at" not in columns:
            op.add_column(
                "xiuxian_profiles",
                sa.Column("retreat_end_at", sa.DateTime(), nullable=True),
            )
        if "retreat_gain_per_minute" not in columns:
            op.add_column(
                "xiuxian_profiles",
                sa.Column("retreat_gain_per_minute", sa.Integer(), nullable=False, server_default="0"),
            )
        if "retreat_cost_per_minute" not in columns:
            op.add_column(
                "xiuxian_profiles",
                sa.Column("retreat_cost_per_minute", sa.Integer(), nullable=False, server_default="0"),
            )
        if "retreat_minutes_total" not in columns:
            op.add_column(
                "xiuxian_profiles",
                sa.Column("retreat_minutes_total", sa.Integer(), nullable=False, server_default="0"),
            )
        if "retreat_minutes_resolved" not in columns:
            op.add_column(
                "xiuxian_profiles",
                sa.Column("retreat_minutes_resolved", sa.Integer(), nullable=False, server_default="0"),
            )

        columns = _column_names("xiuxian_profiles")
        for column_name in (
            "retreat_gain_per_minute",
            "retreat_cost_per_minute",
            "retreat_minutes_total",
            "retreat_minutes_resolved",
        ):
            if column_name in columns:
                op.alter_column("xiuxian_profiles", column_name, server_default=None)

    if "xiuxian_artifacts" in table_names:
        columns = _column_names("xiuxian_artifacts")
        if "min_realm_stage" not in columns:
            op.add_column(
                "xiuxian_artifacts",
                sa.Column("min_realm_stage", sa.String(length=32), nullable=True),
            )
        if "min_realm_layer" not in columns:
            op.add_column(
                "xiuxian_artifacts",
                sa.Column("min_realm_layer", sa.Integer(), nullable=False, server_default="1"),
            )
            op.alter_column("xiuxian_artifacts", "min_realm_layer", server_default=None)

    if "xiuxian_pills" in table_names:
        columns = _column_names("xiuxian_pills")
        if "min_realm_stage" not in columns:
            op.add_column(
                "xiuxian_pills",
                sa.Column("min_realm_stage", sa.String(length=32), nullable=True),
            )
        if "min_realm_layer" not in columns:
            op.add_column(
                "xiuxian_pills",
                sa.Column("min_realm_layer", sa.Integer(), nullable=False, server_default="1"),
            )
            op.alter_column("xiuxian_pills", "min_realm_layer", server_default=None)

    if "xiuxian_talismans" not in table_names:
        op.create_table(
            "xiuxian_talismans",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("name", sa.String(length=64), nullable=False),
            sa.Column("rarity", sa.String(length=32), nullable=False, server_default="凡品"),
            sa.Column("image_url", sa.String(length=512), nullable=True),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("power_bonus", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("duel_rate_bonus", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("merit_bonus", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("min_realm_stage", sa.String(length=32), nullable=True),
            sa.Column("min_realm_layer", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("1")),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("name", name="uq_xiuxian_talisman_name"),
        )
        op.alter_column("xiuxian_talismans", "rarity", server_default=None)
        op.alter_column("xiuxian_talismans", "power_bonus", server_default=None)
        op.alter_column("xiuxian_talismans", "duel_rate_bonus", server_default=None)
        op.alter_column("xiuxian_talismans", "merit_bonus", server_default=None)
        op.alter_column("xiuxian_talismans", "min_realm_layer", server_default=None)
        op.alter_column("xiuxian_talismans", "enabled", server_default=None)
        op.alter_column("xiuxian_talismans", "created_at", server_default=None)
        op.alter_column("xiuxian_talismans", "updated_at", server_default=None)

    table_names = _table_names()
    if "xiuxian_talisman_inventory" not in table_names:
        op.create_table(
            "xiuxian_talisman_inventory",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("tg", sa.BigInteger(), nullable=False),
            sa.Column("talisman_id", sa.Integer(), nullable=False),
            sa.Column("quantity", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.ForeignKeyConstraint(["talisman_id"], ["xiuxian_talismans.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("tg", "talisman_id", name="uq_xiuxian_talisman_inventory"),
        )
        op.alter_column("xiuxian_talisman_inventory", "quantity", server_default=None)
        op.alter_column("xiuxian_talisman_inventory", "created_at", server_default=None)
        op.alter_column("xiuxian_talisman_inventory", "updated_at", server_default=None)

    table_names = _table_names()
    if "xiuxian_duel_records" in table_names:
        index_names = _index_names("xiuxian_duel_records")
        if "ix_xiuxian_duel_created_at" not in index_names:
            op.create_index("ix_xiuxian_duel_created_at", "xiuxian_duel_records", ["created_at"], unique=False)

    op.execute(
        """
        INSERT INTO `xiuxian_settings` (`setting_key`, `setting_value`, `updated_at`)
        VALUES
          ('chat_cultivation_chance', CAST(8 AS JSON), CURRENT_TIMESTAMP),
          ('chat_cultivation_min_gain', CAST(1 AS JSON), CURRENT_TIMESTAMP),
          ('chat_cultivation_max_gain', CAST(3 AS JSON), CURRENT_TIMESTAMP)
        ON DUPLICATE KEY UPDATE
          `setting_value` = `setting_value`,
          `updated_at` = `updated_at`;
        """
    )
    op.execute(
        """
        UPDATE `xiuxian_settings`
        SET `setting_value` = CAST(1 AS JSON), `updated_at` = CURRENT_TIMESTAMP
        WHERE `setting_key` = 'min_coin_exchange'
          AND CAST(JSON_UNQUOTE(`setting_value`) AS UNSIGNED) = 100;
        """
    )


def downgrade() -> None:
    table_names = _table_names()

    if "xiuxian_talisman_inventory" in table_names:
        op.drop_table("xiuxian_talisman_inventory")

    table_names = _table_names()
    if "xiuxian_talismans" in table_names:
        op.drop_table("xiuxian_talismans")

    if "xiuxian_pills" in table_names:
        columns = _column_names("xiuxian_pills")
        if "min_realm_layer" in columns:
            op.drop_column("xiuxian_pills", "min_realm_layer")
        if "min_realm_stage" in columns:
            op.drop_column("xiuxian_pills", "min_realm_stage")

    if "xiuxian_artifacts" in table_names:
        columns = _column_names("xiuxian_artifacts")
        if "min_realm_layer" in columns:
            op.drop_column("xiuxian_artifacts", "min_realm_layer")
        if "min_realm_stage" in columns:
            op.drop_column("xiuxian_artifacts", "min_realm_stage")

    if "xiuxian_profiles" in table_names:
        columns = _column_names("xiuxian_profiles")
        for column_name in (
            "retreat_minutes_resolved",
            "retreat_minutes_total",
            "retreat_cost_per_minute",
            "retreat_gain_per_minute",
            "retreat_end_at",
            "retreat_started_at",
            "active_talisman_id",
        ):
            if column_name in columns:
                op.drop_column("xiuxian_profiles", column_name)

    if "xiuxian_settings" in table_names:
        op.execute(
            """
            DELETE FROM `xiuxian_settings`
            WHERE `setting_key` IN (
              'chat_cultivation_chance',
              'chat_cultivation_min_gain',
              'chat_cultivation_max_gain'
            );
            """
        )

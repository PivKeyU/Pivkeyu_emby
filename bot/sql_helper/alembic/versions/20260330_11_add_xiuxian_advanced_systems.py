"""add advanced xiuxian systems

Revision ID: 20260330_11
Revises: 20260330_10
Create Date: 2026-03-30 18:30:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260330_11"
down_revision = "20260330_10"
branch_labels = None
depends_on = None


def _has_table(inspector, table_name: str) -> bool:
    return table_name in inspector.get_table_names()


def _has_column(inspector, table_name: str, column_name: str) -> bool:
    return column_name in {column["name"] for column in inspector.get_columns(table_name)}


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    profile_columns = {
        "sect_id": sa.Column("sect_id", sa.Integer(), nullable=True),
        "sect_role_key": sa.Column("sect_role_key", sa.String(length=32), nullable=True),
        "last_salary_claim_at": sa.Column("last_salary_claim_at", sa.DateTime(), nullable=True),
        "robbery_daily_count": sa.Column("robbery_daily_count", sa.Integer(), nullable=False, server_default="0"),
        "robbery_day_key": sa.Column("robbery_day_key", sa.String(length=16), nullable=True),
    }
    for column_name, column in profile_columns.items():
        if not _has_column(inspector, "xiuxian_profiles", column_name):
            op.add_column("xiuxian_profiles", column)

    if not _has_table(inspector, "xiuxian_sects"):
        op.create_table(
            "xiuxian_sects",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("name", sa.String(length=64), nullable=False, unique=True),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("image_url", sa.String(length=512), nullable=True),
            sa.Column("min_realm_stage", sa.String(length=32), nullable=True),
            sa.Column("min_realm_layer", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("min_merit", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("min_stone", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            mysql_charset="utf8mb4",
            mysql_collate="utf8mb4_unicode_ci",
        )

    if not _has_table(inspector, "xiuxian_sect_roles"):
        op.create_table(
            "xiuxian_sect_roles",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("sect_id", sa.Integer(), sa.ForeignKey("xiuxian_sects.id", ondelete="CASCADE"), nullable=False),
            sa.Column("role_key", sa.String(length=32), nullable=False),
            sa.Column("role_name", sa.String(length=64), nullable=False),
            sa.Column("attack_bonus", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("defense_bonus", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("duel_rate_bonus", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("cultivation_bonus", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("merit_bonus", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("monthly_salary", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("can_publish_tasks", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.UniqueConstraint("sect_id", "role_key", name="uq_xiuxian_sect_role_key"),
            mysql_charset="utf8mb4",
            mysql_collate="utf8mb4_unicode_ci",
        )

    if not _has_table(inspector, "xiuxian_materials"):
        op.create_table(
            "xiuxian_materials",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("name", sa.String(length=64), nullable=False, unique=True),
            sa.Column("quality_level", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("image_url", sa.String(length=512), nullable=True),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            mysql_charset="utf8mb4",
            mysql_collate="utf8mb4_unicode_ci",
        )

    if not _has_table(inspector, "xiuxian_material_inventory"):
        op.create_table(
            "xiuxian_material_inventory",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("tg", sa.BigInteger(), nullable=False),
            sa.Column("material_id", sa.Integer(), sa.ForeignKey("xiuxian_materials.id", ondelete="CASCADE"), nullable=False),
            sa.Column("quantity", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.UniqueConstraint("tg", "material_id", name="uq_xiuxian_material_inventory"),
            mysql_charset="utf8mb4",
            mysql_collate="utf8mb4_unicode_ci",
        )

    if not _has_table(inspector, "xiuxian_recipes"):
        op.create_table(
            "xiuxian_recipes",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("name", sa.String(length=64), nullable=False, unique=True),
            sa.Column("recipe_kind", sa.String(length=16), nullable=False),
            sa.Column("result_kind", sa.String(length=16), nullable=False),
            sa.Column("result_ref_id", sa.Integer(), nullable=False),
            sa.Column("result_quantity", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("required_merit", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("base_success_rate", sa.Integer(), nullable=False, server_default="60"),
            sa.Column("broadcast_on_success", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            mysql_charset="utf8mb4",
            mysql_collate="utf8mb4_unicode_ci",
        )

    if not _has_table(inspector, "xiuxian_recipe_ingredients"):
        op.create_table(
            "xiuxian_recipe_ingredients",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("recipe_id", sa.Integer(), sa.ForeignKey("xiuxian_recipes.id", ondelete="CASCADE"), nullable=False),
            sa.Column("material_id", sa.Integer(), sa.ForeignKey("xiuxian_materials.id", ondelete="CASCADE"), nullable=False),
            sa.Column("quantity", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            mysql_charset="utf8mb4",
            mysql_collate="utf8mb4_unicode_ci",
        )

    if not _has_table(inspector, "xiuxian_scenes"):
        op.create_table(
            "xiuxian_scenes",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("name", sa.String(length=64), nullable=False, unique=True),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("image_url", sa.String(length=512), nullable=True),
            sa.Column("max_minutes", sa.Integer(), nullable=False, server_default="60"),
            sa.Column("event_pool", sa.JSON(), nullable=True),
            sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            mysql_charset="utf8mb4",
            mysql_collate="utf8mb4_unicode_ci",
        )

    if not _has_table(inspector, "xiuxian_scene_drops"):
        op.create_table(
            "xiuxian_scene_drops",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("scene_id", sa.Integer(), sa.ForeignKey("xiuxian_scenes.id", ondelete="CASCADE"), nullable=False),
            sa.Column("reward_kind", sa.String(length=16), nullable=False),
            sa.Column("reward_ref_id", sa.Integer(), nullable=True),
            sa.Column("quantity_min", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("quantity_max", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("weight", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("stone_reward", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("merit_reward", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("event_text", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            mysql_charset="utf8mb4",
            mysql_collate="utf8mb4_unicode_ci",
        )

    if not _has_table(inspector, "xiuxian_explorations"):
        op.create_table(
            "xiuxian_explorations",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("tg", sa.BigInteger(), nullable=False),
            sa.Column("scene_id", sa.Integer(), sa.ForeignKey("xiuxian_scenes.id", ondelete="CASCADE"), nullable=False),
            sa.Column("started_at", sa.DateTime(), nullable=False),
            sa.Column("end_at", sa.DateTime(), nullable=False),
            sa.Column("claimed", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("reward_kind", sa.String(length=16), nullable=True),
            sa.Column("reward_ref_id", sa.Integer(), nullable=True),
            sa.Column("reward_quantity", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("stone_reward", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("merit_reward", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("event_text", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            mysql_charset="utf8mb4",
            mysql_collate="utf8mb4_unicode_ci",
        )

    if not _has_table(inspector, "xiuxian_tasks"):
        op.create_table(
            "xiuxian_tasks",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("title", sa.String(length=128), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("task_scope", sa.String(length=16), nullable=False),
            sa.Column("task_type", sa.String(length=16), nullable=False, server_default="quiz"),
            sa.Column("owner_tg", sa.BigInteger(), nullable=True),
            sa.Column("sect_id", sa.Integer(), nullable=True),
            sa.Column("question_text", sa.Text(), nullable=True),
            sa.Column("answer_text", sa.String(length=255), nullable=True),
            sa.Column("image_url", sa.String(length=512), nullable=True),
            sa.Column("reward_stone", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("reward_merit", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("reward_item_kind", sa.String(length=16), nullable=True),
            sa.Column("reward_item_ref_id", sa.Integer(), nullable=True),
            sa.Column("reward_item_quantity", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("max_claimants", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("claimants_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("active_in_group", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("group_chat_id", sa.BigInteger(), nullable=True),
            sa.Column("group_message_id", sa.Integer(), nullable=True),
            sa.Column("winner_tg", sa.BigInteger(), nullable=True),
            sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("status", sa.String(length=16), nullable=False, server_default="open"),
            sa.Column("deadline_at", sa.DateTime(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            mysql_charset="utf8mb4",
            mysql_collate="utf8mb4_unicode_ci",
        )

    if not _has_table(inspector, "xiuxian_task_claims"):
        op.create_table(
            "xiuxian_task_claims",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("task_id", sa.Integer(), sa.ForeignKey("xiuxian_tasks.id", ondelete="CASCADE"), nullable=False),
            sa.Column("tg", sa.BigInteger(), nullable=False),
            sa.Column("status", sa.String(length=16), nullable=False, server_default="accepted"),
            sa.Column("submitted_answer", sa.String(length=255), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.UniqueConstraint("task_id", "tg", name="uq_xiuxian_task_claim"),
            mysql_charset="utf8mb4",
            mysql_collate="utf8mb4_unicode_ci",
        )

    if not _has_table(inspector, "xiuxian_red_envelopes"):
        op.create_table(
            "xiuxian_red_envelopes",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("creator_tg", sa.BigInteger(), nullable=False),
            sa.Column("cover_text", sa.String(length=255), nullable=True),
            sa.Column("mode", sa.String(length=16), nullable=False),
            sa.Column("target_tg", sa.BigInteger(), nullable=True),
            sa.Column("amount_total", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("count_total", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("remaining_amount", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("remaining_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("merit_rewarded", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("status", sa.String(length=16), nullable=False, server_default="active"),
            sa.Column("group_chat_id", sa.BigInteger(), nullable=True),
            sa.Column("message_id", sa.Integer(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            mysql_charset="utf8mb4",
            mysql_collate="utf8mb4_unicode_ci",
        )

    if not _has_table(inspector, "xiuxian_red_envelope_claims"):
        op.create_table(
            "xiuxian_red_envelope_claims",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("envelope_id", sa.Integer(), sa.ForeignKey("xiuxian_red_envelopes.id", ondelete="CASCADE"), nullable=False),
            sa.Column("tg", sa.BigInteger(), nullable=False),
            sa.Column("amount", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.UniqueConstraint("envelope_id", "tg", name="uq_xiuxian_red_envelope_claim"),
            mysql_charset="utf8mb4",
            mysql_collate="utf8mb4_unicode_ci",
        )

    if not _has_table(inspector, "xiuxian_duel_bet_pools"):
        op.create_table(
            "xiuxian_duel_bet_pools",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("challenger_tg", sa.BigInteger(), nullable=False),
            sa.Column("defender_tg", sa.BigInteger(), nullable=False),
            sa.Column("stake", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("group_chat_id", sa.BigInteger(), nullable=False),
            sa.Column("duel_message_id", sa.Integer(), nullable=True),
            sa.Column("bet_message_id", sa.Integer(), nullable=True),
            sa.Column("bets_close_at", sa.DateTime(), nullable=False),
            sa.Column("resolved", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("winner_tg", sa.BigInteger(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            mysql_charset="utf8mb4",
            mysql_collate="utf8mb4_unicode_ci",
        )

    if not _has_table(inspector, "xiuxian_duel_bets"):
        op.create_table(
            "xiuxian_duel_bets",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("pool_id", sa.Integer(), sa.ForeignKey("xiuxian_duel_bet_pools.id", ondelete="CASCADE"), nullable=False),
            sa.Column("tg", sa.BigInteger(), nullable=False),
            sa.Column("side", sa.String(length=16), nullable=False),
            sa.Column("amount", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.UniqueConstraint("pool_id", "tg", name="uq_xiuxian_duel_bet"),
            mysql_charset="utf8mb4",
            mysql_collate="utf8mb4_unicode_ci",
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    for table_name in [
        "xiuxian_duel_bets",
        "xiuxian_duel_bet_pools",
        "xiuxian_red_envelope_claims",
        "xiuxian_red_envelopes",
        "xiuxian_task_claims",
        "xiuxian_tasks",
        "xiuxian_explorations",
        "xiuxian_scene_drops",
        "xiuxian_scenes",
        "xiuxian_recipe_ingredients",
        "xiuxian_recipes",
        "xiuxian_material_inventory",
        "xiuxian_materials",
        "xiuxian_sect_roles",
        "xiuxian_sects",
    ]:
        if _has_table(inspector, table_name):
            op.drop_table(table_name)

    for column_name in ["robbery_day_key", "robbery_daily_count", "last_salary_claim_at", "sect_role_key", "sect_id"]:
        if _has_column(inspector, "xiuxian_profiles", column_name):
            op.drop_column("xiuxian_profiles", column_name)

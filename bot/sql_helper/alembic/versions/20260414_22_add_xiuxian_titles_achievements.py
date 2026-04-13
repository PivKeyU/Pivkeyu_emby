"""add xiuxian titles and achievements

Revision ID: 20260414_22
Revises: 20260413_21
Create Date: 2026-04-14 09:40:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260414_22"
down_revision = "20260413_21"
branch_labels = None
depends_on = None


def _has_table(inspector, table_name: str) -> bool:
    return table_name in inspector.get_table_names()


def _has_column(inspector, table_name: str, column_name: str) -> bool:
    if not _has_table(inspector, table_name):
        return False
    return any(column.get("name") == column_name for column in inspector.get_columns(table_name))


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    # 迁移按“存在即跳过”的方式执行，兼容重复部署或手动补库后的环境。
    if _has_table(inspector, "xiuxian_profiles") and not _has_column(inspector, "xiuxian_profiles", "current_title_id"):
        with op.batch_alter_table("xiuxian_profiles") as batch_op:
            batch_op.add_column(sa.Column("current_title_id", sa.Integer(), nullable=True))

    if not _has_table(inspector, "xiuxian_titles"):
        op.create_table(
            "xiuxian_titles",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("name", sa.String(length=64), nullable=False, unique=True),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("color", sa.String(length=32), nullable=True),
            sa.Column("image_url", sa.String(length=512), nullable=True),
            sa.Column("attack_bonus", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("defense_bonus", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("bone_bonus", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("comprehension_bonus", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("divine_sense_bonus", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("fortune_bonus", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("qi_blood_bonus", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("true_yuan_bonus", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("body_movement_bonus", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("duel_rate_bonus", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("cultivation_bonus", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("breakthrough_bonus", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("extra_effects", sa.JSON(), nullable=True),
            sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        )

    if not _has_table(inspector, "xiuxian_user_titles"):
        op.create_table(
            "xiuxian_user_titles",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("tg", sa.BigInteger(), nullable=False),
            sa.Column("title_id", sa.Integer(), sa.ForeignKey("xiuxian_titles.id", ondelete="CASCADE"), nullable=False),
            sa.Column("source", sa.String(length=32), nullable=True),
            sa.Column("obtained_note", sa.String(length=255), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.UniqueConstraint("tg", "title_id", name="uq_xiuxian_user_title"),
        )

    if not _has_table(inspector, "xiuxian_achievements"):
        op.create_table(
            "xiuxian_achievements",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("achievement_key", sa.String(length=64), nullable=False, unique=True),
            sa.Column("name", sa.String(length=64), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("metric_key", sa.String(length=64), nullable=False),
            sa.Column("target_value", sa.BigInteger(), nullable=False, server_default="1"),
            sa.Column("reward_config", sa.JSON(), nullable=True),
            sa.Column("notify_group", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("notify_private", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        )

    if not _has_table(inspector, "xiuxian_achievement_progress"):
        op.create_table(
            "xiuxian_achievement_progress",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("tg", sa.BigInteger(), nullable=False),
            sa.Column("metric_key", sa.String(length=64), nullable=False),
            sa.Column("current_value", sa.BigInteger(), nullable=False, server_default="0"),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.UniqueConstraint("tg", "metric_key", name="uq_xiuxian_achievement_progress"),
        )

    if not _has_table(inspector, "xiuxian_user_achievements"):
        op.create_table(
            "xiuxian_user_achievements",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("tg", sa.BigInteger(), nullable=False),
            sa.Column("achievement_id", sa.Integer(), sa.ForeignKey("xiuxian_achievements.id", ondelete="CASCADE"), nullable=False),
            sa.Column("reward_snapshot", sa.JSON(), nullable=True),
            sa.Column("unlocked_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("private_notified_at", sa.DateTime(), nullable=True),
            sa.Column("group_notified_at", sa.DateTime(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.UniqueConstraint("tg", "achievement_id", name="uq_xiuxian_user_achievement"),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    # 回滚时按依赖顺序删除，避免外键和重复删列导致迁移失败。
    if _has_table(inspector, "xiuxian_user_achievements"):
        op.drop_table("xiuxian_user_achievements")

    if _has_table(inspector, "xiuxian_achievement_progress"):
        op.drop_table("xiuxian_achievement_progress")

    if _has_table(inspector, "xiuxian_achievements"):
        op.drop_table("xiuxian_achievements")

    if _has_table(inspector, "xiuxian_user_titles"):
        op.drop_table("xiuxian_user_titles")

    if _has_table(inspector, "xiuxian_titles"):
        op.drop_table("xiuxian_titles")

    if _has_table(inspector, "xiuxian_profiles") and _has_column(inspector, "xiuxian_profiles", "current_title_id"):
        with op.batch_alter_table("xiuxian_profiles") as batch_op:
            batch_op.drop_column("current_title_id")

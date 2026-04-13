"""add xiuxian combat configs

Revision ID: 20260414_23
Revises: 20260414_22
Create Date: 2026-04-14 17:10:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260414_23"
down_revision = "20260414_22"
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

    # 新增字段全部做幂等检查，保证线上重复执行迁移时不会因为列已存在而中断。
    if _has_table(inspector, "xiuxian_techniques") and not _has_column(inspector, "xiuxian_techniques", "combat_config"):
        with op.batch_alter_table("xiuxian_techniques") as batch_op:
            batch_op.add_column(sa.Column("combat_config", sa.JSON(), nullable=True))

    if _has_table(inspector, "xiuxian_artifacts") and not _has_column(inspector, "xiuxian_artifacts", "combat_config"):
        with op.batch_alter_table("xiuxian_artifacts") as batch_op:
            batch_op.add_column(sa.Column("combat_config", sa.JSON(), nullable=True))

    if _has_table(inspector, "xiuxian_talismans") and not _has_column(inspector, "xiuxian_talismans", "combat_config"):
        with op.batch_alter_table("xiuxian_talismans") as batch_op:
            batch_op.add_column(sa.Column("combat_config", sa.JSON(), nullable=True))

    if _has_table(inspector, "xiuxian_explorations") and not _has_column(inspector, "xiuxian_explorations", "outcome_payload"):
        with op.batch_alter_table("xiuxian_explorations") as batch_op:
            batch_op.add_column(sa.Column("outcome_payload", sa.JSON(), nullable=True))

    if _has_table(inspector, "xiuxian_duel_records") and not _has_column(inspector, "xiuxian_duel_records", "battle_log"):
        with op.batch_alter_table("xiuxian_duel_records") as batch_op:
            batch_op.add_column(sa.Column("battle_log", sa.JSON(), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    # 回滚顺序与升级相反，逐列清理战斗配置与战报快照字段。
    if _has_table(inspector, "xiuxian_duel_records") and _has_column(inspector, "xiuxian_duel_records", "battle_log"):
        with op.batch_alter_table("xiuxian_duel_records") as batch_op:
            batch_op.drop_column("battle_log")

    if _has_table(inspector, "xiuxian_explorations") and _has_column(inspector, "xiuxian_explorations", "outcome_payload"):
        with op.batch_alter_table("xiuxian_explorations") as batch_op:
            batch_op.drop_column("outcome_payload")

    if _has_table(inspector, "xiuxian_talismans") and _has_column(inspector, "xiuxian_talismans", "combat_config"):
        with op.batch_alter_table("xiuxian_talismans") as batch_op:
            batch_op.drop_column("combat_config")

    if _has_table(inspector, "xiuxian_artifacts") and _has_column(inspector, "xiuxian_artifacts", "combat_config"):
        with op.batch_alter_table("xiuxian_artifacts") as batch_op:
            batch_op.drop_column("combat_config")

    if _has_table(inspector, "xiuxian_techniques") and _has_column(inspector, "xiuxian_techniques", "combat_config"):
        with op.batch_alter_table("xiuxian_techniques") as batch_op:
            batch_op.drop_column("combat_config")

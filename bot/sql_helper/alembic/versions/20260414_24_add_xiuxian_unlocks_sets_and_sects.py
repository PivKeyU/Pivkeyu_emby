"""add xiuxian unlocks, artifact sets, and sect expansions

Revision ID: 20260414_24
Revises: 20260414_23
Create Date: 2026-04-14 20:30:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260414_24"
down_revision = "20260414_23"
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
    if not _has_table("xiuxian_artifact_sets"):
        op.create_table(
            "xiuxian_artifact_sets",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("name", sa.String(length=64), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("required_count", sa.Integer(), nullable=False, server_default="2"),
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
            sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.UniqueConstraint("name", name="uq_xiuxian_artifact_set_name"),
        )

    if not _has_table("xiuxian_user_recipes"):
        op.create_table(
            "xiuxian_user_recipes",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("tg", sa.BigInteger(), nullable=False),
            sa.Column("recipe_id", sa.Integer(), sa.ForeignKey("xiuxian_recipes.id", ondelete="CASCADE"), nullable=False),
            sa.Column("source", sa.String(length=32), nullable=True),
            sa.Column("obtained_note", sa.String(length=255), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.UniqueConstraint("tg", "recipe_id", name="uq_xiuxian_user_recipe"),
        )

    if not _has_table("xiuxian_user_techniques"):
        op.create_table(
            "xiuxian_user_techniques",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("tg", sa.BigInteger(), nullable=False),
            sa.Column("technique_id", sa.Integer(), sa.ForeignKey("xiuxian_techniques.id", ondelete="CASCADE"), nullable=False),
            sa.Column("source", sa.String(length=32), nullable=True),
            sa.Column("obtained_note", sa.String(length=255), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.UniqueConstraint("tg", "technique_id", name="uq_xiuxian_user_technique"),
        )

    if _has_table("xiuxian_profiles") and not _has_column("xiuxian_profiles", "technique_capacity"):
        with op.batch_alter_table("xiuxian_profiles") as batch_op:
            batch_op.add_column(sa.Column("technique_capacity", sa.Integer(), nullable=False, server_default="3"))

    if _has_table("xiuxian_sects"):
        with op.batch_alter_table("xiuxian_sects") as batch_op:
            if not _has_column("xiuxian_sects", "camp"):
                batch_op.add_column(sa.Column("camp", sa.String(length=16), nullable=False, server_default="orthodox"))
            if not _has_column("xiuxian_sects", "min_bone"):
                batch_op.add_column(sa.Column("min_bone", sa.Integer(), nullable=False, server_default="0"))
            if not _has_column("xiuxian_sects", "min_comprehension"):
                batch_op.add_column(sa.Column("min_comprehension", sa.Integer(), nullable=False, server_default="0"))
            if not _has_column("xiuxian_sects", "min_divine_sense"):
                batch_op.add_column(sa.Column("min_divine_sense", sa.Integer(), nullable=False, server_default="0"))
            if not _has_column("xiuxian_sects", "min_fortune"):
                batch_op.add_column(sa.Column("min_fortune", sa.Integer(), nullable=False, server_default="0"))
            if not _has_column("xiuxian_sects", "attack_bonus"):
                batch_op.add_column(sa.Column("attack_bonus", sa.Integer(), nullable=False, server_default="0"))
            if not _has_column("xiuxian_sects", "defense_bonus"):
                batch_op.add_column(sa.Column("defense_bonus", sa.Integer(), nullable=False, server_default="0"))
            if not _has_column("xiuxian_sects", "duel_rate_bonus"):
                batch_op.add_column(sa.Column("duel_rate_bonus", sa.Integer(), nullable=False, server_default="0"))
            if not _has_column("xiuxian_sects", "cultivation_bonus"):
                batch_op.add_column(sa.Column("cultivation_bonus", sa.Integer(), nullable=False, server_default="0"))
            if not _has_column("xiuxian_sects", "fortune_bonus"):
                batch_op.add_column(sa.Column("fortune_bonus", sa.Integer(), nullable=False, server_default="0"))
            if not _has_column("xiuxian_sects", "body_movement_bonus"):
                batch_op.add_column(sa.Column("body_movement_bonus", sa.Integer(), nullable=False, server_default="0"))
            if not _has_column("xiuxian_sects", "entry_hint"):
                batch_op.add_column(sa.Column("entry_hint", sa.Text(), nullable=True))

    if _has_table("xiuxian_artifacts"):
        with op.batch_alter_table("xiuxian_artifacts") as batch_op:
            if not _has_column("xiuxian_artifacts", "artifact_role"):
                batch_op.add_column(sa.Column("artifact_role", sa.String(length=16), nullable=False, server_default="battle"))
            if not _has_column("xiuxian_artifacts", "equip_slot"):
                batch_op.add_column(sa.Column("equip_slot", sa.String(length=16), nullable=False, server_default="weapon"))
            if not _has_column("xiuxian_artifacts", "artifact_set_id"):
                batch_op.add_column(sa.Column("artifact_set_id", sa.Integer(), sa.ForeignKey("xiuxian_artifact_sets.id", ondelete="SET NULL"), nullable=True))


def downgrade() -> None:
    if _has_table("xiuxian_artifacts"):
        with op.batch_alter_table("xiuxian_artifacts") as batch_op:
            if _has_column("xiuxian_artifacts", "artifact_set_id"):
                batch_op.drop_column("artifact_set_id")
            if _has_column("xiuxian_artifacts", "equip_slot"):
                batch_op.drop_column("equip_slot")
            if _has_column("xiuxian_artifacts", "artifact_role"):
                batch_op.drop_column("artifact_role")

    if _has_table("xiuxian_sects"):
        with op.batch_alter_table("xiuxian_sects") as batch_op:
            if _has_column("xiuxian_sects", "entry_hint"):
                batch_op.drop_column("entry_hint")
            if _has_column("xiuxian_sects", "body_movement_bonus"):
                batch_op.drop_column("body_movement_bonus")
            if _has_column("xiuxian_sects", "fortune_bonus"):
                batch_op.drop_column("fortune_bonus")
            if _has_column("xiuxian_sects", "cultivation_bonus"):
                batch_op.drop_column("cultivation_bonus")
            if _has_column("xiuxian_sects", "duel_rate_bonus"):
                batch_op.drop_column("duel_rate_bonus")
            if _has_column("xiuxian_sects", "defense_bonus"):
                batch_op.drop_column("defense_bonus")
            if _has_column("xiuxian_sects", "attack_bonus"):
                batch_op.drop_column("attack_bonus")
            if _has_column("xiuxian_sects", "min_fortune"):
                batch_op.drop_column("min_fortune")
            if _has_column("xiuxian_sects", "min_divine_sense"):
                batch_op.drop_column("min_divine_sense")
            if _has_column("xiuxian_sects", "min_comprehension"):
                batch_op.drop_column("min_comprehension")
            if _has_column("xiuxian_sects", "min_bone"):
                batch_op.drop_column("min_bone")
            if _has_column("xiuxian_sects", "camp"):
                batch_op.drop_column("camp")

    if _has_table("xiuxian_profiles") and _has_column("xiuxian_profiles", "technique_capacity"):
        with op.batch_alter_table("xiuxian_profiles") as batch_op:
            batch_op.drop_column("technique_capacity")

    if _has_table("xiuxian_user_techniques"):
        op.drop_table("xiuxian_user_techniques")

    if _has_table("xiuxian_user_recipes"):
        op.drop_table("xiuxian_user_recipes")

    if _has_table("xiuxian_artifact_sets"):
        op.drop_table("xiuxian_artifact_sets")

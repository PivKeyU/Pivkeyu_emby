"""add xiuxian attribute system

Revision ID: 20260330_15
Revises: 20260330_14
Create Date: 2026-03-31 00:50:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260330_15"
down_revision = "20260330_14"
branch_labels = None
depends_on = None


def _has_table(inspector, table_name: str) -> bool:
    return table_name in inspector.get_table_names()


def _has_column(inspector, table_name: str, column_name: str) -> bool:
    return column_name in {column["name"] for column in inspector.get_columns(table_name)}


def _add_column_if_missing(inspector, table_name: str, column: sa.Column) -> None:
    if _has_table(inspector, table_name) and not _has_column(inspector, table_name, column.name):
        op.add_column(table_name, column)


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    profile_columns = [
        sa.Column("root_quality", sa.String(length=32), nullable=True),
        sa.Column("root_quality_level", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("root_quality_color", sa.String(length=32), nullable=True),
        sa.Column("bone", sa.Integer(), nullable=False, server_default="12"),
        sa.Column("comprehension", sa.Integer(), nullable=False, server_default="12"),
        sa.Column("divine_sense", sa.Integer(), nullable=False, server_default="12"),
        sa.Column("fortune", sa.Integer(), nullable=False, server_default="12"),
        sa.Column("qi_blood", sa.Integer(), nullable=False, server_default="120"),
        sa.Column("true_yuan", sa.Integer(), nullable=False, server_default="120"),
        sa.Column("body_movement", sa.Integer(), nullable=False, server_default="12"),
        sa.Column("attack_power", sa.Integer(), nullable=False, server_default="12"),
        sa.Column("defense_power", sa.Integer(), nullable=False, server_default="12"),
    ]
    for column in profile_columns:
        _add_column_if_missing(inspector, "xiuxian_profiles", column)

    shared_item_columns = [
        sa.Column("bone_bonus", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("comprehension_bonus", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("divine_sense_bonus", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("fortune_bonus", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("qi_blood_bonus", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("true_yuan_bonus", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("body_movement_bonus", sa.Integer(), nullable=False, server_default="0"),
    ]

    for column in shared_item_columns:
        _add_column_if_missing(inspector, "xiuxian_artifacts", column.copy())
    for column in shared_item_columns:
        _add_column_if_missing(inspector, "xiuxian_pills", column.copy())
    for column in shared_item_columns:
        _add_column_if_missing(inspector, "xiuxian_talismans", column.copy())

    _add_column_if_missing(
        inspector,
        "xiuxian_pills",
        sa.Column("rarity", sa.String(length=32), nullable=False, server_default="凡品"),
    )
    _add_column_if_missing(
        inspector,
        "xiuxian_pills",
        sa.Column("attack_bonus", sa.Integer(), nullable=False, server_default="0"),
    )
    _add_column_if_missing(
        inspector,
        "xiuxian_pills",
        sa.Column("defense_bonus", sa.Integer(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    for table_name in ("xiuxian_artifacts", "xiuxian_pills", "xiuxian_talismans"):
        for column_name in (
            "bone_bonus",
            "comprehension_bonus",
            "divine_sense_bonus",
            "fortune_bonus",
            "qi_blood_bonus",
            "true_yuan_bonus",
            "body_movement_bonus",
        ):
            if _has_table(inspector, table_name) and _has_column(inspector, table_name, column_name):
                op.drop_column(table_name, column_name)

    for column_name in ("attack_bonus", "defense_bonus", "rarity"):
        if _has_table(inspector, "xiuxian_pills") and _has_column(inspector, "xiuxian_pills", column_name):
            op.drop_column("xiuxian_pills", column_name)

    for column_name in (
        "root_quality",
        "root_quality_level",
        "root_quality_color",
        "bone",
        "comprehension",
        "divine_sense",
        "fortune",
        "qi_blood",
        "true_yuan",
        "body_movement",
        "attack_power",
        "defense_power",
    ):
        if _has_table(inspector, "xiuxian_profiles") and _has_column(inspector, "xiuxian_profiles", column_name):
            op.drop_column("xiuxian_profiles", column_name)

"""修仙插件 ORM 模型与数据库读写封装。

定义表结构、序列化器，以及后台和玩法层会直接调用的增删改查函数。
"""

from __future__ import annotations

import copy
import random
import re
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    BigInteger,
    String,
    Text,
    UniqueConstraint,
    or_,
)

from bot.sql_helper import Base, Session
from bot.sql_helper.sql_emby import Emby


REALM_ORDER = ["凡人", "炼气", "筑基", "结丹", "元婴", "化神", "须弥", "芥子", "混元一体"]
FIVE_ELEMENTS = ["金", "木", "水", "火", "土"]
ELEMENT_GENERATES = {"木": "火", "火": "土", "土": "金", "金": "水", "水": "木"}
ELEMENT_CONTROLS = {"木": "土", "土": "水", "水": "火", "火": "金", "金": "木"}
ITEM_KIND_LABELS = {
    "artifact": "法宝",
    "pill": "丹药",
    "talisman": "符箓",
    "material": "材料",
    "technique": "功法",
    "recipe": "配方",
}
DUEL_MODE_LABELS = {
    "standard": "普通斗法",
    "master": "主仆对决",
    "death": "生死斗",
}
ARTIFACT_TYPE_LABELS = {
    "battle": "战斗法宝",
    "support": "辅助法宝",
}
ARTIFACT_ROLE_LABELS = {
    "battle": "攻伐",
    "support": "辅修",
    "guardian": "护身",
    "movement": "身法",
}
ARTIFACT_SLOT_LABELS = {
    "weapon": "武器",
    "chest": "胸甲",
    "legs": "护腿",
    "boots": "靴子",
    "necklace": "项链",
    "ring": "戒指",
    "helmet": "头冠",
    "bracelet": "护腕",
}
SECT_CAMP_LABELS = {
    "orthodox": "正道",
    "heterodox": "邪道",
}
PILL_TYPE_LABELS = {
    "foundation": "突破加成",
    "clear_poison": "解毒",
    "cultivation": "提升修为",
    "stone": "补给灵石",
    "bone": "提升根骨",
    "comprehension": "提升悟性",
    "divine_sense": "提升神识",
    "fortune": "提升机缘",
    "willpower": "提升心志",
    "charisma": "提升魅力",
    "karma": "提升因果",
    "qi_blood": "提升气血",
    "true_yuan": "提升真元",
    "body_movement": "提升身法",
    "attack": "提升攻击",
    "defense": "提升防御",
    "root_refine": "淬炼灵根",
    "root_remold": "重塑灵根",
    "root_single": "洗成单灵根",
    "root_double": "洗成双灵根",
    "root_earth": "洗成地灵根",
    "root_heaven": "洗成天灵根",
    "root_variant": "洗成变异灵根",
}
SECT_ROLE_PRESETS = [
    ("leader", "掌门", 1),
    ("elder", "长老", 2),
    ("core", "真传弟子", 3),
    ("inner_deacon", "内门执事", 4),
    ("outer_deacon", "外门执事", 5),
    ("inner_disciple", "内门弟子", 6),
    ("outer_disciple", "外门弟子", 7),
]
SECT_ROLE_LABELS = {key: label for key, label, _ in SECT_ROLE_PRESETS}
TASK_SCOPE_LABELS = {
    "official": "官方任务",
    "sect": "宗门任务",
    "personal": "个人悬赏",
}
TASK_TYPE_LABELS = {
    "quiz": "答题任务",
    "custom": "自定义任务",
}
TECHNIQUE_TYPE_LABELS = {
    "balanced": "均衡功法",
    "cultivation": "吐纳功法",
    "combat": "斗战功法",
    "attack": "攻伐功法",
    "movement": "身法秘术",
    "defense": "护体功法",
    "divine": "神识秘法",
    "support": "辅修功法",
}
RECIPE_KIND_LABELS = {
    "artifact": "炼制法宝",
    "pill": "炼制丹药",
    "talisman": "炼制符箓",
}
ENVELOPE_MODE_LABELS = {
    "normal": "普通红包",
    "lucky": "拼手气红包",
    "exclusive": "专属红包",
}
DEFAULT_ROOT_QUALITY_VALUE_RULES = {
    "废灵根": {"cultivation_rate": 0.72, "breakthrough_bonus": -8, "combat_factor": 0.92},
    "下品灵根": {"cultivation_rate": 0.88, "breakthrough_bonus": -3, "combat_factor": 0.97},
    "中品灵根": {"cultivation_rate": 1.0, "breakthrough_bonus": 0, "combat_factor": 1.0},
    "上品灵根": {"cultivation_rate": 1.12, "breakthrough_bonus": 3, "combat_factor": 1.05},
    "极品灵根": {"cultivation_rate": 1.24, "breakthrough_bonus": 6, "combat_factor": 1.1},
    "天灵根": {"cultivation_rate": 1.38, "breakthrough_bonus": 12, "combat_factor": 1.16},
    "变异灵根": {"cultivation_rate": 1.3, "breakthrough_bonus": 9, "combat_factor": 1.14},
}
DEFAULT_EXPLORATION_DROP_WEIGHT_RULES = {
    "material_divine_sense_divisor": 5,
    "high_quality_threshold": 4,
    "high_quality_fortune_divisor": 5,
    "high_quality_root_level_start": 3,
}
DEFAULT_ITEM_QUALITY_VALUE_RULES = {
    "凡品": {"artifact_multiplier": 1.0, "pill_multiplier": 1.0, "talisman_multiplier": 1.0},
    "下品": {"artifact_multiplier": 1.0, "pill_multiplier": 1.0, "talisman_multiplier": 1.0},
    "中品": {"artifact_multiplier": 1.0, "pill_multiplier": 1.0, "talisman_multiplier": 1.0},
    "上品": {"artifact_multiplier": 1.0, "pill_multiplier": 1.0, "talisman_multiplier": 1.0},
    "极品": {"artifact_multiplier": 1.0, "pill_multiplier": 1.0, "talisman_multiplier": 1.0},
    "仙品": {"artifact_multiplier": 1.0, "pill_multiplier": 1.0, "talisman_multiplier": 1.0},
    "先天至宝": {"artifact_multiplier": 1.0, "pill_multiplier": 1.0, "talisman_multiplier": 1.0},
}
DEPRECATED_XIUXIAN_SETTING_KEYS = {
    "red_packet_merit_min_stone",
    "red_packet_merit_min_count",
    "red_packet_merit_reward",
    "red_packet_merit_modes",
}
DEFAULT_SETTINGS = {
    "coin_exchange_rate": 100,
    "exchange_fee_percent": 1,
    "min_coin_exchange": 1,
    "message_auto_delete_seconds": 180,
    "equipment_unbind_cost": 100,
    "artifact_plunder_chance": 20,
    "shop_broadcast_cost": 20,
    "official_shop_name": "官方商店",
    "allow_user_task_publish": True,
    "task_publish_cost": 20,
    "artifact_equip_limit": 3,
    "duel_winner_steal_percent": 25,
    "allow_non_admin_image_upload": False,
    "chat_cultivation_chance": 8,
    "chat_cultivation_min_gain": 1,
    "chat_cultivation_max_gain": 3,
    "robbery_daily_limit": 3,
    "robbery_max_steal": 180,
    "high_quality_broadcast_level": 4,
    "root_quality_value_rules": DEFAULT_ROOT_QUALITY_VALUE_RULES,
    "exploration_drop_weight_rules": DEFAULT_EXPLORATION_DROP_WEIGHT_RULES,
    "item_quality_value_rules": DEFAULT_ITEM_QUALITY_VALUE_RULES,
    "immortal_touch_infusion_layers": 1,
    "encounter_spawn_chance": 5,
    "encounter_group_cooldown_minutes": 12,
    "encounter_active_seconds": 90,
    "slave_tribute_percent": 20,
    "slave_challenge_cooldown_hours": 24,
    "sect_salary_min_stay_days": 30,
    "sect_betrayal_cooldown_days": 7,
}
DEFAULT_SETTINGS["duel_bet_minutes"] = 2

QUALITY_LEVEL_LABELS = {
    1: "凡品",
    2: "下品",
    3: "中品",
    4: "上品",
    5: "极品",
    6: "仙品",
    7: "先天至宝",
}
QUALITY_LABEL_LEVELS = {label: level for level, label in QUALITY_LEVEL_LABELS.items()}
QUALITY_LEVEL_COLORS = {
    1: "#9ca3af",
    2: "#22c55e",
    3: "#3b82f6",
    4: "#8b5cf6",
    5: "#f59e0b",
    6: "#ef4444",
    7: "linear-gradient(135deg, #fb7185 0%, #f59e0b 18%, #fde047 36%, #34d399 54%, #60a5fa 72%, #a78bfa 88%, #f472b6 100%)",
}
QUALITY_LEVEL_DESCRIPTIONS = {
    1: "新手过渡基础货，例如破损木剑、粗制丹药。",
    2: "前期主力，可通过简单任务或低级商店稳定获得。",
    3: "中期主力，开始出现基础词条与明显属性加成。",
    4: "后期主力，通常拥有 1-2 个实用词条或特效。",
    5: "毕业级物品，固定拥有强力特效或完整战斗定位。",
    6: "传说级稀有物，往往与事件、榜单或极低概率掉落绑定。",
    7: "神话级至宝，通常具备唯一机制或全服级稀有度。",
}
QUALITY_LEVEL_FEATURES = {
    1: "无词条或单一基础词条",
    2: "单一基础词条，数值稳定",
    3: "1 个属性词条，可能带低阶特效",
    4: "1-2 个实用词条，开始出现百分比或机制词条",
    5: "固定强词条或核心特效",
    6: "强力特效，可能改变玩法节奏",
    7: "唯一机制、套装或事件级特效",
}
MATERIAL_QUALITY_NOTES = {
    1: "常见基础灵材，适合入门炼制、任务收集与日常积累。",
    2: "灵性稳定的常备材料，足以支撑前中期常规配方。",
    3: "已具明显灵韵，可作为中阶丹器符配方的主辅材料。",
    4: "材质精纯、灵息凝实，常用于高阶炼制与精修。",
    5: "珍稀核心灵材，往往决定成品的上限与方向。",
    6: "传说层次的异材，多见于险地奇遇、榜单奖励或古修遗藏。",
    7: "天材地宝级重宝，足以左右顶级炼制与机缘布局。",
}
PILL_TYPE_LABELS = {
    "foundation": "突破加成",
    "clear_poison": "解毒",
    "cultivation": "提升修为",
    "stone": "补给灵石",
    "bone": "提升根骨",
    "comprehension": "提升悟性",
    "divine_sense": "提升神识",
    "fortune": "提升机缘",
    "willpower": "提升心志",
    "charisma": "提升魅力",
    "karma": "提升因果",
    "qi_blood": "提升气血",
    "true_yuan": "提升真元",
    "body_movement": "提升身法",
    "attack": "提升攻击",
    "defense": "提升防御",
    "root_refine": "淬炼灵根",
    "root_remold": "重塑灵根",
    "root_single": "洗成单灵根",
    "root_double": "洗成双灵根",
    "root_earth": "洗成地灵根",
    "root_heaven": "洗成天灵根",
    "root_variant": "洗成变异灵根",
}
PILL_EFFECT_VALUE_LABELS = {
    "foundation": "突破增幅",
    "clear_poison": "解毒值",
    "cultivation": "修为增量",
    "stone": "灵石增量",
    "bone": "根骨增量",
    "comprehension": "悟性增量",
    "divine_sense": "神识增量",
    "fortune": "机缘增量",
    "willpower": "心志增量",
    "charisma": "魅力增量",
    "karma": "因果增量",
    "qi_blood": "气血增量",
    "true_yuan": "真元增量",
    "body_movement": "身法增量",
    "attack": "攻击增量",
    "defense": "防御增量",
    "root_refine": "淬灵阶数",
    "root_remold": "保底品阶",
    "root_single": "保底品阶",
    "root_double": "保底品阶",
    "root_earth": "效果值未用",
    "root_heaven": "效果值未用",
    "root_variant": "效果值未用",
}


def list_pill_type_options() -> list[dict[str, str]]:
    # 管理页丹药类型统一以后端定义为准，避免前端写死后升级不生效。
    return [
        {
            "value": key,
            "label": label,
            "effect": PILL_EFFECT_VALUE_LABELS.get(key, "主效果"),
        }
        for key, label in PILL_TYPE_LABELS.items()
    ]
ATTRIBUTE_LABELS = {
    "bone_bonus": "根骨",
    "comprehension_bonus": "悟性",
    "divine_sense_bonus": "神识",
    "fortune_bonus": "机缘",
    "willpower_bonus": "心志",
    "charisma_bonus": "魅力",
    "karma_bonus": "因果",
    "qi_blood_bonus": "气血",
    "true_yuan_bonus": "真元",
    "body_movement_bonus": "身法",
    "attack_bonus": "攻击",
    "defense_bonus": "防御",
}
ATTRIBUTE_EFFECT_HINTS = {
    "bone": "影响吐纳收益、丹毒抗性与气血底子",
    "comprehension": "影响吐纳收益、炼制与突破把握",
    "divine_sense": "影响秘境判断、掉落权重与斗法洞察",
    "fortune": "影响奇遇、夺宝与高品质掉落",
    "willpower": "影响突破成功率与持久战韧性",
    "charisma": "影响坊市广播折扣与部分身份门槛",
    "karma": "影响高风险机缘与斗法综合评价",
    "qi_blood": "影响斗法耐久上限",
    "true_yuan": "影响斗法技能续航",
    "body_movement": "影响斗法闪避与身法门槛",
    "attack_power": "影响斗法输出",
    "defense_power": "影响斗法承伤",
}
ROOT_QUALITY_LEVELS = {
    "废灵根": 1,
    "下品灵根": 2,
    "中品灵根": 3,
    "上品灵根": 4,
    "极品灵根": 5,
    "天灵根": 6,
    "变异灵根": 7,
}
ROOT_QUALITY_COLORS = {
    "废灵根": "#6b7280",
    "下品灵根": "#22c55e",
    "中品灵根": "#3b82f6",
    "上品灵根": "#8b5cf6",
    "极品灵根": "#f59e0b",
    "天灵根": "#ef4444",
    "变异灵根": "#ec4899",
}
ROOT_VARIANT_ELEMENTS = ["雷", "风"]
SHANGHAI_TZ = timezone(timedelta(hours=8))
UTC_TZ = timezone.utc


def utcnow() -> datetime:
    return datetime.utcnow()


def shanghai_now() -> datetime:
    return datetime.now(SHANGHAI_TZ)


def serialize_datetime(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC_TZ)
    return value.astimezone(SHANGHAI_TZ).isoformat()


def normalize_realm_stage(stage: str | None) -> str:
    raw = str(stage or "").strip()
    if not raw:
        return "凡人"
    aliases = {
        "练气": "炼气",
    }
    return aliases.get(raw, raw)


def normalize_quality_level(level: int | str | None) -> int:
    if isinstance(level, str):
        level = QUALITY_LABEL_LEVELS.get(level.strip(), level)
    try:
        value = int(level or 1)
    except (TypeError, ValueError):
        value = 1
    return max(1, min(value, max(QUALITY_LEVEL_LABELS)))


def normalize_quality_label(label: str | None) -> str:
    level = normalize_quality_level(label or QUALITY_LEVEL_LABELS[1])
    return QUALITY_LEVEL_LABELS[level]


def get_quality_meta(level_or_label: int | str | None) -> dict[str, Any]:
    level = normalize_quality_level(level_or_label)
    return {
        "level": level,
        "label": QUALITY_LEVEL_LABELS[level],
        "color": QUALITY_LEVEL_COLORS.get(level, "#9ca3af"),
        "description": QUALITY_LEVEL_DESCRIPTIONS.get(level, ""),
        "feature": QUALITY_LEVEL_FEATURES.get(level, ""),
    }


class XiuxianSetting(Base):
    __tablename__ = "xiuxian_settings"

    setting_key = Column(String(64), primary_key=True)
    setting_value = Column(JSON, nullable=True)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)


class XiuxianImageUploadPermission(Base):
    __tablename__ = "xiuxian_image_upload_permissions"

    tg = Column(BigInteger, primary_key=True, autoincrement=False)
    created_at = Column(DateTime, default=utcnow, nullable=False)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)


class XiuxianProfile(Base):
    __tablename__ = "xiuxian_profiles"

    tg = Column(BigInteger, primary_key=True, autoincrement=False)
    display_name = Column(String(128), nullable=True)
    username = Column(String(64), nullable=True)
    consented = Column(Boolean, default=False, nullable=False)
    root_type = Column(String(32), nullable=True)
    root_primary = Column(String(8), nullable=True)
    root_secondary = Column(String(8), nullable=True)
    root_relation = Column(String(16), nullable=True)
    root_bonus = Column(Integer, default=0, nullable=False)
    root_quality = Column(String(32), nullable=True)
    root_quality_level = Column(Integer, default=1, nullable=False)
    root_quality_color = Column(String(32), nullable=True)
    realm_stage = Column(String(32), default="凡人", nullable=False)
    realm_layer = Column(Integer, default=0, nullable=False)
    cultivation = Column(Integer, default=0, nullable=False)
    spiritual_stone = Column(Integer, default=0, nullable=False)
    bone = Column(Integer, default=12, nullable=False)
    comprehension = Column(Integer, default=12, nullable=False)
    divine_sense = Column(Integer, default=12, nullable=False)
    fortune = Column(Integer, default=12, nullable=False)
    willpower = Column(Integer, default=10, nullable=False)
    charisma = Column(Integer, default=10, nullable=False)
    karma = Column(Integer, default=10, nullable=False)
    qi_blood = Column(Integer, default=120, nullable=False)
    true_yuan = Column(Integer, default=120, nullable=False)
    body_movement = Column(Integer, default=12, nullable=False)
    attack_power = Column(Integer, default=12, nullable=False)
    defense_power = Column(Integer, default=12, nullable=False)
    insight_bonus = Column(Integer, default=0, nullable=False)
    sect_contribution = Column(Integer, default=0, nullable=False)
    dan_poison = Column(Integer, default=0, nullable=False)
    breakthrough_pill_uses = Column(Integer, default=0, nullable=False)
    sect_id = Column(Integer, nullable=True)
    sect_role_key = Column(String(32), nullable=True)
    last_salary_claim_at = Column(DateTime, nullable=True)
    sect_joined_at = Column(DateTime, nullable=True)
    sect_betrayal_until = Column(DateTime, nullable=True)
    master_tg = Column(BigInteger, nullable=True)
    servitude_started_at = Column(DateTime, nullable=True)
    servitude_challenge_available_at = Column(DateTime, nullable=True)
    death_at = Column(DateTime, nullable=True)
    rebirth_count = Column(Integer, default=0, nullable=False)
    robbery_daily_count = Column(Integer, default=0, nullable=False)
    robbery_day_key = Column(String(16), nullable=True)
    current_artifact_id = Column(Integer, nullable=True)
    active_talisman_id = Column(Integer, nullable=True)
    current_technique_id = Column(Integer, nullable=True)
    current_title_id = Column(Integer, nullable=True)
    technique_capacity = Column(Integer, default=3, nullable=False)
    shop_name = Column(String(64), nullable=True)
    shop_broadcast = Column(Boolean, default=False, nullable=False)
    last_train_at = Column(DateTime, nullable=True)
    retreat_started_at = Column(DateTime, nullable=True)
    retreat_end_at = Column(DateTime, nullable=True)
    retreat_gain_per_minute = Column(Integer, default=0, nullable=False)
    retreat_cost_per_minute = Column(Integer, default=0, nullable=False)
    retreat_minutes_total = Column(Integer, default=0, nullable=False)
    retreat_minutes_resolved = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, default=utcnow, nullable=False)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)


class XiuxianJournal(Base):
    __tablename__ = "xiuxian_journals"

    id = Column(Integer, primary_key=True, autoincrement=True)
    tg = Column(BigInteger, nullable=False)
    action_type = Column(String(32), nullable=False)
    title = Column(String(128), nullable=False)
    detail = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utcnow, nullable=False)


class XiuxianTitle(Base):
    __tablename__ = "xiuxian_titles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(64), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    color = Column(String(32), nullable=True)
    image_url = Column(String(512), nullable=True)
    attack_bonus = Column(Integer, default=0, nullable=False)
    defense_bonus = Column(Integer, default=0, nullable=False)
    bone_bonus = Column(Integer, default=0, nullable=False)
    comprehension_bonus = Column(Integer, default=0, nullable=False)
    divine_sense_bonus = Column(Integer, default=0, nullable=False)
    fortune_bonus = Column(Integer, default=0, nullable=False)
    qi_blood_bonus = Column(Integer, default=0, nullable=False)
    true_yuan_bonus = Column(Integer, default=0, nullable=False)
    body_movement_bonus = Column(Integer, default=0, nullable=False)
    duel_rate_bonus = Column(Integer, default=0, nullable=False)
    cultivation_bonus = Column(Integer, default=0, nullable=False)
    breakthrough_bonus = Column(Integer, default=0, nullable=False)
    extra_effects = Column(JSON, nullable=True)
    enabled = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=utcnow, nullable=False)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)


class XiuxianUserTitle(Base):
    __tablename__ = "xiuxian_user_titles"
    __table_args__ = (UniqueConstraint("tg", "title_id", name="uq_xiuxian_user_title"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    tg = Column(BigInteger, nullable=False)
    title_id = Column(Integer, ForeignKey("xiuxian_titles.id", ondelete="CASCADE"), nullable=False)
    source = Column(String(32), nullable=True)
    obtained_note = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=utcnow, nullable=False)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)


class XiuxianAchievement(Base):
    __tablename__ = "xiuxian_achievements"

    id = Column(Integer, primary_key=True, autoincrement=True)
    achievement_key = Column(String(64), nullable=False, unique=True)
    name = Column(String(64), nullable=False)
    description = Column(Text, nullable=True)
    metric_key = Column(String(64), nullable=False)
    target_value = Column(BigInteger, default=1, nullable=False)
    reward_config = Column(JSON, nullable=True)
    notify_group = Column(Boolean, default=True, nullable=False)
    notify_private = Column(Boolean, default=True, nullable=False)
    enabled = Column(Boolean, default=True, nullable=False)
    sort_order = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, default=utcnow, nullable=False)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)


class XiuxianAchievementProgress(Base):
    __tablename__ = "xiuxian_achievement_progress"
    __table_args__ = (UniqueConstraint("tg", "metric_key", name="uq_xiuxian_achievement_progress"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    tg = Column(BigInteger, nullable=False)
    metric_key = Column(String(64), nullable=False)
    current_value = Column(BigInteger, default=0, nullable=False)
    created_at = Column(DateTime, default=utcnow, nullable=False)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)


class XiuxianUserAchievement(Base):
    __tablename__ = "xiuxian_user_achievements"
    __table_args__ = (UniqueConstraint("tg", "achievement_id", name="uq_xiuxian_user_achievement"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    tg = Column(BigInteger, nullable=False)
    achievement_id = Column(Integer, ForeignKey("xiuxian_achievements.id", ondelete="CASCADE"), nullable=False)
    reward_snapshot = Column(JSON, nullable=True)
    unlocked_at = Column(DateTime, default=utcnow, nullable=False)
    private_notified_at = Column(DateTime, nullable=True)
    group_notified_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)


class XiuxianSect(Base):
    __tablename__ = "xiuxian_sects"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(64), nullable=False, unique=True)
    camp = Column(String(16), default="orthodox", nullable=False)
    description = Column(Text, nullable=True)
    image_url = Column(String(512), nullable=True)
    min_realm_stage = Column(String(32), nullable=True)
    min_realm_layer = Column(Integer, default=1, nullable=False)
    min_stone = Column(Integer, default=0, nullable=False)
    min_bone = Column(Integer, default=0, nullable=False)
    min_comprehension = Column(Integer, default=0, nullable=False)
    min_divine_sense = Column(Integer, default=0, nullable=False)
    min_fortune = Column(Integer, default=0, nullable=False)
    min_willpower = Column(Integer, default=0, nullable=False)
    min_charisma = Column(Integer, default=0, nullable=False)
    min_karma = Column(Integer, default=0, nullable=False)
    min_body_movement = Column(Integer, default=0, nullable=False)
    min_combat_power = Column(Integer, default=0, nullable=False)
    attack_bonus = Column(Integer, default=0, nullable=False)
    defense_bonus = Column(Integer, default=0, nullable=False)
    duel_rate_bonus = Column(Integer, default=0, nullable=False)
    cultivation_bonus = Column(Integer, default=0, nullable=False)
    fortune_bonus = Column(Integer, default=0, nullable=False)
    body_movement_bonus = Column(Integer, default=0, nullable=False)
    entry_hint = Column(Text, nullable=True)
    enabled = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=utcnow, nullable=False)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)


class XiuxianSectRole(Base):
    __tablename__ = "xiuxian_sect_roles"
    __table_args__ = (UniqueConstraint("sect_id", "role_key", name="uq_xiuxian_sect_role_key"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    sect_id = Column(Integer, ForeignKey("xiuxian_sects.id", ondelete="CASCADE"), nullable=False)
    role_key = Column(String(32), nullable=False)
    role_name = Column(String(64), nullable=False)
    attack_bonus = Column(Integer, default=0, nullable=False)
    defense_bonus = Column(Integer, default=0, nullable=False)
    duel_rate_bonus = Column(Integer, default=0, nullable=False)
    cultivation_bonus = Column(Integer, default=0, nullable=False)
    monthly_salary = Column(Integer, default=0, nullable=False)
    can_publish_tasks = Column(Boolean, default=False, nullable=False)
    sort_order = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, default=utcnow, nullable=False)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)


class XiuxianMaterial(Base):
    __tablename__ = "xiuxian_materials"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(64), nullable=False, unique=True)
    quality_level = Column(Integer, default=1, nullable=False)
    image_url = Column(String(512), nullable=True)
    description = Column(Text, nullable=True)
    enabled = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=utcnow, nullable=False)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)


class XiuxianMaterialInventory(Base):
    __tablename__ = "xiuxian_material_inventory"
    __table_args__ = (UniqueConstraint("tg", "material_id", name="uq_xiuxian_material_inventory"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    tg = Column(BigInteger, nullable=False)
    material_id = Column(Integer, ForeignKey("xiuxian_materials.id", ondelete="CASCADE"), nullable=False)
    quantity = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, default=utcnow, nullable=False)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)


class XiuxianRecipe(Base):
    __tablename__ = "xiuxian_recipes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(64), nullable=False, unique=True)
    recipe_kind = Column(String(16), nullable=False)
    result_kind = Column(String(16), nullable=False)
    result_ref_id = Column(Integer, nullable=False)
    result_quantity = Column(Integer, default=1, nullable=False)
    base_success_rate = Column(Integer, default=60, nullable=False)
    broadcast_on_success = Column(Boolean, default=False, nullable=False)
    enabled = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=utcnow, nullable=False)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)


class XiuxianUserRecipe(Base):
    __tablename__ = "xiuxian_user_recipes"
    __table_args__ = (UniqueConstraint("tg", "recipe_id", name="uq_xiuxian_user_recipe"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    tg = Column(BigInteger, nullable=False)
    recipe_id = Column(Integer, ForeignKey("xiuxian_recipes.id", ondelete="CASCADE"), nullable=False)
    source = Column(String(32), nullable=True)
    obtained_note = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=utcnow, nullable=False)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)


class XiuxianRecipeIngredient(Base):
    __tablename__ = "xiuxian_recipe_ingredients"

    id = Column(Integer, primary_key=True, autoincrement=True)
    recipe_id = Column(Integer, ForeignKey("xiuxian_recipes.id", ondelete="CASCADE"), nullable=False)
    material_id = Column(Integer, ForeignKey("xiuxian_materials.id", ondelete="CASCADE"), nullable=False)
    quantity = Column(Integer, default=1, nullable=False)
    created_at = Column(DateTime, default=utcnow, nullable=False)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)


class XiuxianScene(Base):
    __tablename__ = "xiuxian_scenes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(64), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    image_url = Column(String(512), nullable=True)
    max_minutes = Column(Integer, default=60, nullable=False)
    min_realm_stage = Column(String(32), nullable=True)
    min_realm_layer = Column(Integer, default=1, nullable=False)
    min_combat_power = Column(Integer, default=0, nullable=False)
    event_pool = Column(JSON, nullable=True)
    enabled = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=utcnow, nullable=False)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)


class XiuxianSceneDrop(Base):
    __tablename__ = "xiuxian_scene_drops"

    id = Column(Integer, primary_key=True, autoincrement=True)
    scene_id = Column(Integer, ForeignKey("xiuxian_scenes.id", ondelete="CASCADE"), nullable=False)
    reward_kind = Column(String(16), nullable=False)
    reward_ref_id = Column(Integer, nullable=True)
    quantity_min = Column(Integer, default=1, nullable=False)
    quantity_max = Column(Integer, default=1, nullable=False)
    weight = Column(Integer, default=1, nullable=False)
    stone_reward = Column(Integer, default=0, nullable=False)
    event_text = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utcnow, nullable=False)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)


class XiuxianExploration(Base):
    __tablename__ = "xiuxian_explorations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    tg = Column(BigInteger, nullable=False)
    scene_id = Column(Integer, ForeignKey("xiuxian_scenes.id", ondelete="CASCADE"), nullable=False)
    started_at = Column(DateTime, default=utcnow, nullable=False)
    end_at = Column(DateTime, nullable=False)
    claimed = Column(Boolean, default=False, nullable=False)
    reward_kind = Column(String(16), nullable=True)
    reward_ref_id = Column(Integer, nullable=True)
    reward_quantity = Column(Integer, default=0, nullable=False)
    stone_reward = Column(Integer, default=0, nullable=False)
    event_text = Column(Text, nullable=True)
    outcome_payload = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=utcnow, nullable=False)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)


class XiuxianTask(Base):
    __tablename__ = "xiuxian_tasks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(128), nullable=False)
    description = Column(Text, nullable=True)
    task_scope = Column(String(16), nullable=False)
    task_type = Column(String(16), default="quiz", nullable=False)
    owner_tg = Column(BigInteger, nullable=True)
    sect_id = Column(Integer, nullable=True)
    question_text = Column(Text, nullable=True)
    answer_text = Column(String(255), nullable=True)
    image_url = Column(String(512), nullable=True)
    required_item_kind = Column(String(16), nullable=True)
    required_item_ref_id = Column(Integer, nullable=True)
    required_item_quantity = Column(Integer, default=0, nullable=False)
    reward_stone = Column(Integer, default=0, nullable=False)
    reward_item_kind = Column(String(16), nullable=True)
    reward_item_ref_id = Column(Integer, nullable=True)
    reward_item_quantity = Column(Integer, default=0, nullable=False)
    max_claimants = Column(Integer, default=1, nullable=False)
    claimants_count = Column(Integer, default=0, nullable=False)
    active_in_group = Column(Boolean, default=False, nullable=False)
    group_chat_id = Column(BigInteger, nullable=True)
    group_message_id = Column(Integer, nullable=True)
    winner_tg = Column(BigInteger, nullable=True)
    enabled = Column(Boolean, default=True, nullable=False)
    status = Column(String(16), default="open", nullable=False)
    deadline_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utcnow, nullable=False)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)


class XiuxianTaskClaim(Base):
    __tablename__ = "xiuxian_task_claims"
    __table_args__ = (UniqueConstraint("task_id", "tg", name="uq_xiuxian_task_claim"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(Integer, ForeignKey("xiuxian_tasks.id", ondelete="CASCADE"), nullable=False)
    tg = Column(BigInteger, nullable=False)
    status = Column(String(16), default="accepted", nullable=False)
    submitted_answer = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=utcnow, nullable=False)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)


class XiuxianEncounterTemplate(Base):
    __tablename__ = "xiuxian_encounter_templates"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(128), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    image_url = Column(String(512), nullable=True)
    button_text = Column(String(64), nullable=True)
    success_text = Column(Text, nullable=True)
    broadcast_text = Column(Text, nullable=True)
    weight = Column(Integer, default=1, nullable=False)
    active_seconds = Column(Integer, default=90, nullable=False)
    min_realm_stage = Column(String(32), nullable=True)
    min_realm_layer = Column(Integer, default=1, nullable=False)
    min_combat_power = Column(Integer, default=0, nullable=False)
    reward_stone_min = Column(Integer, default=0, nullable=False)
    reward_stone_max = Column(Integer, default=0, nullable=False)
    reward_cultivation_min = Column(Integer, default=0, nullable=False)
    reward_cultivation_max = Column(Integer, default=0, nullable=False)
    reward_item_kind = Column(String(16), nullable=True)
    reward_item_ref_id = Column(Integer, nullable=True)
    reward_item_quantity_min = Column(Integer, default=1, nullable=False)
    reward_item_quantity_max = Column(Integer, default=1, nullable=False)
    reward_willpower = Column(Integer, default=0, nullable=False)
    reward_charisma = Column(Integer, default=0, nullable=False)
    reward_karma = Column(Integer, default=0, nullable=False)
    enabled = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=utcnow, nullable=False)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)


class XiuxianEncounterInstance(Base):
    __tablename__ = "xiuxian_encounter_instances"

    id = Column(Integer, primary_key=True, autoincrement=True)
    template_id = Column(Integer, ForeignKey("xiuxian_encounter_templates.id", ondelete="SET NULL"), nullable=True)
    template_name = Column(String(128), nullable=False)
    group_chat_id = Column(BigInteger, nullable=False)
    message_id = Column(Integer, nullable=True)
    button_text = Column(String(64), nullable=True)
    status = Column(String(16), default="active", nullable=False)
    reward_payload = Column(JSON, nullable=True)
    expires_at = Column(DateTime, nullable=False)
    claimer_tg = Column(BigInteger, nullable=True)
    claimed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utcnow, nullable=False)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)


class XiuxianRedEnvelope(Base):
    __tablename__ = "xiuxian_red_envelopes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    creator_tg = Column(BigInteger, nullable=False)
    cover_text = Column(String(255), nullable=True)
    image_url = Column(String(512), nullable=True)
    mode = Column(String(16), nullable=False)
    target_tg = Column(BigInteger, nullable=True)
    amount_total = Column(Integer, default=0, nullable=False)
    count_total = Column(Integer, default=1, nullable=False)
    remaining_amount = Column(Integer, default=0, nullable=False)
    remaining_count = Column(Integer, default=0, nullable=False)
    status = Column(String(16), default="active", nullable=False)
    group_chat_id = Column(BigInteger, nullable=True)
    message_id = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=utcnow, nullable=False)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)


class XiuxianRedEnvelopeClaim(Base):
    __tablename__ = "xiuxian_red_envelope_claims"
    __table_args__ = (UniqueConstraint("envelope_id", "tg", name="uq_xiuxian_red_envelope_claim"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    envelope_id = Column(Integer, ForeignKey("xiuxian_red_envelopes.id", ondelete="CASCADE"), nullable=False)
    tg = Column(BigInteger, nullable=False)
    amount = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, default=utcnow, nullable=False)


class XiuxianDuelBetPool(Base):
    __tablename__ = "xiuxian_duel_bet_pools"

    id = Column(Integer, primary_key=True, autoincrement=True)
    challenger_tg = Column(BigInteger, nullable=False)
    defender_tg = Column(BigInteger, nullable=False)
    stake = Column(Integer, default=0, nullable=False)
    group_chat_id = Column(BigInteger, nullable=False)
    duel_message_id = Column(Integer, nullable=True)
    bet_message_id = Column(Integer, nullable=True)
    duel_mode = Column(String(16), default="standard", nullable=False)
    bets_close_at = Column(DateTime, nullable=False)
    resolved = Column(Boolean, default=False, nullable=False)
    winner_tg = Column(BigInteger, nullable=True)
    created_at = Column(DateTime, default=utcnow, nullable=False)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)


class XiuxianDuelBet(Base):
    __tablename__ = "xiuxian_duel_bets"
    __table_args__ = (UniqueConstraint("pool_id", "tg", name="uq_xiuxian_duel_bet"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    pool_id = Column(Integer, ForeignKey("xiuxian_duel_bet_pools.id", ondelete="CASCADE"), nullable=False)
    tg = Column(BigInteger, nullable=False)
    side = Column(String(16), nullable=False)
    amount = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, default=utcnow, nullable=False)


class XiuxianTechnique(Base):
    __tablename__ = "xiuxian_techniques"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(64), nullable=False, unique=True)
    rarity = Column(String(32), default="凡品", nullable=False)
    technique_type = Column(String(16), default="balanced", nullable=False)
    image_url = Column(String(512), nullable=True)
    description = Column(Text, nullable=True)
    attack_bonus = Column(Integer, default=0, nullable=False)
    defense_bonus = Column(Integer, default=0, nullable=False)
    bone_bonus = Column(Integer, default=0, nullable=False)
    comprehension_bonus = Column(Integer, default=0, nullable=False)
    divine_sense_bonus = Column(Integer, default=0, nullable=False)
    fortune_bonus = Column(Integer, default=0, nullable=False)
    qi_blood_bonus = Column(Integer, default=0, nullable=False)
    true_yuan_bonus = Column(Integer, default=0, nullable=False)
    body_movement_bonus = Column(Integer, default=0, nullable=False)
    duel_rate_bonus = Column(Integer, default=0, nullable=False)
    cultivation_bonus = Column(Integer, default=0, nullable=False)
    breakthrough_bonus = Column(Integer, default=0, nullable=False)
    combat_config = Column(JSON, nullable=True)
    min_realm_stage = Column(String(32), nullable=True)
    min_realm_layer = Column(Integer, default=1, nullable=False)
    enabled = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=utcnow, nullable=False)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)


class XiuxianUserTechnique(Base):
    __tablename__ = "xiuxian_user_techniques"
    __table_args__ = (UniqueConstraint("tg", "technique_id", name="uq_xiuxian_user_technique"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    tg = Column(BigInteger, nullable=False)
    technique_id = Column(Integer, ForeignKey("xiuxian_techniques.id", ondelete="CASCADE"), nullable=False)
    source = Column(String(32), nullable=True)
    obtained_note = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=utcnow, nullable=False)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)


class XiuxianArtifactSet(Base):
    __tablename__ = "xiuxian_artifact_sets"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(64), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    required_count = Column(Integer, default=2, nullable=False)
    attack_bonus = Column(Integer, default=0, nullable=False)
    defense_bonus = Column(Integer, default=0, nullable=False)
    bone_bonus = Column(Integer, default=0, nullable=False)
    comprehension_bonus = Column(Integer, default=0, nullable=False)
    divine_sense_bonus = Column(Integer, default=0, nullable=False)
    fortune_bonus = Column(Integer, default=0, nullable=False)
    qi_blood_bonus = Column(Integer, default=0, nullable=False)
    true_yuan_bonus = Column(Integer, default=0, nullable=False)
    body_movement_bonus = Column(Integer, default=0, nullable=False)
    duel_rate_bonus = Column(Integer, default=0, nullable=False)
    cultivation_bonus = Column(Integer, default=0, nullable=False)
    breakthrough_bonus = Column(Integer, default=0, nullable=False)
    enabled = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=utcnow, nullable=False)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)


class XiuxianArtifact(Base):
    __tablename__ = "xiuxian_artifacts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(64), nullable=False, unique=True)
    rarity = Column(String(32), default="凡品", nullable=False)
    image_url = Column(String(512), nullable=True)
    description = Column(Text, nullable=True)
    attack_bonus = Column(Integer, default=0, nullable=False)
    defense_bonus = Column(Integer, default=0, nullable=False)
    bone_bonus = Column(Integer, default=0, nullable=False)
    comprehension_bonus = Column(Integer, default=0, nullable=False)
    divine_sense_bonus = Column(Integer, default=0, nullable=False)
    fortune_bonus = Column(Integer, default=0, nullable=False)
    qi_blood_bonus = Column(Integer, default=0, nullable=False)
    true_yuan_bonus = Column(Integer, default=0, nullable=False)
    body_movement_bonus = Column(Integer, default=0, nullable=False)
    artifact_type = Column(String(16), default="battle", nullable=False)
    artifact_role = Column(String(16), default="battle", nullable=False)
    equip_slot = Column(String(16), default="weapon", nullable=False)
    artifact_set_id = Column(Integer, ForeignKey("xiuxian_artifact_sets.id", ondelete="SET NULL"), nullable=True)
    duel_rate_bonus = Column(Integer, default=0, nullable=False)
    cultivation_bonus = Column(Integer, default=0, nullable=False)
    combat_config = Column(JSON, nullable=True)
    min_realm_stage = Column(String(32), nullable=True)
    min_realm_layer = Column(Integer, default=1, nullable=False)
    enabled = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=utcnow, nullable=False)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)


class XiuxianPill(Base):
    __tablename__ = "xiuxian_pills"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(64), nullable=False, unique=True)
    rarity = Column(String(32), default="凡品", nullable=False)
    pill_type = Column(String(32), nullable=False)
    image_url = Column(String(512), nullable=True)
    description = Column(Text, nullable=True)
    effect_value = Column(Integer, default=0, nullable=False)
    poison_delta = Column(Integer, default=0, nullable=False)
    attack_bonus = Column(Integer, default=0, nullable=False)
    defense_bonus = Column(Integer, default=0, nullable=False)
    bone_bonus = Column(Integer, default=0, nullable=False)
    comprehension_bonus = Column(Integer, default=0, nullable=False)
    divine_sense_bonus = Column(Integer, default=0, nullable=False)
    fortune_bonus = Column(Integer, default=0, nullable=False)
    qi_blood_bonus = Column(Integer, default=0, nullable=False)
    true_yuan_bonus = Column(Integer, default=0, nullable=False)
    body_movement_bonus = Column(Integer, default=0, nullable=False)
    min_realm_stage = Column(String(32), nullable=True)
    min_realm_layer = Column(Integer, default=1, nullable=False)
    enabled = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=utcnow, nullable=False)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)


class XiuxianTalisman(Base):
    __tablename__ = "xiuxian_talismans"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(64), nullable=False, unique=True)
    rarity = Column(String(32), default="凡品", nullable=False)
    image_url = Column(String(512), nullable=True)
    description = Column(Text, nullable=True)
    attack_bonus = Column(Integer, default=0, nullable=False)
    defense_bonus = Column(Integer, default=0, nullable=False)
    bone_bonus = Column(Integer, default=0, nullable=False)
    comprehension_bonus = Column(Integer, default=0, nullable=False)
    divine_sense_bonus = Column(Integer, default=0, nullable=False)
    fortune_bonus = Column(Integer, default=0, nullable=False)
    qi_blood_bonus = Column(Integer, default=0, nullable=False)
    true_yuan_bonus = Column(Integer, default=0, nullable=False)
    body_movement_bonus = Column(Integer, default=0, nullable=False)
    duel_rate_bonus = Column(Integer, default=0, nullable=False)
    effect_uses = Column(Integer, default=1, nullable=False)
    combat_config = Column(JSON, nullable=True)
    min_realm_stage = Column(String(32), nullable=True)
    min_realm_layer = Column(Integer, default=1, nullable=False)
    enabled = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=utcnow, nullable=False)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)


class XiuxianArtifactInventory(Base):
    __tablename__ = "xiuxian_artifact_inventory"
    __table_args__ = (UniqueConstraint("tg", "artifact_id", name="uq_xiuxian_artifact_inventory"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    tg = Column(BigInteger, nullable=False)
    artifact_id = Column(Integer, ForeignKey("xiuxian_artifacts.id", ondelete="CASCADE"), nullable=False)
    quantity = Column(Integer, default=0, nullable=False)
    bound_quantity = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, default=utcnow, nullable=False)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)


class XiuxianEquippedArtifact(Base):
    __tablename__ = "xiuxian_equipped_artifacts"
    __table_args__ = (
        UniqueConstraint("tg", "slot", name="uq_xiuxian_equipped_artifact_slot"),
        UniqueConstraint("tg", "artifact_id", name="uq_xiuxian_equipped_artifact_unique"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    tg = Column(BigInteger, nullable=False)
    artifact_id = Column(Integer, ForeignKey("xiuxian_artifacts.id", ondelete="CASCADE"), nullable=False)
    slot = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=utcnow, nullable=False)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)


class XiuxianPillInventory(Base):
    __tablename__ = "xiuxian_pill_inventory"
    __table_args__ = (UniqueConstraint("tg", "pill_id", name="uq_xiuxian_pill_inventory"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    tg = Column(BigInteger, nullable=False)
    pill_id = Column(Integer, ForeignKey("xiuxian_pills.id", ondelete="CASCADE"), nullable=False)
    quantity = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, default=utcnow, nullable=False)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)


class XiuxianTalismanInventory(Base):
    __tablename__ = "xiuxian_talisman_inventory"
    __table_args__ = (UniqueConstraint("tg", "talisman_id", name="uq_xiuxian_talisman_inventory"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    tg = Column(BigInteger, nullable=False)
    talisman_id = Column(Integer, ForeignKey("xiuxian_talismans.id", ondelete="CASCADE"), nullable=False)
    quantity = Column(Integer, default=0, nullable=False)
    bound_quantity = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, default=utcnow, nullable=False)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)


class XiuxianShopItem(Base):
    __tablename__ = "xiuxian_shop_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    owner_tg = Column(BigInteger, nullable=True)
    shop_name = Column(String(64), nullable=False)
    item_kind = Column(String(16), nullable=False)
    item_ref_id = Column(Integer, nullable=False)
    item_name = Column(String(64), nullable=False)
    quantity = Column(Integer, default=0, nullable=False)
    price_stone = Column(Integer, default=0, nullable=False)
    enabled = Column(Boolean, default=True, nullable=False)
    is_official = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=utcnow, nullable=False)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)


class XiuxianDuelRecord(Base):
    __tablename__ = "xiuxian_duel_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    challenger_tg = Column(BigInteger, nullable=False)
    defender_tg = Column(BigInteger, nullable=False)
    winner_tg = Column(BigInteger, nullable=False)
    loser_tg = Column(BigInteger, nullable=False)
    duel_mode = Column(String(16), default="standard", nullable=False)
    challenger_rate = Column(Integer, default=500, nullable=False)
    defender_rate = Column(Integer, default=500, nullable=False)
    summary = Column(Text, nullable=True)
    battle_log = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=utcnow, nullable=False)


def realm_index(stage: str | None) -> int:
    try:
        return REALM_ORDER.index(normalize_realm_stage(stage))
    except ValueError:
        return 0


def serialize_profile(profile: XiuxianProfile | None) -> dict[str, Any] | None:
    if profile is None:
        return None

    realm_stage = normalize_realm_stage(profile.realm_stage)
    return {
        "tg": profile.tg,
        "display_name": profile.display_name,
        "username": profile.username,
        "display_label": profile.display_name or (f"@{profile.username}" if profile.username else f"TG {profile.tg}"),
        "consented": profile.consented,
        "root_type": profile.root_type,
        "root_primary": profile.root_primary,
        "root_secondary": profile.root_secondary,
        "root_relation": profile.root_relation,
        "root_bonus": profile.root_bonus,
        "root_quality": profile.root_quality,
        "root_quality_level": profile.root_quality_level,
        "root_quality_color": profile.root_quality_color,
        "realm_stage": realm_stage,
        "realm_layer": profile.realm_layer,
        "cultivation": profile.cultivation,
        "spiritual_stone": profile.spiritual_stone,
        "bone": profile.bone,
        "comprehension": profile.comprehension,
        "divine_sense": profile.divine_sense,
        "fortune": profile.fortune,
        "willpower": profile.willpower,
        "charisma": profile.charisma,
        "karma": profile.karma,
        "qi_blood": profile.qi_blood,
        "true_yuan": profile.true_yuan,
        "body_movement": profile.body_movement,
        "attack_power": profile.attack_power,
        "defense_power": profile.defense_power,
        "insight_bonus": profile.insight_bonus,
        "sect_contribution": profile.sect_contribution,
        "dan_poison": profile.dan_poison,
        "breakthrough_pill_uses": profile.breakthrough_pill_uses,
        "sect_id": profile.sect_id,
        "sect_role_key": profile.sect_role_key,
        "sect_role_label": SECT_ROLE_LABELS.get(profile.sect_role_key or "", profile.sect_role_key),
        "last_salary_claim_at": serialize_datetime(profile.last_salary_claim_at),
        "sect_joined_at": serialize_datetime(profile.sect_joined_at),
        "sect_betrayal_until": serialize_datetime(profile.sect_betrayal_until),
        "master_tg": profile.master_tg,
        "servitude_started_at": serialize_datetime(profile.servitude_started_at),
        "servitude_challenge_available_at": serialize_datetime(profile.servitude_challenge_available_at),
        "death_at": serialize_datetime(profile.death_at),
        "rebirth_count": int(profile.rebirth_count or 0),
        "robbery_daily_count": profile.robbery_daily_count,
        "robbery_day_key": profile.robbery_day_key,
        "current_artifact_id": profile.current_artifact_id,
        "active_talisman_id": profile.active_talisman_id,
        "current_technique_id": profile.current_technique_id,
        "current_title_id": profile.current_title_id,
        "technique_capacity": profile.technique_capacity,
        "shop_name": profile.shop_name,
        "shop_broadcast": profile.shop_broadcast,
        "last_train_at": serialize_datetime(profile.last_train_at),
        "retreat_started_at": serialize_datetime(profile.retreat_started_at),
        "retreat_end_at": serialize_datetime(profile.retreat_end_at),
        "retreat_gain_per_minute": profile.retreat_gain_per_minute,
        "retreat_cost_per_minute": profile.retreat_cost_per_minute,
        "retreat_minutes_total": profile.retreat_minutes_total,
        "retreat_minutes_resolved": profile.retreat_minutes_resolved,
        "created_at": serialize_datetime(profile.created_at),
        "updated_at": serialize_datetime(profile.updated_at),
    }


def serialize_journal(row: XiuxianJournal | None) -> dict[str, Any] | None:
    if row is None:
        return None
    return {
        "id": row.id,
        "tg": row.tg,
        "action_type": row.action_type,
        "title": row.title,
        "detail": row.detail,
        "created_at": serialize_datetime(row.created_at),
    }


def serialize_title(title: XiuxianTitle | None) -> dict[str, Any] | None:
    if title is None:
        return None
    return {
        "id": title.id,
        "name": title.name,
        "description": title.description,
        "color": title.color,
        "image_url": title.image_url,
        "attack_bonus": title.attack_bonus,
        "defense_bonus": title.defense_bonus,
        "bone_bonus": title.bone_bonus,
        "comprehension_bonus": title.comprehension_bonus,
        "divine_sense_bonus": title.divine_sense_bonus,
        "fortune_bonus": title.fortune_bonus,
        "qi_blood_bonus": title.qi_blood_bonus,
        "true_yuan_bonus": title.true_yuan_bonus,
        "body_movement_bonus": title.body_movement_bonus,
        "duel_rate_bonus": title.duel_rate_bonus,
        "cultivation_bonus": title.cultivation_bonus,
        "breakthrough_bonus": title.breakthrough_bonus,
        "extra_effects": title.extra_effects or {},
        "enabled": title.enabled,
        "created_at": serialize_datetime(title.created_at),
        "updated_at": serialize_datetime(title.updated_at),
    }


def serialize_user_title(row: XiuxianUserTitle | None, title: dict[str, Any] | None = None) -> dict[str, Any] | None:
    if row is None:
        return None
    return {
        "id": row.id,
        "tg": row.tg,
        "title_id": row.title_id,
        "source": row.source,
        "obtained_note": row.obtained_note,
        "title": title,
        "created_at": serialize_datetime(row.created_at),
        "updated_at": serialize_datetime(row.updated_at),
    }


def serialize_achievement(achievement: XiuxianAchievement | None) -> dict[str, Any] | None:
    if achievement is None:
        return None
    return {
        "id": achievement.id,
        "achievement_key": achievement.achievement_key,
        "name": achievement.name,
        "description": achievement.description,
        "metric_key": achievement.metric_key,
        "target_value": int(achievement.target_value or 0),
        "reward_config": achievement.reward_config or {},
        "notify_group": achievement.notify_group,
        "notify_private": achievement.notify_private,
        "enabled": achievement.enabled,
        "sort_order": achievement.sort_order,
        "created_at": serialize_datetime(achievement.created_at),
        "updated_at": serialize_datetime(achievement.updated_at),
    }


def serialize_achievement_progress(progress: XiuxianAchievementProgress | None) -> dict[str, Any] | None:
    if progress is None:
        return None
    return {
        "id": progress.id,
        "tg": progress.tg,
        "metric_key": progress.metric_key,
        "value": int(progress.current_value or 0),
        "created_at": serialize_datetime(progress.created_at),
        "updated_at": serialize_datetime(progress.updated_at),
    }


def serialize_user_achievement(
    row: XiuxianUserAchievement | None,
    achievement: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    if row is None:
        return None
    return {
        "id": row.id,
        "tg": row.tg,
        "achievement_id": row.achievement_id,
        "achievement": achievement,
        "reward_snapshot": row.reward_snapshot or {},
        "unlocked_at": serialize_datetime(row.unlocked_at),
        "private_notified_at": serialize_datetime(row.private_notified_at),
        "group_notified_at": serialize_datetime(row.group_notified_at),
        "updated_at": serialize_datetime(row.updated_at),
    }


def serialize_sect(sect: XiuxianSect | None) -> dict[str, Any] | None:
    if sect is None:
        return None
    return {
        "id": sect.id,
        "name": sect.name,
        "camp": sect.camp,
        "camp_label": SECT_CAMP_LABELS.get(sect.camp, sect.camp),
        "description": sect.description,
        "image_url": sect.image_url,
        "min_realm_stage": sect.min_realm_stage,
        "min_realm_layer": sect.min_realm_layer,
        "min_stone": sect.min_stone,
        "min_bone": sect.min_bone,
        "min_comprehension": sect.min_comprehension,
        "min_divine_sense": sect.min_divine_sense,
        "min_fortune": sect.min_fortune,
        "min_willpower": sect.min_willpower,
        "min_charisma": sect.min_charisma,
        "min_karma": sect.min_karma,
        "min_body_movement": sect.min_body_movement,
        "min_combat_power": int(sect.min_combat_power or 0),
        "attack_bonus": sect.attack_bonus,
        "defense_bonus": sect.defense_bonus,
        "duel_rate_bonus": sect.duel_rate_bonus,
        "cultivation_bonus": sect.cultivation_bonus,
        "fortune_bonus": sect.fortune_bonus,
        "body_movement_bonus": sect.body_movement_bonus,
        "entry_hint": sect.entry_hint,
        "enabled": sect.enabled,
    }


def serialize_sect_role(role: XiuxianSectRole | None) -> dict[str, Any] | None:
    if role is None:
        return None
    return {
        "id": role.id,
        "sect_id": role.sect_id,
        "role_key": role.role_key,
        "role_name": role.role_name,
        "attack_bonus": role.attack_bonus,
        "defense_bonus": role.defense_bonus,
        "duel_rate_bonus": role.duel_rate_bonus,
        "cultivation_bonus": role.cultivation_bonus,
        "monthly_salary": role.monthly_salary,
        "can_publish_tasks": role.can_publish_tasks,
        "sort_order": role.sort_order,
    }


def serialize_material(material: XiuxianMaterial | None) -> dict[str, Any] | None:
    if material is None:
        return None
    quality = get_quality_meta(material.quality_level)
    description = str(material.description or "").strip()
    quality_note = description or MATERIAL_QUALITY_NOTES.get(int(quality["level"]), "") or quality["description"]
    return {
        "id": material.id,
        "name": material.name,
        "quality_level": material.quality_level,
        "quality_label": quality["label"],
        "quality_color": quality["color"],
        "quality_description": quality["description"],
        "quality_feature": quality_note,
        "image_url": material.image_url,
        "description": material.description,
        "enabled": material.enabled,
    }


def serialize_recipe(recipe: XiuxianRecipe | None) -> dict[str, Any] | None:
    if recipe is None:
        return None
    return {
        "id": recipe.id,
        "name": recipe.name,
        "recipe_kind": recipe.recipe_kind,
        "recipe_kind_label": RECIPE_KIND_LABELS.get(recipe.recipe_kind, recipe.recipe_kind),
        "result_kind": recipe.result_kind,
        "result_kind_label": ITEM_KIND_LABELS.get(recipe.result_kind, recipe.result_kind),
        "result_ref_id": recipe.result_ref_id,
        "result_quantity": recipe.result_quantity,
        "base_success_rate": recipe.base_success_rate,
        "broadcast_on_success": recipe.broadcast_on_success,
        "enabled": recipe.enabled,
    }


def serialize_user_recipe(
    row: XiuxianUserRecipe | None,
    recipe: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    if row is None:
        return None
    return {
        "id": row.id,
        "tg": row.tg,
        "recipe_id": row.recipe_id,
        "source": row.source,
        "obtained_note": row.obtained_note,
        "recipe": recipe,
        "created_at": serialize_datetime(row.created_at),
        "updated_at": serialize_datetime(row.updated_at),
    }


def serialize_scene(scene: XiuxianScene | None) -> dict[str, Any] | None:
    if scene is None:
        return None
    return {
        "id": scene.id,
        "name": scene.name,
        "description": scene.description,
        "image_url": scene.image_url,
        "max_minutes": scene.max_minutes,
        "min_realm_stage": normalize_realm_stage(scene.min_realm_stage) if scene.min_realm_stage else None,
        "min_realm_layer": scene.min_realm_layer,
        "min_combat_power": int(scene.min_combat_power or 0),
        "event_pool": _normalize_scene_event_pool(scene.event_pool),
        "enabled": scene.enabled,
    }


def serialize_scene_drop(drop: XiuxianSceneDrop | None) -> dict[str, Any] | None:
    if drop is None:
        return None
    return {
        "id": drop.id,
        "scene_id": drop.scene_id,
        "reward_kind": drop.reward_kind,
        "reward_kind_label": ITEM_KIND_LABELS.get(drop.reward_kind, drop.reward_kind),
        "reward_ref_id": drop.reward_ref_id,
        "quantity_min": drop.quantity_min,
        "quantity_max": drop.quantity_max,
        "weight": drop.weight,
        "stone_reward": drop.stone_reward,
        "event_text": drop.event_text,
    }


def serialize_exploration(exploration: XiuxianExploration | None) -> dict[str, Any] | None:
    if exploration is None:
        return None
    return {
        "id": exploration.id,
        "tg": exploration.tg,
        "scene_id": exploration.scene_id,
        "started_at": serialize_datetime(exploration.started_at),
        "end_at": serialize_datetime(exploration.end_at),
        "claimed": exploration.claimed,
        "reward_kind": exploration.reward_kind,
        "reward_kind_label": ITEM_KIND_LABELS.get(exploration.reward_kind or "", exploration.reward_kind),
        "reward_ref_id": exploration.reward_ref_id,
        "reward_quantity": exploration.reward_quantity,
        "stone_reward": exploration.stone_reward,
        "event_text": exploration.event_text,
        "outcome_payload": _sanitize_json_value(exploration.outcome_payload) or {},
    }


def serialize_task(task: XiuxianTask | None) -> dict[str, Any] | None:
    if task is None:
        return None
    return {
        "id": task.id,
        "title": task.title,
        "description": task.description,
        "task_scope": task.task_scope,
        "task_scope_label": TASK_SCOPE_LABELS.get(task.task_scope, task.task_scope),
        "task_type": task.task_type,
        "task_type_label": TASK_TYPE_LABELS.get(task.task_type, task.task_type),
        "owner_tg": task.owner_tg,
        "sect_id": task.sect_id,
        "question_text": task.question_text,
        "image_url": task.image_url,
        "required_item_kind": task.required_item_kind,
        "required_item_kind_label": ITEM_KIND_LABELS.get(task.required_item_kind or "", task.required_item_kind),
        "required_item_ref_id": task.required_item_ref_id,
        "required_item_quantity": task.required_item_quantity,
        "reward_stone": task.reward_stone,
        "reward_item_kind": task.reward_item_kind,
        "reward_item_kind_label": ITEM_KIND_LABELS.get(task.reward_item_kind or "", task.reward_item_kind),
        "reward_item_ref_id": task.reward_item_ref_id,
        "reward_item_quantity": task.reward_item_quantity,
        "max_claimants": task.max_claimants,
        "claimants_count": task.claimants_count,
        "active_in_group": task.active_in_group,
        "group_chat_id": task.group_chat_id,
        "group_message_id": task.group_message_id,
        "winner_tg": task.winner_tg,
        "enabled": task.enabled,
        "status": task.status,
        "deadline_at": serialize_datetime(task.deadline_at),
        "created_at": serialize_datetime(task.created_at),
    }


def serialize_encounter_template(template: XiuxianEncounterTemplate | None) -> dict[str, Any] | None:
    if template is None:
        return None
    return {
        "id": template.id,
        "name": template.name,
        "description": template.description,
        "image_url": template.image_url,
        "button_text": template.button_text,
        "success_text": template.success_text,
        "broadcast_text": template.broadcast_text,
        "weight": template.weight,
        "active_seconds": template.active_seconds,
        "min_realm_stage": normalize_realm_stage(template.min_realm_stage) if template.min_realm_stage else None,
        "min_realm_layer": template.min_realm_layer,
        "min_combat_power": template.min_combat_power,
        "reward_stone_min": template.reward_stone_min,
        "reward_stone_max": template.reward_stone_max,
        "reward_cultivation_min": template.reward_cultivation_min,
        "reward_cultivation_max": template.reward_cultivation_max,
        "reward_item_kind": template.reward_item_kind,
        "reward_item_kind_label": ITEM_KIND_LABELS.get(template.reward_item_kind or "", template.reward_item_kind),
        "reward_item_ref_id": template.reward_item_ref_id,
        "reward_item_quantity_min": template.reward_item_quantity_min,
        "reward_item_quantity_max": template.reward_item_quantity_max,
        "reward_willpower": template.reward_willpower,
        "reward_charisma": template.reward_charisma,
        "reward_karma": template.reward_karma,
        "enabled": template.enabled,
        "created_at": serialize_datetime(template.created_at),
        "updated_at": serialize_datetime(template.updated_at),
    }


def serialize_encounter_instance(instance: XiuxianEncounterInstance | None) -> dict[str, Any] | None:
    if instance is None:
        return None
    return {
        "id": instance.id,
        "template_id": instance.template_id,
        "template_name": instance.template_name,
        "group_chat_id": instance.group_chat_id,
        "message_id": instance.message_id,
        "button_text": instance.button_text,
        "status": instance.status,
        "reward_payload": _sanitize_json_value(instance.reward_payload) or {},
        "expires_at": serialize_datetime(instance.expires_at),
        "claimer_tg": instance.claimer_tg,
        "claimed_at": serialize_datetime(instance.claimed_at),
        "created_at": serialize_datetime(instance.created_at),
        "updated_at": serialize_datetime(instance.updated_at),
    }


def serialize_red_envelope(envelope: XiuxianRedEnvelope | None) -> dict[str, Any] | None:
    if envelope is None:
        return None
    return {
        "id": envelope.id,
        "creator_tg": envelope.creator_tg,
        "cover_text": envelope.cover_text,
        "image_url": envelope.image_url,
        "mode": envelope.mode,
        "mode_label": ENVELOPE_MODE_LABELS.get(envelope.mode, envelope.mode),
        "target_tg": envelope.target_tg,
        "amount_total": envelope.amount_total,
        "count_total": envelope.count_total,
        "remaining_amount": envelope.remaining_amount,
        "remaining_count": envelope.remaining_count,
        "status": envelope.status,
        "group_chat_id": envelope.group_chat_id,
        "message_id": envelope.message_id,
        "created_at": serialize_datetime(envelope.created_at),
    }


def serialize_artifact(artifact: XiuxianArtifact | None) -> dict[str, Any] | None:
    if artifact is None:
        return None
    quality = get_quality_meta(artifact.rarity)

    return {
        "id": artifact.id,
        "name": artifact.name,
        "rarity": quality["label"],
        "rarity_level": quality["level"],
        "quality_color": quality["color"],
        "quality_description": quality["description"],
        "quality_feature": quality["feature"],
        "artifact_type": artifact.artifact_type,
        "artifact_type_label": ARTIFACT_TYPE_LABELS.get(artifact.artifact_type, artifact.artifact_type),
        "artifact_role": artifact.artifact_role,
        "artifact_role_label": ARTIFACT_ROLE_LABELS.get(artifact.artifact_role, artifact.artifact_role),
        "equip_slot": artifact.equip_slot,
        "equip_slot_label": ARTIFACT_SLOT_LABELS.get(artifact.equip_slot, artifact.equip_slot),
        "artifact_set_id": artifact.artifact_set_id,
        "image_url": artifact.image_url,
        "description": artifact.description,
        "attack_bonus": artifact.attack_bonus,
        "defense_bonus": artifact.defense_bonus,
        "bone_bonus": artifact.bone_bonus,
        "comprehension_bonus": artifact.comprehension_bonus,
        "divine_sense_bonus": artifact.divine_sense_bonus,
        "fortune_bonus": artifact.fortune_bonus,
        "qi_blood_bonus": artifact.qi_blood_bonus,
        "true_yuan_bonus": artifact.true_yuan_bonus,
        "body_movement_bonus": artifact.body_movement_bonus,
        "duel_rate_bonus": artifact.duel_rate_bonus,
        "cultivation_bonus": artifact.cultivation_bonus,
        "combat_config": _normalize_combat_config(artifact.combat_config),
        "min_realm_stage": artifact.min_realm_stage,
        "min_realm_layer": artifact.min_realm_layer,
        "enabled": artifact.enabled,
    }


def serialize_pill(pill: XiuxianPill | None) -> dict[str, Any] | None:
    if pill is None:
        return None
    quality = get_quality_meta(pill.rarity)

    return {
        "id": pill.id,
        "name": pill.name,
        "rarity": quality["label"],
        "rarity_level": quality["level"],
        "quality_color": quality["color"],
        "quality_description": quality["description"],
        "quality_feature": quality["feature"],
        "pill_type": pill.pill_type,
        "pill_type_label": PILL_TYPE_LABELS.get(pill.pill_type, pill.pill_type),
        "effect_label": PILL_TYPE_LABELS.get(pill.pill_type, pill.pill_type),
        "effect_value_label": PILL_EFFECT_VALUE_LABELS.get(pill.pill_type, "主效果"),
        "image_url": pill.image_url,
        "description": pill.description,
        "effect_value": pill.effect_value,
        "poison_delta": pill.poison_delta,
        "attack_bonus": pill.attack_bonus,
        "defense_bonus": pill.defense_bonus,
        "bone_bonus": pill.bone_bonus,
        "comprehension_bonus": pill.comprehension_bonus,
        "divine_sense_bonus": pill.divine_sense_bonus,
        "fortune_bonus": pill.fortune_bonus,
        "qi_blood_bonus": pill.qi_blood_bonus,
        "true_yuan_bonus": pill.true_yuan_bonus,
        "body_movement_bonus": pill.body_movement_bonus,
        "min_realm_stage": pill.min_realm_stage,
        "min_realm_layer": pill.min_realm_layer,
        "enabled": pill.enabled,
    }


def serialize_talisman(talisman: XiuxianTalisman | None) -> dict[str, Any] | None:
    if talisman is None:
        return None
    quality = get_quality_meta(talisman.rarity)

    return {
        "id": talisman.id,
        "name": talisman.name,
        "rarity": quality["label"],
        "rarity_level": quality["level"],
        "quality_color": quality["color"],
        "quality_description": quality["description"],
        "quality_feature": quality["feature"],
        "image_url": talisman.image_url,
        "description": talisman.description,
        "attack_bonus": talisman.attack_bonus,
        "defense_bonus": talisman.defense_bonus,
        "bone_bonus": talisman.bone_bonus,
        "comprehension_bonus": talisman.comprehension_bonus,
        "divine_sense_bonus": talisman.divine_sense_bonus,
        "fortune_bonus": talisman.fortune_bonus,
        "qi_blood_bonus": talisman.qi_blood_bonus,
        "true_yuan_bonus": talisman.true_yuan_bonus,
        "body_movement_bonus": talisman.body_movement_bonus,
        "duel_rate_bonus": talisman.duel_rate_bonus,
        "effect_uses": max(int(talisman.effect_uses or 1), 1),
        "combat_config": _normalize_combat_config(talisman.combat_config),
        "min_realm_stage": talisman.min_realm_stage,
        "min_realm_layer": talisman.min_realm_layer,
        "enabled": talisman.enabled,
    }


def serialize_technique(technique: XiuxianTechnique | None) -> dict[str, Any] | None:
    if technique is None:
        return None
    quality = get_quality_meta(technique.rarity)
    return {
        "id": technique.id,
        "name": technique.name,
        "rarity": quality["label"],
        "rarity_level": quality["level"],
        "quality_color": quality["color"],
        "quality_description": quality["description"],
        "quality_feature": quality["feature"],
        "technique_type": technique.technique_type,
        "technique_type_label": TECHNIQUE_TYPE_LABELS.get(technique.technique_type, technique.technique_type),
        "image_url": technique.image_url,
        "description": technique.description,
        "attack_bonus": technique.attack_bonus,
        "defense_bonus": technique.defense_bonus,
        "bone_bonus": technique.bone_bonus,
        "comprehension_bonus": technique.comprehension_bonus,
        "divine_sense_bonus": technique.divine_sense_bonus,
        "fortune_bonus": technique.fortune_bonus,
        "qi_blood_bonus": technique.qi_blood_bonus,
        "true_yuan_bonus": technique.true_yuan_bonus,
        "body_movement_bonus": technique.body_movement_bonus,
        "duel_rate_bonus": technique.duel_rate_bonus,
        "cultivation_bonus": technique.cultivation_bonus,
        "breakthrough_bonus": technique.breakthrough_bonus,
        "combat_config": _normalize_combat_config(technique.combat_config),
        "min_realm_stage": normalize_realm_stage(technique.min_realm_stage),
        "min_realm_layer": technique.min_realm_layer,
        "enabled": technique.enabled,
    }


def serialize_user_technique(
    row: XiuxianUserTechnique | None,
    technique: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    if row is None:
        return None
    return {
        "id": row.id,
        "tg": row.tg,
        "technique_id": row.technique_id,
        "source": row.source,
        "obtained_note": row.obtained_note,
        "technique": technique,
        "created_at": serialize_datetime(row.created_at),
        "updated_at": serialize_datetime(row.updated_at),
    }


def serialize_artifact_set(artifact_set: XiuxianArtifactSet | None) -> dict[str, Any] | None:
    if artifact_set is None:
        return None
    return {
        "id": artifact_set.id,
        "name": artifact_set.name,
        "description": artifact_set.description,
        "required_count": artifact_set.required_count,
        "attack_bonus": artifact_set.attack_bonus,
        "defense_bonus": artifact_set.defense_bonus,
        "bone_bonus": artifact_set.bone_bonus,
        "comprehension_bonus": artifact_set.comprehension_bonus,
        "divine_sense_bonus": artifact_set.divine_sense_bonus,
        "fortune_bonus": artifact_set.fortune_bonus,
        "qi_blood_bonus": artifact_set.qi_blood_bonus,
        "true_yuan_bonus": artifact_set.true_yuan_bonus,
        "body_movement_bonus": artifact_set.body_movement_bonus,
        "duel_rate_bonus": artifact_set.duel_rate_bonus,
        "cultivation_bonus": artifact_set.cultivation_bonus,
        "breakthrough_bonus": artifact_set.breakthrough_bonus,
        "enabled": artifact_set.enabled,
        "created_at": serialize_datetime(artifact_set.created_at),
        "updated_at": serialize_datetime(artifact_set.updated_at),
    }


def serialize_shop_item(item: XiuxianShopItem | None) -> dict[str, Any] | None:
    if item is None:
        return None

    return {
        "id": item.id,
        "owner_tg": item.owner_tg,
        "shop_name": item.shop_name,
        "item_kind": item.item_kind,
        "item_kind_label": ITEM_KIND_LABELS.get(item.item_kind, item.item_kind),
        "item_ref_id": item.item_ref_id,
        "item_name": item.item_name,
        "quantity": item.quantity,
        "price_stone": item.price_stone,
        "enabled": item.enabled,
        "is_official": item.is_official,
        "created_at": serialize_datetime(item.created_at),
    }


def serialize_image_upload_permission(permission: XiuxianImageUploadPermission | None) -> dict[str, Any] | None:
    if permission is None:
        return None

    return {
        "tg": permission.tg,
        "created_at": serialize_datetime(permission.created_at),
        "updated_at": serialize_datetime(permission.updated_at),
    }


def serialize_emby_account(account: Emby | None) -> dict[str, Any] | None:
    if account is None:
        return None

    return {
        "tg": int(account.tg),
        "name": account.name,
        "embyid": account.embyid,
        "lv": account.lv,
        "us": int(account.us or 0),
        "iv": int(account.iv or 0),
        "cr": serialize_datetime(account.cr),
        "ex": serialize_datetime(account.ex),
        "ch": serialize_datetime(account.ch),
    }


def get_xiuxian_settings() -> dict[str, Any]:
    with Session() as session:
        rows = session.query(XiuxianSetting).all()
        settings = {row.setting_key: row.setting_value for row in rows}
    for key in DEPRECATED_XIUXIAN_SETTING_KEYS:
        settings.pop(key, None)
    merged = copy.deepcopy(DEFAULT_SETTINGS)
    merged.update(settings)
    return merged


def set_xiuxian_settings(patch: dict[str, Any]) -> dict[str, Any]:
    sanitized_patch = {key: value for key, value in patch.items() if key not in DEPRECATED_XIUXIAN_SETTING_KEYS}
    with Session() as session:
        for key, value in sanitized_patch.items():
            row = session.query(XiuxianSetting).filter(XiuxianSetting.setting_key == key).first()
            if row is None:
                row = XiuxianSetting(setting_key=key, setting_value=value)
                session.add(row)
            else:
                row.setting_value = value
                row.updated_at = utcnow()
        session.commit()
    return get_xiuxian_settings()


def list_image_upload_permissions() -> list[dict[str, Any]]:
    with Session() as session:
        rows = (
            session.query(XiuxianImageUploadPermission)
            .order_by(XiuxianImageUploadPermission.updated_at.desc(), XiuxianImageUploadPermission.tg.asc())
            .all()
        )
        return [serialize_image_upload_permission(row) for row in rows]


def has_image_upload_permission(tg: int) -> bool:
    with Session() as session:
        row = session.query(XiuxianImageUploadPermission).filter(XiuxianImageUploadPermission.tg == tg).first()
        return row is not None


def grant_image_upload_permission(tg: int) -> dict[str, Any]:
    with Session() as session:
        row = session.query(XiuxianImageUploadPermission).filter(XiuxianImageUploadPermission.tg == tg).first()
        if row is None:
            row = XiuxianImageUploadPermission(tg=tg)
            session.add(row)
        row.updated_at = utcnow()
        session.commit()
        session.refresh(row)
        return serialize_image_upload_permission(row)


def revoke_image_upload_permission(tg: int) -> bool:
    with Session() as session:
        row = session.query(XiuxianImageUploadPermission).filter(XiuxianImageUploadPermission.tg == tg).first()
        if row is None:
            return False
        session.delete(row)
        session.commit()
        return True


def get_profile(tg: int, create: bool = False) -> XiuxianProfile | None:
    with Session() as session:
        profile = session.query(XiuxianProfile).filter(XiuxianProfile.tg == tg).first()
        if profile is None and create:
            profile = XiuxianProfile(tg=tg)
            session.add(profile)
            session.commit()
            session.refresh(profile)
        return profile


def upsert_profile(tg: int, **fields) -> XiuxianProfile:
    with Session() as session:
        profile = session.query(XiuxianProfile).filter(XiuxianProfile.tg == tg).first()
        if profile is None:
            profile = XiuxianProfile(tg=tg)
            session.add(profile)

        if "realm_stage" in fields:
            fields["realm_stage"] = normalize_realm_stage(fields.get("realm_stage"))

        for key, value in fields.items():
            setattr(profile, key, value)

        profile.updated_at = utcnow()
        session.commit()
        session.refresh(profile)
        return profile


def is_profile_dead(profile: XiuxianProfile | dict[str, Any] | None) -> bool:
    if profile is None:
        return False
    if isinstance(profile, dict):
        return bool(profile.get("death_at"))
    return profile.death_at is not None


def assert_profile_alive(profile: XiuxianProfile | dict[str, Any] | None, action_text: str = "继续行动") -> None:
    if is_profile_dead(profile):
        raise ValueError(f"你已身死道消，无法{action_text}，只能重新踏出仙途。")


def _active_duel_pool_row(
    session: Session,
    tg: int,
    *,
    for_update: bool = False,
) -> XiuxianDuelBetPool | None:
    query = session.query(XiuxianDuelBetPool).filter(
        XiuxianDuelBetPool.resolved.is_(False),
        or_(XiuxianDuelBetPool.challenger_tg == tg, XiuxianDuelBetPool.defender_tg == tg),
    )
    if for_update:
        query = query.with_for_update()
    return query.order_by(XiuxianDuelBetPool.id.desc()).first()


def get_active_duel_lock(tg: int) -> dict[str, Any] | None:
    with Session() as session:
        row = _active_duel_pool_row(session, tg, for_update=False)
        if row is None:
            return None
        return {
            "pool_id": int(row.id),
            "duel_mode": str(row.duel_mode or "standard"),
            "duel_mode_label": DUEL_MODE_LABELS.get(str(row.duel_mode or "standard"), str(row.duel_mode or "standard")),
            "challenger_tg": int(row.challenger_tg),
            "defender_tg": int(row.defender_tg),
            "bets_close_at": serialize_datetime(row.bets_close_at),
        }


def assert_currency_operation_allowed(
    tg: int,
    action_text: str = "进行灵石操作",
    *,
    session: Session | None = None,
    profile: XiuxianProfile | None = None,
) -> None:
    own_session = session is None
    active_session = session or Session()
    try:
        profile_row = profile
        if profile_row is None:
            query = active_session.query(XiuxianProfile).filter(XiuxianProfile.tg == tg)
            if not own_session:
                query = query.with_for_update()
            profile_row = query.first()
        assert_profile_alive(profile_row, action_text)
        active_duel = _active_duel_pool_row(active_session, tg, for_update=not own_session)
        if active_duel is not None:
            duel_mode = str(active_duel.duel_mode or "standard")
            raise ValueError(f"{DUEL_MODE_LABELS.get(duel_mode, '斗法')}结算前，禁止{action_text}。")
    finally:
        if own_session:
            active_session.close()


def _clear_servitude_fields(profile: XiuxianProfile) -> None:
    profile.master_tg = None
    profile.servitude_started_at = None
    profile.servitude_challenge_available_at = None


def apply_spiritual_stone_delta(
    session: Session,
    tg: int,
    delta: int,
    *,
    action_text: str = "进行灵石操作",
    enforce_currency_lock: bool = False,
    allow_create: bool = False,
    allow_dead: bool = False,
    apply_tribute: bool = True,
) -> dict[str, Any]:
    amount = int(delta or 0)
    profile = session.query(XiuxianProfile).filter(XiuxianProfile.tg == tg).with_for_update().first()
    if profile is None:
        if not allow_create:
            raise ValueError("你还没有踏入仙途")
        profile = XiuxianProfile(tg=tg)
        session.add(profile)
        session.flush()
    if not allow_dead:
        assert_profile_alive(profile, action_text)
    if enforce_currency_lock and profile.consented:
        assert_currency_operation_allowed(tg, action_text, session=session, profile=profile)

    current = int(profile.spiritual_stone or 0)
    tribute_amount = 0
    tribute_master = None
    if amount < 0 and current + amount < 0:
        raise ValueError("灵石不足")

    if amount > 0 and apply_tribute and profile.consented and profile.master_tg:
        master = session.query(XiuxianProfile).filter(XiuxianProfile.tg == int(profile.master_tg)).with_for_update().first()
        if master is None or not master.consented or master.death_at is not None or int(master.tg) == int(profile.tg):
            _clear_servitude_fields(profile)
        else:
            settings = get_xiuxian_settings()
            tribute_percent = max(min(int(settings.get("slave_tribute_percent", DEFAULT_SETTINGS.get("slave_tribute_percent", 20)) or 0), 100), 0)
            tribute_amount = min(amount, amount * tribute_percent // 100)
            if tribute_amount > 0:
                master.spiritual_stone = int(master.spiritual_stone or 0) + tribute_amount
                master.updated_at = utcnow()
                tribute_master = master

    profile.spiritual_stone = max(current + amount - tribute_amount, 0)
    profile.updated_at = utcnow()
    return {
        "profile": profile,
        "tribute_amount": tribute_amount,
        "tribute_master": tribute_master,
        "net_delta": amount - tribute_amount,
    }


def get_artifact(artifact_id: int) -> XiuxianArtifact | None:
    with Session() as session:
        return session.query(XiuxianArtifact).filter(XiuxianArtifact.id == artifact_id).first()


def get_pill(pill_id: int) -> XiuxianPill | None:
    with Session() as session:
        return session.query(XiuxianPill).filter(XiuxianPill.id == pill_id).first()


def get_talisman(talisman_id: int) -> XiuxianTalisman | None:
    with Session() as session:
        return session.query(XiuxianTalisman).filter(XiuxianTalisman.id == talisman_id).first()


def get_technique(technique_id: int) -> XiuxianTechnique | None:
    with Session() as session:
        return session.query(XiuxianTechnique).filter(XiuxianTechnique.id == technique_id).first()


def get_artifact_set(artifact_set_id: int) -> XiuxianArtifactSet | None:
    with Session() as session:
        return session.query(XiuxianArtifactSet).filter(XiuxianArtifactSet.id == artifact_set_id).first()


def list_artifacts(enabled_only: bool = False) -> list[dict[str, Any]]:
    with Session() as session:
        query = session.query(XiuxianArtifact)
        if enabled_only:
            query = query.filter(XiuxianArtifact.enabled.is_(True))
        return [serialize_artifact(item) for item in query.order_by(XiuxianArtifact.id.desc()).all()]


def list_pills(enabled_only: bool = False) -> list[dict[str, Any]]:
    with Session() as session:
        query = session.query(XiuxianPill)
        if enabled_only:
            query = query.filter(XiuxianPill.enabled.is_(True))
        return [serialize_pill(item) for item in query.order_by(XiuxianPill.id.desc()).all()]


def list_talismans(enabled_only: bool = False) -> list[dict[str, Any]]:
    with Session() as session:
        query = session.query(XiuxianTalisman)
        if enabled_only:
            query = query.filter(XiuxianTalisman.enabled.is_(True))
        return [serialize_talisman(item) for item in query.order_by(XiuxianTalisman.id.desc()).all()]


def list_techniques(enabled_only: bool = False) -> list[dict[str, Any]]:
    with Session() as session:
        query = session.query(XiuxianTechnique)
        if enabled_only:
            query = query.filter(XiuxianTechnique.enabled.is_(True))
        return [serialize_technique(item) for item in query.order_by(XiuxianTechnique.id.desc()).all()]


def list_user_techniques(tg: int, enabled_only: bool = False) -> list[dict[str, Any]]:
    with Session() as session:
        rows = (
            session.query(XiuxianUserTechnique)
            .filter(XiuxianUserTechnique.tg == tg)
            .order_by(XiuxianUserTechnique.created_at.asc(), XiuxianUserTechnique.id.asc())
            .all()
        )
        technique_ids = [item.technique_id for item in rows] or [-1]
        technique_map = {
            row.id: row
            for row in session.query(XiuxianTechnique).filter(XiuxianTechnique.id.in_(technique_ids)).all()
        }
        payloads: list[dict[str, Any]] = []
        for row in rows:
            technique = serialize_technique(technique_map.get(row.technique_id))
            if enabled_only and not (technique or {}).get("enabled"):
                continue
            payloads.append(serialize_user_technique(row, technique))
        return payloads


def user_has_technique(tg: int, technique_id: int) -> bool:
    with Session() as session:
        row = (
            session.query(XiuxianUserTechnique)
            .filter(XiuxianUserTechnique.tg == tg, XiuxianUserTechnique.technique_id == technique_id)
            .first()
        )
        return row is not None


def grant_technique_to_user(
    tg: int,
    technique_id: int,
    *,
    source: str | None = None,
    obtained_note: str | None = None,
    auto_equip_if_empty: bool = False,
) -> dict[str, Any]:
    with Session() as session:
        technique = session.query(XiuxianTechnique).filter(XiuxianTechnique.id == technique_id).first()
        if technique is None:
            raise ValueError("technique not found")
        profile = session.query(XiuxianProfile).filter(XiuxianProfile.tg == tg).first()
        if profile is None:
            profile = XiuxianProfile(tg=tg)
            session.add(profile)
        owned_count = (
            session.query(XiuxianUserTechnique)
            .filter(XiuxianUserTechnique.tg == tg)
            .count()
        )
        row = (
            session.query(XiuxianUserTechnique)
            .filter(XiuxianUserTechnique.tg == tg, XiuxianUserTechnique.technique_id == technique_id)
            .first()
        )
        if row is None:
            capacity = max(int(profile.technique_capacity or 0), 1)
            if owned_count >= capacity:
                raise ValueError(f"可参悟功法数量已满，当前上限为 {capacity}。")
            row = XiuxianUserTechnique(
                tg=tg,
                technique_id=technique_id,
                source=(source or "").strip() or None,
                obtained_note=(obtained_note or "").strip() or None,
            )
            session.add(row)
        else:
            row.source = (source or row.source or "").strip() or None
            if obtained_note is not None:
                row.obtained_note = (obtained_note or "").strip() or None
            row.updated_at = utcnow()
        if auto_equip_if_empty and not profile.current_technique_id:
            profile.current_technique_id = technique_id
            profile.updated_at = utcnow()
        session.commit()
        session.refresh(row)
        return serialize_user_technique(row, serialize_technique(technique))


def revoke_technique_from_user(tg: int, technique_id: int) -> bool:
    with Session() as session:
        row = (
            session.query(XiuxianUserTechnique)
            .filter(XiuxianUserTechnique.tg == tg, XiuxianUserTechnique.technique_id == technique_id)
            .first()
        )
        if row is None:
            return False
        profile = session.query(XiuxianProfile).filter(XiuxianProfile.tg == tg).first()
        if profile is not None and int(profile.current_technique_id or 0) == int(technique_id):
            profile.current_technique_id = None
            profile.updated_at = utcnow()
        session.delete(row)
        session.commit()
        return True


def list_artifact_sets(enabled_only: bool = False) -> list[dict[str, Any]]:
    with Session() as session:
        query = session.query(XiuxianArtifactSet)
        if enabled_only:
            query = query.filter(XiuxianArtifactSet.enabled.is_(True))
        return [serialize_artifact_set(item) for item in query.order_by(XiuxianArtifactSet.id.desc()).all()]


def _coerce_int(value: Any, default: int = 0) -> int:
    try:
        return int(value if value is not None else default)
    except (TypeError, ValueError):
        return int(default)


def _coerce_bool(value: Any, default: bool = True) -> bool:
    if value is None:
        return default
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"", "0", "false", "no", "off"}:
            return False
        if normalized in {"1", "true", "yes", "on"}:
            return True
    return bool(value)


def _sanitize_json_value(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        return {str(key): _sanitize_json_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_sanitize_json_value(item) for item in value]
    return str(value)


def _normalize_combat_config(raw: Any) -> dict[str, Any]:
    # 战斗配置来自后台 JSON 表单，入库前统一裁剪字段和数值范围，避免前端传脏数据。
    payload = _sanitize_json_value(copy.deepcopy(raw)) if isinstance(raw, dict) else {}
    if not isinstance(payload, dict):
        payload = {}
    payload["opening_text"] = str(payload.get("opening_text") or "").strip()
    for key in ("skills", "passives"):
        normalized_rows: list[dict[str, Any]] = []
        for item in payload.get(key) or []:
            if not isinstance(item, dict):
                continue
            entry = {str(k): _sanitize_json_value(v) for k, v in item.items()}
            entry["name"] = str(entry.get("name") or entry.get("label") or "").strip()
            entry["kind"] = str(entry.get("kind") or "").strip()
            entry["chance"] = max(min(_coerce_int(entry.get("chance"), 0), 100), 0)
            entry["duration"] = max(_coerce_int(entry.get("duration"), 0), 0)
            entry["flat_damage"] = _coerce_int(entry.get("flat_damage"), 0)
            entry["flat_shield"] = max(_coerce_int(entry.get("flat_shield"), 0), 0)
            entry["flat_heal"] = max(_coerce_int(entry.get("flat_heal"), 0), 0)
            entry["cost_true_yuan"] = max(_coerce_int(entry.get("cost_true_yuan"), 0), 0)
            entry["ratio_percent"] = _coerce_int(entry.get("ratio_percent"), 0)
            entry["dodge_bonus"] = _coerce_int(entry.get("dodge_bonus"), 0)
            entry["hit_bonus"] = _coerce_int(entry.get("hit_bonus"), 0)
            entry["defense_ratio_percent"] = _coerce_int(entry.get("defense_ratio_percent"), 0)
            entry["attack_ratio_percent"] = _coerce_int(entry.get("attack_ratio_percent"), 0)
            entry["trigger"] = str(entry.get("trigger") or "attack").strip() or "attack"
            entry["text"] = str(entry.get("text") or "").strip()
            if entry["kind"]:
                normalized_rows.append(entry)
        payload[key] = normalized_rows
    return payload


def _normalize_scene_event_pool(raw: Any) -> list[dict[str, Any]]:
    # 兼容旧字符串写法与新结构化写法，升级后旧秘境配置也能继续读取。
    rows: list[dict[str, Any]] = []
    for item in raw or []:
        if isinstance(item, str):
            text = item.strip()
            if not text:
                continue
            rows.append(
                {
                    "name": "",
                    "description": text,
                    "event_type": "encounter",
                    "weight": 1,
                    "stone_bonus_min": 0,
                    "stone_bonus_max": 0,
                    "stone_loss_min": 0,
                    "stone_loss_max": 0,
                    "bonus_reward_kind": None,
                    "bonus_reward_ref_id": None,
                    "bonus_quantity_min": 1,
                    "bonus_quantity_max": 1,
                    "bonus_chance": 0,
                }
            )
            continue
        if not isinstance(item, dict):
            continue
        payload = _sanitize_json_value(item)
        bonus_kind = str(payload.get("bonus_reward_kind") or "").strip() or None
        if bonus_kind and bonus_kind not in ITEM_KIND_LABELS:
            bonus_kind = None
        rows.append(
            {
                "name": str(payload.get("name") or "").strip(),
                "description": str(payload.get("description") or payload.get("text") or "").strip(),
                "event_type": str(payload.get("event_type") or "encounter").strip() or "encounter",
                "weight": max(_coerce_int(payload.get("weight"), 1), 1),
                "stone_bonus_min": max(_coerce_int(payload.get("stone_bonus_min"), 0), 0),
                "stone_bonus_max": max(_coerce_int(payload.get("stone_bonus_max"), payload.get("stone_bonus_min") or 0), 0),
                "stone_loss_min": max(_coerce_int(payload.get("stone_loss_min"), 0), 0),
                "stone_loss_max": max(_coerce_int(payload.get("stone_loss_max"), payload.get("stone_loss_min") or 0), 0),
                "bonus_reward_kind": bonus_kind,
                "bonus_reward_ref_id": _coerce_int(payload.get("bonus_reward_ref_id"), 0) or None,
                "bonus_quantity_min": max(_coerce_int(payload.get("bonus_quantity_min"), 1), 1),
                "bonus_quantity_max": max(_coerce_int(payload.get("bonus_quantity_max"), payload.get("bonus_quantity_min") or 1), 1),
                "bonus_chance": max(min(_coerce_int(payload.get("bonus_chance"), 0), 100), 0),
            }
        )
    return rows


def _normalize_common_bonus_fields(fields: dict[str, Any]) -> dict[str, int]:
    return {
        "attack_bonus": _coerce_int(fields.get("attack_bonus"), 0),
        "defense_bonus": _coerce_int(fields.get("defense_bonus"), 0),
        "bone_bonus": _coerce_int(fields.get("bone_bonus"), 0),
        "comprehension_bonus": _coerce_int(fields.get("comprehension_bonus"), 0),
        "divine_sense_bonus": _coerce_int(fields.get("divine_sense_bonus"), 0),
        "fortune_bonus": _coerce_int(fields.get("fortune_bonus"), 0),
        "qi_blood_bonus": _coerce_int(fields.get("qi_blood_bonus"), 0),
        "true_yuan_bonus": _coerce_int(fields.get("true_yuan_bonus"), 0),
        "body_movement_bonus": _coerce_int(fields.get("body_movement_bonus"), 0),
    }


def _normalize_title_fields(fields: dict[str, Any]) -> dict[str, Any]:
    name = str(fields.get("name") or "").strip()
    if not name:
        raise ValueError("title name is required")
    payload = {
        "name": name,
        "description": str(fields.get("description") or "").strip(),
        "color": str(fields.get("color") or "").strip(),
        "image_url": str(fields.get("image_url") or "").strip(),
        "enabled": _coerce_bool(fields.get("enabled"), True),
        "extra_effects": fields.get("extra_effects") if isinstance(fields.get("extra_effects"), dict) else {},
    }
    payload.update(_normalize_common_bonus_fields(fields))
    payload["duel_rate_bonus"] = _coerce_int(fields.get("duel_rate_bonus"), 0)
    payload["cultivation_bonus"] = _coerce_int(fields.get("cultivation_bonus"), 0)
    payload["breakthrough_bonus"] = _coerce_int(fields.get("breakthrough_bonus"), 0)
    return payload


def _slugify_achievement_key(raw: str | None, fallback: str) -> str:
    source = str(raw or fallback or "").strip().lower()
    source = re.sub(r"[^a-z0-9_-]+", "_", source)
    source = re.sub(r"_+", "_", source).strip("_")
    return source or "achievement"


def _normalize_reward_config(raw: Any) -> dict[str, Any]:
    # 成就奖励允许后台自由编辑，但这里只保留可识别且安全的奖励字段。
    payload = dict(raw) if isinstance(raw, dict) else {}
    payload["spiritual_stone"] = max(_coerce_int(payload.get("spiritual_stone"), 0), 0)
    payload["cultivation"] = max(_coerce_int(payload.get("cultivation"), 0), 0)
    payload["titles"] = [
        int(item)
        for item in (payload.get("titles") or payload.get("title_ids") or [])
        if str(item).strip().isdigit() and int(item) > 0
    ]
    items: list[dict[str, Any]] = []
    for item in payload.get("items") or []:
        if not isinstance(item, dict):
            continue
        kind = str(item.get("kind") or item.get("item_kind") or "").strip()
        ref_id = _coerce_int(item.get("ref_id") or item.get("item_ref_id"), 0)
        quantity = max(_coerce_int(item.get("quantity"), 0), 0)
        if kind not in ITEM_KIND_LABELS or ref_id <= 0 or quantity <= 0:
            continue
        items.append(
            {
                "kind": kind,
                "ref_id": ref_id,
                "quantity": quantity,
            }
        )
    payload["items"] = items
    payload["message"] = str(payload.get("message") or "").strip()
    return payload


def _normalize_achievement_fields(fields: dict[str, Any]) -> dict[str, Any]:
    metric_key = str(fields.get("metric_key") or "").strip()
    if not metric_key:
        raise ValueError("achievement metric_key is required")
    target_value = max(int(fields.get("target_value") or 0), 1)
    name = str(fields.get("name") or "").strip()
    if not name:
        raise ValueError("achievement name is required")
    achievement_key = _slugify_achievement_key(
        fields.get("achievement_key") or fields.get("key"),
        f"{metric_key}_{target_value}",
    )
    return {
        "achievement_key": achievement_key,
        "name": name,
        "description": str(fields.get("description") or "").strip(),
        "metric_key": metric_key,
        "target_value": target_value,
        "reward_config": _normalize_reward_config(fields.get("reward_config")),
        "notify_group": _coerce_bool(fields.get("notify_group"), True),
        "notify_private": _coerce_bool(fields.get("notify_private"), True),
        "enabled": _coerce_bool(fields.get("enabled"), True),
        "sort_order": max(_coerce_int(fields.get("sort_order"), 0), 0),
    }


def _normalize_common_item_fields(fields: dict[str, Any], *, rarity_default: str = "凡品") -> dict[str, Any]:
    name = str(fields.get("name") or "").strip()
    if not name:
        raise ValueError("name is required")
    min_realm_stage = fields.get("min_realm_stage")
    return {
        "name": name,
        "rarity": normalize_quality_label(fields.get("rarity") or rarity_default),
        "image_url": str(fields.get("image_url") or "").strip(),
        "description": str(fields.get("description") or "").strip(),
        "min_realm_stage": normalize_realm_stage(min_realm_stage) if min_realm_stage else None,
        "min_realm_layer": max(_coerce_int(fields.get("min_realm_layer"), 1), 1),
        "enabled": _coerce_bool(fields.get("enabled"), True),
    }


def _normalize_artifact_fields(fields: dict[str, Any]) -> dict[str, Any]:
    payload = _normalize_common_item_fields(fields)
    payload.update(_normalize_common_bonus_fields(fields))
    payload["artifact_type"] = str(fields.get("artifact_type") or "battle").strip() or "battle"
    payload["artifact_role"] = str(fields.get("artifact_role") or payload["artifact_type"] or "battle").strip() or "battle"
    payload["equip_slot"] = str(fields.get("equip_slot") or "weapon").strip() or "weapon"
    payload["artifact_set_id"] = _coerce_int(fields.get("artifact_set_id"), 0) or None
    payload["duel_rate_bonus"] = _coerce_int(fields.get("duel_rate_bonus"), 0)
    payload["cultivation_bonus"] = _coerce_int(fields.get("cultivation_bonus"), 0)
    payload["combat_config"] = _normalize_combat_config(fields.get("combat_config"))
    return payload


def _normalize_artifact_set_fields(fields: dict[str, Any]) -> dict[str, Any]:
    name = str(fields.get("name") or "").strip()
    if not name:
        raise ValueError("artifact set name is required")
    payload = _normalize_common_bonus_fields(fields)
    payload.update(
        {
            "name": name,
            "description": str(fields.get("description") or "").strip(),
            "required_count": max(_coerce_int(fields.get("required_count"), 2), 2),
            "duel_rate_bonus": _coerce_int(fields.get("duel_rate_bonus"), 0),
            "cultivation_bonus": _coerce_int(fields.get("cultivation_bonus"), 0),
            "breakthrough_bonus": _coerce_int(fields.get("breakthrough_bonus"), 0),
            "enabled": _coerce_bool(fields.get("enabled"), True),
        }
    )
    return payload


def _normalize_sect_fields(fields: dict[str, Any]) -> dict[str, Any]:
    name = str(fields.get("name") or "").strip()
    if not name:
        raise ValueError("sect name is required")
    min_realm_stage = fields.get("min_realm_stage")
    return {
        "name": name,
        "camp": str(fields.get("camp") or "orthodox").strip() or "orthodox",
        "description": str(fields.get("description") or "").strip(),
        "image_url": str(fields.get("image_url") or "").strip(),
        "min_realm_stage": normalize_realm_stage(min_realm_stage) if min_realm_stage else None,
        "min_realm_layer": max(_coerce_int(fields.get("min_realm_layer"), 1), 1),
        "min_stone": max(_coerce_int(fields.get("min_stone"), 0), 0),
        "min_bone": max(_coerce_int(fields.get("min_bone"), 0), 0),
        "min_comprehension": max(_coerce_int(fields.get("min_comprehension"), 0), 0),
        "min_divine_sense": max(_coerce_int(fields.get("min_divine_sense"), 0), 0),
        "min_fortune": max(_coerce_int(fields.get("min_fortune"), 0), 0),
        "min_willpower": max(_coerce_int(fields.get("min_willpower"), 0), 0),
        "min_charisma": max(_coerce_int(fields.get("min_charisma"), 0), 0),
        "min_karma": max(_coerce_int(fields.get("min_karma"), 0), 0),
        "min_body_movement": max(_coerce_int(fields.get("min_body_movement"), 0), 0),
        "min_combat_power": max(_coerce_int(fields.get("min_combat_power"), 0), 0),
        "attack_bonus": _coerce_int(fields.get("attack_bonus"), 0),
        "defense_bonus": _coerce_int(fields.get("defense_bonus"), 0),
        "duel_rate_bonus": _coerce_int(fields.get("duel_rate_bonus"), 0),
        "cultivation_bonus": _coerce_int(fields.get("cultivation_bonus"), 0),
        "fortune_bonus": _coerce_int(fields.get("fortune_bonus"), 0),
        "body_movement_bonus": _coerce_int(fields.get("body_movement_bonus"), 0),
        "entry_hint": str(fields.get("entry_hint") or "").strip(),
        "enabled": _coerce_bool(fields.get("enabled"), True),
    }


def _normalize_pill_fields(fields: dict[str, Any]) -> dict[str, Any]:
    payload = _normalize_common_item_fields(fields)
    payload.update(_normalize_common_bonus_fields(fields))
    payload["pill_type"] = str(fields.get("pill_type") or "foundation").strip() or "foundation"
    payload["effect_value"] = _coerce_int(fields.get("effect_value"), 0)
    payload["poison_delta"] = _coerce_int(fields.get("poison_delta"), 0)
    return payload


def _normalize_talisman_fields(fields: dict[str, Any]) -> dict[str, Any]:
    payload = _normalize_common_item_fields(fields)
    payload.update(_normalize_common_bonus_fields(fields))
    payload["duel_rate_bonus"] = _coerce_int(fields.get("duel_rate_bonus"), 0)
    payload["effect_uses"] = max(_coerce_int(fields.get("effect_uses"), 1), 1)
    payload["combat_config"] = _normalize_combat_config(fields.get("combat_config"))
    return payload


def _normalize_technique_fields(fields: dict[str, Any]) -> dict[str, Any]:
    payload = _normalize_common_item_fields(fields)
    payload.update(_normalize_common_bonus_fields(fields))
    payload["technique_type"] = str(fields.get("technique_type") or "balanced").strip() or "balanced"
    payload["duel_rate_bonus"] = _coerce_int(fields.get("duel_rate_bonus"), 0)
    payload["cultivation_bonus"] = _coerce_int(fields.get("cultivation_bonus"), 0)
    payload["breakthrough_bonus"] = _coerce_int(fields.get("breakthrough_bonus"), 0)
    payload["combat_config"] = _normalize_combat_config(fields.get("combat_config"))
    return payload


def _sync_named_entity(model_cls, serializer, fields: dict[str, Any]) -> dict[str, Any]:
    # 默认种子按名称原地同步，避免镜像升级后后台仍显示旧数据。
    with Session() as session:
        row = session.query(model_cls).filter(model_cls.name == fields["name"]).first()
        if row is None:
            row = model_cls(**fields)
            session.add(row)
            session.commit()
            session.refresh(row)
            return serializer(row)

        changed = False
        for key, value in fields.items():
            if getattr(row, key) != value:
                setattr(row, key, value)
                changed = True
        if changed:
            session.commit()
            session.refresh(row)
        return serializer(row)


def create_artifact(**fields) -> dict[str, Any]:
    fields = _normalize_artifact_fields(dict(fields))
    with Session() as session:
        artifact = XiuxianArtifact(**fields)
        session.add(artifact)
        session.commit()
        session.refresh(artifact)
        return serialize_artifact(artifact)


def create_pill(**fields) -> dict[str, Any]:
    fields = _normalize_pill_fields(dict(fields))
    with Session() as session:
        pill = XiuxianPill(**fields)
        session.add(pill)
        session.commit()
        session.refresh(pill)
        return serialize_pill(pill)


def create_talisman(**fields) -> dict[str, Any]:
    fields = _normalize_talisman_fields(dict(fields))
    with Session() as session:
        talisman = XiuxianTalisman(**fields)
        session.add(talisman)
        session.commit()
        session.refresh(talisman)
        return serialize_talisman(talisman)


def create_technique(**fields) -> dict[str, Any]:
    fields = _normalize_technique_fields(dict(fields))
    with Session() as session:
        technique = XiuxianTechnique(**fields)
        session.add(technique)
        session.commit()
        session.refresh(technique)
        return serialize_technique(technique)


def create_artifact_set(**fields) -> dict[str, Any]:
    fields = _normalize_artifact_set_fields(dict(fields))
    with Session() as session:
        artifact_set = XiuxianArtifactSet(**fields)
        session.add(artifact_set)
        session.commit()
        session.refresh(artifact_set)
        return serialize_artifact_set(artifact_set)


def patch_artifact(artifact_id: int, **fields) -> dict[str, Any] | None:
    patch = dict(fields)
    with Session() as session:
        row = session.query(XiuxianArtifact).filter(XiuxianArtifact.id == artifact_id).first()
        if row is None:
            return None
        current = serialize_artifact(row) or {}
        current.update(patch)
        payload = _normalize_artifact_fields(current)
        for key, value in payload.items():
            setattr(row, key, value)
        row.updated_at = utcnow()
        session.commit()
        session.refresh(row)
        return serialize_artifact(row)


def patch_pill(pill_id: int, **fields) -> dict[str, Any] | None:
    patch = dict(fields)
    with Session() as session:
        row = session.query(XiuxianPill).filter(XiuxianPill.id == pill_id).first()
        if row is None:
            return None
        current = serialize_pill(row) or {}
        current.update(patch)
        payload = _normalize_pill_fields(current)
        for key, value in payload.items():
            setattr(row, key, value)
        row.updated_at = utcnow()
        session.commit()
        session.refresh(row)
        return serialize_pill(row)


def patch_talisman(talisman_id: int, **fields) -> dict[str, Any] | None:
    patch = dict(fields)
    with Session() as session:
        row = session.query(XiuxianTalisman).filter(XiuxianTalisman.id == talisman_id).first()
        if row is None:
            return None
        current = serialize_talisman(row) or {}
        current.update(patch)
        payload = _normalize_talisman_fields(current)
        for key, value in payload.items():
            setattr(row, key, value)
        row.updated_at = utcnow()
        session.commit()
        session.refresh(row)
        return serialize_talisman(row)


def patch_technique(technique_id: int, **fields) -> dict[str, Any] | None:
    patch = dict(fields)
    with Session() as session:
        row = session.query(XiuxianTechnique).filter(XiuxianTechnique.id == technique_id).first()
        if row is None:
            return None
        current = serialize_technique(row) or {}
        current.update(patch)
        payload = _normalize_technique_fields(current)
        for key, value in payload.items():
            setattr(row, key, value)
        row.updated_at = utcnow()
        session.commit()
        session.refresh(row)
        return serialize_technique(row)


def patch_artifact_set(artifact_set_id: int, **fields) -> dict[str, Any] | None:
    patch = dict(fields)
    with Session() as session:
        row = session.query(XiuxianArtifactSet).filter(XiuxianArtifactSet.id == artifact_set_id).first()
        if row is None:
            return None
        current = serialize_artifact_set(row) or {}
        current.update(patch)
        payload = _normalize_artifact_set_fields(current)
        for key, value in payload.items():
            setattr(row, key, value)
        row.updated_at = utcnow()
        session.commit()
        session.refresh(row)
        return serialize_artifact_set(row)


def sync_artifact_by_name(**fields) -> dict[str, Any]:
    return _sync_named_entity(XiuxianArtifact, serialize_artifact, _normalize_artifact_fields(dict(fields)))


def sync_pill_by_name(**fields) -> dict[str, Any]:
    return _sync_named_entity(XiuxianPill, serialize_pill, _normalize_pill_fields(dict(fields)))


def sync_talisman_by_name(**fields) -> dict[str, Any]:
    return _sync_named_entity(XiuxianTalisman, serialize_talisman, _normalize_talisman_fields(dict(fields)))


def sync_technique_by_name(**fields) -> dict[str, Any]:
    return _sync_named_entity(XiuxianTechnique, serialize_technique, _normalize_technique_fields(dict(fields)))


def sync_artifact_set_by_name(**fields) -> dict[str, Any]:
    return _sync_named_entity(XiuxianArtifactSet, serialize_artifact_set, _normalize_artifact_set_fields(dict(fields)))


def delete_artifact(artifact_id: int) -> bool:
    with Session() as session:
        row = session.query(XiuxianArtifact).filter(XiuxianArtifact.id == artifact_id).first()
        if row is None:
            return False
        session.delete(row)
        session.commit()
        return True


def delete_pill(pill_id: int) -> bool:
    with Session() as session:
        row = session.query(XiuxianPill).filter(XiuxianPill.id == pill_id).first()
        if row is None:
            return False
        session.delete(row)
        session.commit()
        return True


def delete_talisman(talisman_id: int) -> bool:
    with Session() as session:
        row = session.query(XiuxianTalisman).filter(XiuxianTalisman.id == talisman_id).first()
        if row is None:
            return False
        session.delete(row)
        session.commit()
        return True


def delete_technique(technique_id: int) -> bool:
    with Session() as session:
        row = session.query(XiuxianTechnique).filter(XiuxianTechnique.id == technique_id).first()
        if row is None:
            return False
        session.query(XiuxianProfile).filter(XiuxianProfile.current_technique_id == technique_id).update(
            {"current_technique_id": None, "updated_at": utcnow()},
            synchronize_session=False,
        )
        session.delete(row)
        session.commit()
        return True


def delete_artifact_set(artifact_set_id: int) -> bool:
    with Session() as session:
        row = session.query(XiuxianArtifactSet).filter(XiuxianArtifactSet.id == artifact_set_id).first()
        if row is None:
            return False
        session.query(XiuxianArtifact).filter(XiuxianArtifact.artifact_set_id == artifact_set_id).update(
            {"artifact_set_id": None, "updated_at": utcnow()},
            synchronize_session=False,
        )
        session.delete(row)
        session.commit()
        return True


def grant_artifact_to_user(tg: int, artifact_id: int, quantity: int = 1) -> dict[str, Any]:
    with Session() as session:
        row = (
            session.query(XiuxianArtifactInventory)
            .filter(
                XiuxianArtifactInventory.tg == tg,
                XiuxianArtifactInventory.artifact_id == artifact_id,
            )
            .first()
        )
        if row is None:
            row = XiuxianArtifactInventory(tg=tg, artifact_id=artifact_id, quantity=0)
            session.add(row)
        row.quantity += max(int(quantity), 1)
        row.bound_quantity = max(min(int(row.bound_quantity or 0), int(row.quantity or 0)), 0)
        row.updated_at = utcnow()
        session.commit()
        artifact = session.query(XiuxianArtifact).filter(XiuxianArtifact.id == artifact_id).first()
        return {
            "artifact": serialize_artifact(artifact),
            "quantity": row.quantity,
            "bound_quantity": int(row.bound_quantity or 0),
        }


def grant_pill_to_user(tg: int, pill_id: int, quantity: int = 1) -> dict[str, Any]:
    with Session() as session:
        row = (
            session.query(XiuxianPillInventory)
            .filter(
                XiuxianPillInventory.tg == tg,
                XiuxianPillInventory.pill_id == pill_id,
            )
            .first()
        )
        if row is None:
            row = XiuxianPillInventory(tg=tg, pill_id=pill_id, quantity=0)
            session.add(row)
        row.quantity += max(int(quantity), 1)
        row.updated_at = utcnow()
        session.commit()
        pill = session.query(XiuxianPill).filter(XiuxianPill.id == pill_id).first()
        return {
            "pill": serialize_pill(pill),
            "quantity": row.quantity,
        }


def grant_talisman_to_user(tg: int, talisman_id: int, quantity: int = 1) -> dict[str, Any]:
    with Session() as session:
        row = (
            session.query(XiuxianTalismanInventory)
            .filter(
                XiuxianTalismanInventory.tg == tg,
                XiuxianTalismanInventory.talisman_id == talisman_id,
            )
            .first()
        )
        if row is None:
            row = XiuxianTalismanInventory(tg=tg, talisman_id=talisman_id, quantity=0)
            session.add(row)
        row.quantity += max(int(quantity), 1)
        row.bound_quantity = max(min(int(row.bound_quantity or 0), int(row.quantity or 0)), 0)
        row.updated_at = utcnow()
        session.commit()
        talisman = session.query(XiuxianTalisman).filter(XiuxianTalisman.id == talisman_id).first()
        return {
            "talisman": serialize_talisman(talisman),
            "quantity": row.quantity,
            "bound_quantity": int(row.bound_quantity or 0),
        }


def list_user_artifacts(tg: int) -> list[dict[str, Any]]:
    with Session() as session:
        rows = (
            session.query(XiuxianArtifactInventory, XiuxianArtifact)
            .join(XiuxianArtifact, XiuxianArtifact.id == XiuxianArtifactInventory.artifact_id)
            .filter(XiuxianArtifactInventory.tg == tg)
            .order_by(XiuxianArtifact.id.desc())
            .all()
        )
        return [
            {
                "quantity": inventory.quantity,
                "bound_quantity": max(min(int(inventory.bound_quantity or 0), int(inventory.quantity or 0)), 0),
                "artifact": serialize_artifact(artifact),
            }
            for inventory, artifact in rows
        ]


def list_equipped_artifacts(tg: int) -> list[dict[str, Any]]:
    with Session() as session:
        rows = (
            session.query(XiuxianEquippedArtifact, XiuxianArtifact)
            .join(XiuxianArtifact, XiuxianArtifact.id == XiuxianEquippedArtifact.artifact_id)
            .filter(XiuxianEquippedArtifact.tg == tg)
            .order_by(XiuxianEquippedArtifact.slot.asc(), XiuxianEquippedArtifact.id.asc())
            .all()
        )
        return [
            {
                "slot": equipped.slot,
                "artifact": serialize_artifact(artifact),
            }
            for equipped, artifact in rows
        ]


def plunder_random_artifact_to_user(receiver_tg: int, owner_tg: int) -> dict[str, Any] | None:
    if receiver_tg == owner_tg:
        raise ValueError("不能从自己身上掠夺法宝。")

    with Session() as session:
        owner_profile = session.query(XiuxianProfile).filter(XiuxianProfile.tg == owner_tg).with_for_update().first()
        receiver_profile = session.query(XiuxianProfile).filter(XiuxianProfile.tg == receiver_tg).with_for_update().first()
        if owner_profile is None or receiver_profile is None:
            return None

        owner_rows = (
            session.query(XiuxianArtifactInventory)
            .filter(XiuxianArtifactInventory.tg == owner_tg)
            .with_for_update()
            .all()
        )
        if not owner_rows:
            return None

        weighted_ids: list[int] = []
        for row in owner_rows:
            total_quantity = int(row.quantity or 0)
            bound_quantity = max(min(int(row.bound_quantity or 0), total_quantity), 0)
            weighted_ids.extend([int(row.artifact_id)] * max(total_quantity - bound_quantity, 0))
        if not weighted_ids:
            return None

        artifact_id = random.choice(weighted_ids)
        owner_row = next((row for row in owner_rows if int(row.artifact_id) == artifact_id), None)
        if owner_row is None:
            return None

        equipped_rows = (
            session.query(XiuxianEquippedArtifact)
            .filter(XiuxianEquippedArtifact.tg == owner_tg)
            .order_by(XiuxianEquippedArtifact.slot.asc(), XiuxianEquippedArtifact.id.asc())
            .with_for_update()
            .all()
        )
        equipped_row = next((row for row in equipped_rows if int(row.artifact_id) == artifact_id), None)

        owner_row.quantity = max(int(owner_row.quantity or 0) - 1, 0)
        owner_row.bound_quantity = max(min(int(owner_row.bound_quantity or 0), int(owner_row.quantity or 0)), 0)
        owner_row.updated_at = utcnow()

        was_equipped = False
        if equipped_row is not None and int(owner_row.quantity or 0) < 1:
            session.delete(equipped_row)
            session.flush()
            was_equipped = True

        if int(owner_row.quantity or 0) <= 0:
            session.delete(owner_row)

        receiver_row = (
            session.query(XiuxianArtifactInventory)
            .filter(
                XiuxianArtifactInventory.tg == receiver_tg,
                XiuxianArtifactInventory.artifact_id == artifact_id,
            )
            .first()
        )
        if receiver_row is None:
            receiver_row = XiuxianArtifactInventory(tg=receiver_tg, artifact_id=artifact_id, quantity=0)
            session.add(receiver_row)
        receiver_row.quantity += 1
        receiver_row.bound_quantity = max(min(int(receiver_row.bound_quantity or 0), int(receiver_row.quantity or 0)), 0)
        receiver_row.updated_at = utcnow()

        refreshed_equipped = (
            session.query(XiuxianEquippedArtifact)
            .filter(XiuxianEquippedArtifact.tg == owner_tg)
            .order_by(XiuxianEquippedArtifact.slot.asc(), XiuxianEquippedArtifact.id.asc())
            .all()
        )
        for index, row in enumerate(refreshed_equipped, start=1):
            row.slot = index

        owner_profile.current_artifact_id = refreshed_equipped[0].artifact_id if refreshed_equipped else None
        owner_profile.updated_at = utcnow()
        receiver_profile.updated_at = utcnow()

        artifact = session.query(XiuxianArtifact).filter(XiuxianArtifact.id == artifact_id).first()
        owner_remaining = max(int(owner_row.quantity or 0), 0)
        receiver_quantity = int(receiver_row.quantity or 0)
        session.commit()
        return {
            "artifact": serialize_artifact(artifact),
            "was_equipped": was_equipped,
            "owner_remaining": owner_remaining,
            "receiver_quantity": receiver_quantity,
        }


def list_user_pills(tg: int) -> list[dict[str, Any]]:
    with Session() as session:
        rows = (
            session.query(XiuxianPillInventory, XiuxianPill)
            .join(XiuxianPill, XiuxianPill.id == XiuxianPillInventory.pill_id)
            .filter(XiuxianPillInventory.tg == tg)
            .order_by(XiuxianPill.id.desc())
            .all()
        )
        return [
            {
                "quantity": inventory.quantity,
                "pill": serialize_pill(pill),
            }
            for inventory, pill in rows
        ]


def list_user_talismans(tg: int) -> list[dict[str, Any]]:
    with Session() as session:
        rows = (
            session.query(XiuxianTalismanInventory, XiuxianTalisman)
            .join(XiuxianTalisman, XiuxianTalisman.id == XiuxianTalismanInventory.talisman_id)
            .filter(XiuxianTalismanInventory.tg == tg)
            .order_by(XiuxianTalisman.id.desc())
            .all()
        )
        return [
            {
                "quantity": inventory.quantity,
                "bound_quantity": max(min(int(inventory.bound_quantity or 0), int(inventory.quantity or 0)), 0),
                "talisman": serialize_talisman(talisman),
            }
            for inventory, talisman in rows
        ]


def consume_user_pill(tg: int, pill_id: int, quantity: int = 1) -> bool:
    with Session() as session:
        row = (
            session.query(XiuxianPillInventory)
            .filter(
                XiuxianPillInventory.tg == tg,
                XiuxianPillInventory.pill_id == pill_id,
            )
            .with_for_update()
            .first()
        )
        if row is None or row.quantity < quantity:
            return False

        row.quantity -= quantity
        row.updated_at = utcnow()
        if row.quantity <= 0:
            session.delete(row)
        session.commit()
        return True


def consume_user_talisman(tg: int, talisman_id: int, quantity: int = 1) -> bool:
    with Session() as session:
        row = (
            session.query(XiuxianTalismanInventory)
            .filter(
                XiuxianTalismanInventory.tg == tg,
                XiuxianTalismanInventory.talisman_id == talisman_id,
            )
            .with_for_update()
            .first()
        )
        if row is None or row.quantity < quantity:
            return False

        row.quantity -= quantity
        row.bound_quantity = max(min(int(row.bound_quantity or 0), int(row.quantity or 0)), 0)
        row.updated_at = utcnow()
        if row.quantity <= 0:
            session.delete(row)
        session.commit()
        return True


def admin_set_user_artifact_inventory(
    tg: int,
    artifact_id: int,
    quantity: int,
    bound_quantity: int | None = None,
) -> dict[str, Any]:
    target_quantity = max(int(quantity or 0), 0)
    desired_bound = max(int(bound_quantity or 0), 0) if bound_quantity is not None else None
    with Session() as session:
        artifact = session.query(XiuxianArtifact).filter(XiuxianArtifact.id == artifact_id).first()
        if artifact is None:
            raise ValueError("artifact not found")
        profile = session.query(XiuxianProfile).filter(XiuxianProfile.tg == tg).with_for_update().first()
        if profile is None:
            profile = XiuxianProfile(tg=tg)
            session.add(profile)
            session.flush()
        row = (
            session.query(XiuxianArtifactInventory)
            .filter(XiuxianArtifactInventory.tg == tg, XiuxianArtifactInventory.artifact_id == artifact_id)
            .with_for_update()
            .first()
        )
        equipped_rows = (
            session.query(XiuxianEquippedArtifact)
            .filter(XiuxianEquippedArtifact.tg == tg, XiuxianEquippedArtifact.artifact_id == artifact_id)
            .order_by(XiuxianEquippedArtifact.slot.asc(), XiuxianEquippedArtifact.id.asc())
            .with_for_update()
            .all()
        )
        if target_quantity < len(equipped_rows):
            for equipped_row in equipped_rows[target_quantity:]:
                session.delete(equipped_row)
            session.flush()
            equipped_rows = equipped_rows[:target_quantity]
        if target_quantity <= 0:
            if row is not None:
                session.delete(row)
        else:
            if row is None:
                row = XiuxianArtifactInventory(tg=tg, artifact_id=artifact_id, quantity=0, bound_quantity=0)
                session.add(row)
            row.quantity = target_quantity
            max_bound = max(target_quantity - len(equipped_rows), 0)
            applied_bound = int(row.bound_quantity or 0) if desired_bound is None else desired_bound
            row.bound_quantity = max(min(applied_bound, max_bound), 0)
            row.updated_at = utcnow()
        refreshed_equipped = (
            session.query(XiuxianEquippedArtifact)
            .filter(XiuxianEquippedArtifact.tg == tg)
            .order_by(XiuxianEquippedArtifact.slot.asc(), XiuxianEquippedArtifact.id.asc())
            .all()
        )
        for index, equipped_row in enumerate(refreshed_equipped, start=1):
            equipped_row.slot = index
        profile.current_artifact_id = refreshed_equipped[0].artifact_id if refreshed_equipped else None
        profile.updated_at = utcnow()
        session.commit()
        applied_bound = 0
        if target_quantity > 0:
            refreshed_row = (
                session.query(XiuxianArtifactInventory)
                .filter(XiuxianArtifactInventory.tg == tg, XiuxianArtifactInventory.artifact_id == artifact_id)
                .first()
            )
            applied_bound = int(refreshed_row.bound_quantity or 0) if refreshed_row is not None else 0
        return {
            "artifact": serialize_artifact(artifact),
            "quantity": target_quantity,
            "bound_quantity": applied_bound,
            "equipped_count": len([row for row in refreshed_equipped if int(row.artifact_id) == int(artifact_id)]),
        }


def admin_set_user_pill_inventory(tg: int, pill_id: int, quantity: int) -> dict[str, Any]:
    target_quantity = max(int(quantity or 0), 0)
    with Session() as session:
        pill = session.query(XiuxianPill).filter(XiuxianPill.id == pill_id).first()
        if pill is None:
            raise ValueError("pill not found")
        row = (
            session.query(XiuxianPillInventory)
            .filter(XiuxianPillInventory.tg == tg, XiuxianPillInventory.pill_id == pill_id)
            .with_for_update()
            .first()
        )
        if target_quantity <= 0:
            if row is not None:
                session.delete(row)
        else:
            if row is None:
                row = XiuxianPillInventory(tg=tg, pill_id=pill_id, quantity=0)
                session.add(row)
            row.quantity = target_quantity
            row.updated_at = utcnow()
        session.commit()
        return {
            "pill": serialize_pill(pill),
            "quantity": target_quantity,
        }


def admin_set_user_talisman_inventory(
    tg: int,
    talisman_id: int,
    quantity: int,
    bound_quantity: int | None = None,
) -> dict[str, Any]:
    target_quantity = max(int(quantity or 0), 0)
    with Session() as session:
        talisman = session.query(XiuxianTalisman).filter(XiuxianTalisman.id == talisman_id).first()
        if talisman is None:
            raise ValueError("talisman not found")
        profile = session.query(XiuxianProfile).filter(XiuxianProfile.tg == tg).with_for_update().first()
        if profile is None:
            profile = XiuxianProfile(tg=tg)
            session.add(profile)
            session.flush()
        row = (
            session.query(XiuxianTalismanInventory)
            .filter(XiuxianTalismanInventory.tg == tg, XiuxianTalismanInventory.talisman_id == talisman_id)
            .with_for_update()
            .first()
        )
        desired_bound = max(int(bound_quantity or 0), 0) if bound_quantity is not None else (int(row.bound_quantity or 0) if row is not None else 0)
        if target_quantity <= 0:
            if row is not None:
                session.delete(row)
            if int(profile.active_talisman_id or 0) == int(talisman_id):
                profile.active_talisman_id = None
        else:
            if row is None:
                row = XiuxianTalismanInventory(tg=tg, talisman_id=talisman_id, quantity=0, bound_quantity=0)
                session.add(row)
            row.quantity = target_quantity
            row.bound_quantity = max(min(desired_bound, target_quantity), 0)
            row.updated_at = utcnow()
        profile.updated_at = utcnow()
        session.commit()
        return {
            "talisman": serialize_talisman(talisman),
            "quantity": target_quantity,
            "bound_quantity": 0 if target_quantity <= 0 else max(min(desired_bound, target_quantity), 0),
            "active": int(profile.active_talisman_id or 0) == int(talisman_id),
        }


def admin_set_user_material_inventory(tg: int, material_id: int, quantity: int) -> dict[str, Any]:
    target_quantity = max(int(quantity or 0), 0)
    with Session() as session:
        material = session.query(XiuxianMaterial).filter(XiuxianMaterial.id == material_id).first()
        if material is None:
            raise ValueError("material not found")
        row = (
            session.query(XiuxianMaterialInventory)
            .filter(XiuxianMaterialInventory.tg == tg, XiuxianMaterialInventory.material_id == material_id)
            .with_for_update()
            .first()
        )
        if target_quantity <= 0:
            if row is not None:
                session.delete(row)
        else:
            if row is None:
                row = XiuxianMaterialInventory(tg=tg, material_id=material_id, quantity=0)
                session.add(row)
            row.quantity = target_quantity
            row.updated_at = utcnow()
        session.commit()
        return {
            "material": serialize_material(material),
            "quantity": target_quantity,
        }


def use_user_artifact_listing_stock(tg: int, artifact_id: int, quantity: int = 1) -> bool:
    with Session() as session:
        row = (
            session.query(XiuxianArtifactInventory)
            .filter(
                XiuxianArtifactInventory.tg == tg,
                XiuxianArtifactInventory.artifact_id == artifact_id,
            )
            .with_for_update()
            .first()
        )
        if row is None or row.quantity < quantity:
            return False
        bound_quantity = max(min(int(row.bound_quantity or 0), int(row.quantity or 0)), 0)
        equipped_count = (
            session.query(XiuxianEquippedArtifact)
            .filter(
                XiuxianEquippedArtifact.tg == tg,
                XiuxianEquippedArtifact.artifact_id == artifact_id,
            )
            .count()
        )
        available_quantity = int(row.quantity or 0) - bound_quantity - int(equipped_count or 0)
        if available_quantity < quantity:
            return False

        row.quantity -= quantity
        row.updated_at = utcnow()
        if row.quantity <= 0:
            session.delete(row)
        session.commit()
        return True


def use_user_pill_listing_stock(tg: int, pill_id: int, quantity: int = 1) -> bool:
    with Session() as session:
        row = (
            session.query(XiuxianPillInventory)
            .filter(
                XiuxianPillInventory.tg == tg,
                XiuxianPillInventory.pill_id == pill_id,
            )
            .with_for_update()
            .first()
        )
        if row is None or row.quantity < quantity:
            return False

        row.quantity -= quantity
        row.updated_at = utcnow()
        if row.quantity <= 0:
            session.delete(row)
        session.commit()
        return True


def use_user_material_listing_stock(tg: int, material_id: int, quantity: int = 1) -> bool:
    with Session() as session:
        row = (
            session.query(XiuxianMaterialInventory)
            .filter(
                XiuxianMaterialInventory.tg == tg,
                XiuxianMaterialInventory.material_id == material_id,
            )
            .with_for_update()
            .first()
        )
        if row is None or row.quantity < quantity:
            return False

        row.quantity -= quantity
        row.updated_at = utcnow()
        if row.quantity <= 0:
            session.delete(row)
        session.commit()
        return True


def use_user_talisman_listing_stock(tg: int, talisman_id: int, quantity: int = 1) -> bool:
    with Session() as session:
        row = (
            session.query(XiuxianTalismanInventory)
            .filter(
                XiuxianTalismanInventory.tg == tg,
                XiuxianTalismanInventory.talisman_id == talisman_id,
            )
            .with_for_update()
            .first()
        )
        if row is None or row.quantity < quantity:
            return False
        bound_quantity = max(min(int(row.bound_quantity or 0), int(row.quantity or 0)), 0)
        available_quantity = int(row.quantity or 0) - bound_quantity
        if available_quantity < quantity:
            return False

        row.quantity -= quantity
        row.updated_at = utcnow()
        if row.quantity <= 0:
            session.delete(row)
        session.commit()
        return True


def bind_user_artifact(tg: int, artifact_id: int, quantity: int = 1) -> dict[str, Any]:
    amount = max(int(quantity or 0), 1)
    with Session() as session:
        row = (
            session.query(XiuxianArtifactInventory)
            .filter(
                XiuxianArtifactInventory.tg == tg,
                XiuxianArtifactInventory.artifact_id == artifact_id,
            )
            .with_for_update()
            .first()
        )
        if row is None:
            raise ValueError("你的背包里没有这件法宝。")
        bound_quantity = max(min(int(row.bound_quantity or 0), int(row.quantity or 0)), 0)
        bindable_quantity = int(row.quantity or 0) - bound_quantity
        if bindable_quantity < amount:
            raise ValueError("没有足够的未绑定法宝可供绑定。")
        row.bound_quantity = bound_quantity + amount
        row.updated_at = utcnow()
        session.commit()
        return {
            "quantity": int(row.quantity or 0),
            "bound_quantity": int(row.bound_quantity or 0),
        }


def unbind_user_artifact(tg: int, artifact_id: int, cost: int, quantity: int = 1) -> dict[str, Any]:
    amount = max(int(quantity or 0), 1)
    unit_cost = max(int(cost or 0), 0)
    total_cost = unit_cost * amount
    with Session() as session:
        profile = session.query(XiuxianProfile).filter(XiuxianProfile.tg == tg).with_for_update().first()
        row = (
            session.query(XiuxianArtifactInventory)
            .filter(
                XiuxianArtifactInventory.tg == tg,
                XiuxianArtifactInventory.artifact_id == artifact_id,
            )
            .with_for_update()
            .first()
        )
        if profile is None or row is None:
            raise ValueError("你的背包里没有这件法宝。")
        bound_quantity = max(min(int(row.bound_quantity or 0), int(row.quantity or 0)), 0)
        if bound_quantity < amount:
            raise ValueError("没有足够的已绑定法宝可供解绑。")
        if int(profile.spiritual_stone or 0) < total_cost:
            raise ValueError(f"灵石不足，解绑需要 {total_cost} 灵石。")
        profile.spiritual_stone = max(int(profile.spiritual_stone or 0) - total_cost, 0)
        profile.updated_at = utcnow()
        row.bound_quantity = bound_quantity - amount
        row.updated_at = utcnow()
        session.commit()
        return {
            "quantity": int(row.quantity or 0),
            "bound_quantity": int(row.bound_quantity or 0),
            "cost": total_cost,
            "balance": int(profile.spiritual_stone or 0),
        }


def bind_user_talisman(tg: int, talisman_id: int, quantity: int = 1) -> dict[str, Any]:
    amount = max(int(quantity or 0), 1)
    with Session() as session:
        row = (
            session.query(XiuxianTalismanInventory)
            .filter(
                XiuxianTalismanInventory.tg == tg,
                XiuxianTalismanInventory.talisman_id == talisman_id,
            )
            .with_for_update()
            .first()
        )
        if row is None:
            raise ValueError("你的背包里没有这张符箓。")
        bound_quantity = max(min(int(row.bound_quantity or 0), int(row.quantity or 0)), 0)
        bindable_quantity = int(row.quantity or 0) - bound_quantity
        if bindable_quantity < amount:
            raise ValueError("没有足够的未绑定符箓可供绑定。")
        row.bound_quantity = bound_quantity + amount
        row.updated_at = utcnow()
        session.commit()
        return {
            "quantity": int(row.quantity or 0),
            "bound_quantity": int(row.bound_quantity or 0),
        }


def unbind_user_talisman(tg: int, talisman_id: int, cost: int, quantity: int = 1) -> dict[str, Any]:
    amount = max(int(quantity or 0), 1)
    unit_cost = max(int(cost or 0), 0)
    total_cost = unit_cost * amount
    with Session() as session:
        profile = session.query(XiuxianProfile).filter(XiuxianProfile.tg == tg).with_for_update().first()
        row = (
            session.query(XiuxianTalismanInventory)
            .filter(
                XiuxianTalismanInventory.tg == tg,
                XiuxianTalismanInventory.talisman_id == talisman_id,
            )
            .with_for_update()
            .first()
        )
        if profile is None or row is None:
            raise ValueError("你的背包里没有这张符箓。")
        bound_quantity = max(min(int(row.bound_quantity or 0), int(row.quantity or 0)), 0)
        if bound_quantity < amount:
            raise ValueError("没有足够的已绑定符箓可供解绑。")
        if int(profile.spiritual_stone or 0) < total_cost:
            raise ValueError(f"灵石不足，解绑需要 {total_cost} 灵石。")
        profile.spiritual_stone = max(int(profile.spiritual_stone or 0) - total_cost, 0)
        profile.updated_at = utcnow()
        row.bound_quantity = bound_quantity - amount
        row.updated_at = utcnow()
        session.commit()
        return {
            "quantity": int(row.quantity or 0),
            "bound_quantity": int(row.bound_quantity or 0),
            "cost": total_cost,
            "balance": int(profile.spiritual_stone or 0),
        }


def set_equipped_artifact(tg: int, artifact_id: int, equip_limit: int = 3) -> dict[str, Any] | None:
    with Session() as session:
        profile = session.query(XiuxianProfile).filter(XiuxianProfile.tg == tg).with_for_update().first()
        if profile is None:
            return None
        artifact = session.query(XiuxianArtifact).filter(XiuxianArtifact.id == artifact_id).first()
        if artifact is None:
            return None

        equipped_rows = (
            session.query(XiuxianEquippedArtifact)
            .filter(XiuxianEquippedArtifact.tg == tg)
            .order_by(XiuxianEquippedArtifact.slot.asc(), XiuxianEquippedArtifact.id.asc())
            .with_for_update()
            .all()
        )
        existing = next((row for row in equipped_rows if row.artifact_id == artifact_id), None)
        action = "equipped"
        replaced_artifact_id = None

        if existing is not None:
            session.delete(existing)
            session.flush()
            action = "unequipped"
        else:
            slot_conflict = None
            for row in equipped_rows:
                equipped_artifact = session.query(XiuxianArtifact).filter(XiuxianArtifact.id == row.artifact_id).first()
                if equipped_artifact and str(equipped_artifact.equip_slot or "") == str(artifact.equip_slot or ""):
                    slot_conflict = row
                    break
            if slot_conflict is not None:
                replaced_artifact_id = int(slot_conflict.artifact_id)
                session.delete(slot_conflict)
                session.flush()
                equipped_rows = [row for row in equipped_rows if row.id != slot_conflict.id]
            safe_limit = max(int(equip_limit or 0), 1)
            if len(equipped_rows) >= safe_limit:
                raise ValueError(f"当前最多只能装备 {safe_limit} 件法宝。")
            used_slots = {row.slot for row in equipped_rows}
            slot = 1
            while slot in used_slots:
                slot += 1
            session.add(XiuxianEquippedArtifact(tg=tg, artifact_id=artifact_id, slot=slot))
            session.flush()

        refreshed = (
            session.query(XiuxianEquippedArtifact)
            .filter(XiuxianEquippedArtifact.tg == tg)
            .order_by(XiuxianEquippedArtifact.slot.asc(), XiuxianEquippedArtifact.id.asc())
            .all()
        )
        for index, row in enumerate(refreshed, start=1):
            row.slot = index

        profile.current_artifact_id = refreshed[0].artifact_id if refreshed else None
        profile.updated_at = utcnow()
        session.commit()
        session.refresh(profile)
        return {
            "profile": serialize_profile(profile),
            "action": action,
            "replaced_artifact_id": replaced_artifact_id,
            "equipped_count": len(refreshed),
            "equipped_artifact_ids": [row.artifact_id for row in refreshed],
        }


def set_active_talisman(tg: int, talisman_id: int | None) -> dict[str, Any] | None:
    with Session() as session:
        profile = session.query(XiuxianProfile).filter(XiuxianProfile.tg == tg).first()
        if profile is None:
            return None

        profile.active_talisman_id = talisman_id
        profile.updated_at = utcnow()
        session.commit()
        session.refresh(profile)
        return serialize_profile(profile)


def set_current_technique(tg: int, technique_id: int | None) -> dict[str, Any] | None:
    with Session() as session:
        profile = session.query(XiuxianProfile).filter(XiuxianProfile.tg == tg).first()
        if profile is None:
            return None
        profile.current_technique_id = technique_id
        profile.updated_at = utcnow()
        session.commit()
        session.refresh(profile)
        return serialize_profile(profile)


def list_shop_items(
    owner_tg: int | None = None,
    official_only: bool | None = None,
    include_disabled: bool = False,
) -> list[dict[str, Any]]:
    with Session() as session:
        query = session.query(XiuxianShopItem)
        if not include_disabled:
            query = query.filter(XiuxianShopItem.enabled.is_(True))
        if owner_tg is not None:
            query = query.filter(XiuxianShopItem.owner_tg == owner_tg)
        if official_only is True:
            query = query.filter(XiuxianShopItem.is_official.is_(True))
        elif official_only is False:
            query = query.filter(XiuxianShopItem.is_official.is_(False))

        return [serialize_shop_item(item) for item in query.order_by(XiuxianShopItem.id.desc()).all()]


def create_shop_item(
    *,
    owner_tg: int | None,
    shop_name: str,
    item_kind: str,
    item_ref_id: int,
    item_name: str,
    quantity: int,
    price_stone: int,
    is_official: bool,
) -> dict[str, Any]:
    with Session() as session:
        item = XiuxianShopItem(
            owner_tg=owner_tg,
            shop_name=shop_name,
            item_kind=item_kind,
            item_ref_id=item_ref_id,
            item_name=item_name,
            quantity=max(int(quantity), 1),
            price_stone=max(int(price_stone), 0),
            is_official=is_official,
            enabled=True,
        )
        session.add(item)
        session.commit()
        session.refresh(item)
        return serialize_shop_item(item)


def sync_official_shop_name(shop_name: str) -> int:
    resolved_name = str(shop_name or "").strip() or DEFAULT_SETTINGS["official_shop_name"]
    with Session() as session:
        rows = session.query(XiuxianShopItem).filter(XiuxianShopItem.is_official.is_(True)).all()
        changed = 0
        for row in rows:
            if row.shop_name == resolved_name:
                continue
            row.shop_name = resolved_name
            row.updated_at = utcnow()
            changed += 1
        session.commit()
        return changed


def update_shop_item(item_id: int, **fields) -> dict[str, Any] | None:
    with Session() as session:
        item = session.query(XiuxianShopItem).filter(XiuxianShopItem.id == item_id).first()
        if item is None:
            return None
        for key, value in fields.items():
            setattr(item, key, value)
        item.updated_at = utcnow()
        session.commit()
        session.refresh(item)
        return serialize_shop_item(item)


def purchase_shop_item(buyer_tg: int, item_id: int, quantity: int = 1) -> dict[str, Any]:
    with Session() as session:
        item = (
            session.query(XiuxianShopItem)
            .filter(XiuxianShopItem.id == item_id, XiuxianShopItem.enabled.is_(True))
            .with_for_update()
            .first()
        )
        if item is None:
            raise ValueError("商品不存在或已下架")

        amount = max(int(quantity), 1)
        if item.quantity < amount:
            raise ValueError("商品库存不足")

        buyer = (
            session.query(XiuxianProfile)
            .filter(XiuxianProfile.tg == buyer_tg)
            .with_for_update()
            .first()
        )
        if buyer is None or not buyer.consented:
            raise ValueError("买家尚未踏入仙途")

        total_cost = item.price_stone * amount
        if buyer.spiritual_stone < total_cost:
            raise ValueError("灵石不足")

        buyer.spiritual_stone -= total_cost
        buyer.updated_at = utcnow()

        seller = None
        if item.owner_tg is not None:
            seller = (
                session.query(XiuxianProfile)
                .filter(XiuxianProfile.tg == item.owner_tg)
                .with_for_update()
                .first()
            )
            if seller is not None:
                seller.spiritual_stone += total_cost
                seller.updated_at = utcnow()

        seller_tg = item.owner_tg
        item.quantity -= amount
        item.updated_at = utcnow()
        if item.quantity <= 0:
            item.enabled = False

        if item.item_kind == "artifact":
            row = (
                session.query(XiuxianArtifactInventory)
                .filter(
                    XiuxianArtifactInventory.tg == buyer_tg,
                    XiuxianArtifactInventory.artifact_id == item.item_ref_id,
                )
                .first()
            )
            if row is None:
                row = XiuxianArtifactInventory(tg=buyer_tg, artifact_id=item.item_ref_id, quantity=0)
                session.add(row)
            row.quantity += amount
            row.updated_at = utcnow()
        elif item.item_kind == "pill":
            row = (
                session.query(XiuxianPillInventory)
                .filter(
                    XiuxianPillInventory.tg == buyer_tg,
                    XiuxianPillInventory.pill_id == item.item_ref_id,
                )
                .first()
            )
            if row is None:
                row = XiuxianPillInventory(tg=buyer_tg, pill_id=item.item_ref_id, quantity=0)
                session.add(row)
            row.quantity += amount
            row.updated_at = utcnow()
        elif item.item_kind == "talisman":
            row = (
                session.query(XiuxianTalismanInventory)
                .filter(
                    XiuxianTalismanInventory.tg == buyer_tg,
                    XiuxianTalismanInventory.talisman_id == item.item_ref_id,
                )
                .first()
            )
            if row is None:
                row = XiuxianTalismanInventory(tg=buyer_tg, talisman_id=item.item_ref_id, quantity=0)
                session.add(row)
            row.quantity += amount
            row.updated_at = utcnow()
        elif item.item_kind == "material":
            row = (
                session.query(XiuxianMaterialInventory)
                .filter(
                    XiuxianMaterialInventory.tg == buyer_tg,
                    XiuxianMaterialInventory.material_id == item.item_ref_id,
                )
                .first()
            )
            if row is None:
                row = XiuxianMaterialInventory(tg=buyer_tg, material_id=item.item_ref_id, quantity=0)
                session.add(row)
            row.quantity += amount
            row.updated_at = utcnow()
        else:
            raise ValueError("不支持的商品类型")

        session.flush()
        serialized_item = serialize_shop_item(item)
        buyer_balance = int(buyer.spiritual_stone or 0)
        seller_balance = None if seller is None else int(seller.spiritual_stone or 0)
        session.commit()

    name_map = get_emby_name_map([buyer_tg] + ([seller_tg] if seller_tg else []))
    return {
        "item": serialized_item,
        "buyer_balance": buyer_balance,
        "seller_balance": seller_balance,
        "total_cost": total_cost,
        "buyer_tg": buyer_tg,
        "buyer_name": name_map.get(buyer_tg, f"TG {buyer_tg}"),
        "seller_tg": seller_tg,
        "seller_name": name_map.get(seller_tg, f"TG {seller_tg}") if seller_tg else None,
    }


def create_duel_record(
    challenger_tg: int,
    defender_tg: int,
    winner_tg: int,
    loser_tg: int,
    challenger_rate: int,
    defender_rate: int,
    summary: str,
    duel_mode: str = "standard",
    battle_log: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    with Session() as session:
        record = XiuxianDuelRecord(
            challenger_tg=challenger_tg,
            defender_tg=defender_tg,
            winner_tg=winner_tg,
            loser_tg=loser_tg,
            duel_mode=str(duel_mode or "standard"),
            challenger_rate=challenger_rate,
            defender_rate=defender_rate,
            summary=summary,
            battle_log=_sanitize_json_value(battle_log) if battle_log else [],
        )
        session.add(record)
        session.commit()
        session.refresh(record)
        return {
            "id": record.id,
            "challenger_tg": record.challenger_tg,
            "defender_tg": record.defender_tg,
            "winner_tg": record.winner_tg,
            "loser_tg": record.loser_tg,
            "duel_mode": record.duel_mode,
            "challenger_rate": record.challenger_rate,
            "defender_rate": record.defender_rate,
            "summary": record.summary,
            "battle_log": _sanitize_json_value(record.battle_log) or [],
            "created_at": serialize_datetime(record.created_at),
        }


def get_emby_name_map(tgs: list[int]) -> dict[int, str]:
    if not tgs:
        return {}

    with Session() as session:
        mapping: dict[int, str] = {}
        profiles = session.query(XiuxianProfile).filter(XiuxianProfile.tg.in_(tgs)).all()
        for profile in profiles:
            label = profile.display_name or (f"@{profile.username}" if profile.username else None)
            if label:
                mapping[int(profile.tg)] = label
        emby_rows = session.query(Emby).filter(Emby.tg.in_(tgs)).all()
        for row in emby_rows:
            mapping.setdefault(int(row.tg), row.name or row.embyid or f"TG {row.tg}")
        for tg in tgs:
            mapping.setdefault(int(tg), f"TG {tg}")
        return mapping


def get_emby_account_map(tgs: list[int]) -> dict[int, dict[str, Any]]:
    if not tgs:
        return {}

    with Session() as session:
        rows = session.query(Emby).filter(Emby.tg.in_(tgs)).all()
        return {int(row.tg): serialize_emby_account(row) for row in rows}


def get_emby_account(tg: int) -> dict[str, Any] | None:
    with Session() as session:
        row = session.query(Emby).filter(Emby.tg == tg).first()
        return serialize_emby_account(row)


def list_profiles() -> list[XiuxianProfile]:
    with Session() as session:
        return session.query(XiuxianProfile).filter(XiuxianProfile.consented.is_(True)).all()


def list_slave_profiles(master_tg: int) -> list[dict[str, Any]]:
    with Session() as session:
        rows = (
            session.query(XiuxianProfile)
            .filter(
                XiuxianProfile.master_tg == int(master_tg),
                XiuxianProfile.consented.is_(True),
            )
            .order_by(XiuxianProfile.updated_at.desc(), XiuxianProfile.tg.asc())
            .all()
        )
        return [serialize_profile(row) for row in rows]


def search_profiles(
    query: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> dict[str, Any]:
    page = max(int(page or 1), 1)
    page_size = max(min(int(page_size or 20), 50), 1)
    offset = (page - 1) * page_size
    with Session() as session:
        q = session.query(XiuxianProfile).outerjoin(Emby, Emby.tg == XiuxianProfile.tg).filter(XiuxianProfile.consented.is_(True))
        if query and query.strip():
            keyword = query.strip()
            normalized_keyword = keyword.lstrip("@")
            if keyword.isdigit():
                q = q.filter(or_(XiuxianProfile.tg == int(keyword), Emby.embyid == keyword))
            else:
                pattern = f"%{keyword}%"
                account_pattern = f"%{normalized_keyword}%"
                q = q.filter(
                    or_(
                        XiuxianProfile.display_name.ilike(pattern),
                        XiuxianProfile.username.ilike(account_pattern),
                        Emby.name.ilike(pattern),
                        Emby.embyid.ilike(account_pattern),
                    )
                )
        total = q.count()
        rows = q.order_by(XiuxianProfile.updated_at.desc()).offset(offset).limit(page_size).all()
        account_map = get_emby_account_map([int(row.tg) for row in rows])
        return {
            "total": total,
            "page": page,
            "page_size": page_size,
            "items": [
                {
                    **serialize_profile(row),
                    "emby_account": account_map.get(int(row.tg)),
                }
                for row in rows
            ],
        }


ADMIN_EDITABLE_PROFILE_FIELDS = {
    "spiritual_stone", "cultivation", "realm_stage", "realm_layer",
    "bone", "comprehension", "divine_sense", "fortune", "willpower", "charisma", "karma",
    "qi_blood", "true_yuan", "body_movement", "attack_power", "defense_power",
    "insight_bonus", "dan_poison", "sect_contribution",
    "technique_capacity",
    "display_name", "username",
    "root_type", "root_primary", "root_secondary", "root_relation",
    "root_bonus", "root_quality", "root_quality_level", "root_quality_color",
}

ADMIN_NULLABLE_STRING_FIELDS = {
    "display_name",
    "username",
    "root_type",
    "root_primary",
    "root_secondary",
    "root_relation",
    "root_quality",
    "root_quality_color",
}


def admin_patch_profile(tg: int, **fields) -> dict[str, Any] | None:
    safe = {k: v for k, v in fields.items() if k in ADMIN_EDITABLE_PROFILE_FIELDS}
    if not safe:
        raise ValueError("没有可更新的字段")
    if "realm_stage" in safe:
        safe["realm_stage"] = normalize_realm_stage(safe.get("realm_stage"))
    if "technique_capacity" in safe:
        safe["technique_capacity"] = max(_coerce_int(safe.get("technique_capacity"), 3), 1)
    for key in ADMIN_NULLABLE_STRING_FIELDS:
        if key in safe:
            safe[key] = None if safe[key] is None else (str(safe[key]).strip() or None)
    with Session() as session:
        profile = session.query(XiuxianProfile).filter(XiuxianProfile.tg == tg).first()
        if profile is None or not profile.consented:
            return None
        for key, value in safe.items():
            setattr(profile, key, value)
        profile.updated_at = utcnow()
        session.commit()
        session.refresh(profile)
        return serialize_profile(profile)


def get_sect(sect_id: int) -> XiuxianSect | None:
    with Session() as session:
        return session.query(XiuxianSect).filter(XiuxianSect.id == sect_id).first()


def list_sects(enabled_only: bool = False) -> list[dict[str, Any]]:
    with Session() as session:
        query = session.query(XiuxianSect)
        if enabled_only:
            query = query.filter(XiuxianSect.enabled.is_(True))
        return [serialize_sect(item) for item in query.order_by(XiuxianSect.id.desc()).all()]


def create_sect(**fields) -> dict[str, Any]:
    fields = _normalize_sect_fields(dict(fields))
    with Session() as session:
        sect = XiuxianSect(**fields)
        session.add(sect)
        session.commit()
        session.refresh(sect)
        return serialize_sect(sect)


def patch_sect(sect_id: int, **fields) -> dict[str, Any] | None:
    patch = dict(fields)
    with Session() as session:
        row = session.query(XiuxianSect).filter(XiuxianSect.id == sect_id).first()
        if row is None:
            return None
        current = serialize_sect(row) or {}
        current.update(patch)
        payload = _normalize_sect_fields(current)
        for key, value in payload.items():
            setattr(row, key, value)
        row.updated_at = utcnow()
        session.commit()
        session.refresh(row)
        return serialize_sect(row)


def delete_sect(sect_id: int) -> bool:
    with Session() as session:
        row = session.query(XiuxianSect).filter(XiuxianSect.id == sect_id).first()
        if row is None:
            return False
        session.delete(row)
        session.commit()
        return True


def replace_sect_roles(sect_id: int, roles: list[dict[str, Any]]) -> list[dict[str, Any]]:
    with Session() as session:
        session.query(XiuxianSectRole).filter(XiuxianSectRole.sect_id == sect_id).delete()
        payloads = []
        for role in roles:
            row = XiuxianSectRole(sect_id=sect_id, **role)
            session.add(row)
            payloads.append(row)
        session.commit()
        return [serialize_sect_role(row) for row in payloads]


def list_sect_roles(sect_id: int) -> list[dict[str, Any]]:
    with Session() as session:
        rows = (
            session.query(XiuxianSectRole)
            .filter(XiuxianSectRole.sect_id == sect_id)
            .order_by(XiuxianSectRole.sort_order.asc(), XiuxianSectRole.id.asc())
            .all()
        )
        return [serialize_sect_role(row) for row in rows]


def get_material(material_id: int) -> XiuxianMaterial | None:
    with Session() as session:
        return session.query(XiuxianMaterial).filter(XiuxianMaterial.id == material_id).first()


def list_materials(enabled_only: bool = False) -> list[dict[str, Any]]:
    with Session() as session:
        query = session.query(XiuxianMaterial)
        if enabled_only:
            query = query.filter(XiuxianMaterial.enabled.is_(True))
        return [serialize_material(row) for row in query.order_by(XiuxianMaterial.id.desc()).all()]


def create_material(**fields) -> dict[str, Any]:
    fields = dict(fields)
    fields["quality_level"] = normalize_quality_level(fields.get("quality_level"))
    with Session() as session:
        material = XiuxianMaterial(**fields)
        session.add(material)
        session.commit()
        session.refresh(material)
        return serialize_material(material)


def sync_material_by_name(**fields) -> dict[str, Any]:
    payload = {
        "name": str(fields.get("name") or "").strip(),
        "quality_level": normalize_quality_level(fields.get("quality_level")),
        "image_url": str(fields.get("image_url") or "").strip(),
        "description": str(fields.get("description") or "").strip(),
        "enabled": _coerce_bool(fields.get("enabled"), True),
    }
    if not payload["name"]:
        raise ValueError("material name is required")
    return _sync_named_entity(XiuxianMaterial, serialize_material, payload)


def patch_material(material_id: int, **fields) -> dict[str, Any] | None:
    patch = dict(fields)
    with Session() as session:
        row = session.query(XiuxianMaterial).filter(XiuxianMaterial.id == material_id).first()
        if row is None:
            return None
        current = serialize_material(row) or {}
        current.update(patch)
        payload = {
            "name": str(current.get("name") or "").strip(),
            "quality_level": normalize_quality_level(current.get("quality_level")),
            "image_url": str(current.get("image_url") or "").strip(),
            "description": str(current.get("description") or "").strip(),
            "enabled": _coerce_bool(current.get("enabled"), True),
        }
        for key, value in payload.items():
            setattr(row, key, value)
        row.updated_at = utcnow()
        session.commit()
        session.refresh(row)
        return serialize_material(row)


def delete_material(material_id: int) -> bool:
    with Session() as session:
        row = session.query(XiuxianMaterial).filter(XiuxianMaterial.id == material_id).first()
        if row is None:
            return False
        session.delete(row)
        session.commit()
        return True


def grant_material_to_user(tg: int, material_id: int, quantity: int = 1) -> dict[str, Any]:
    with Session() as session:
        row = (
            session.query(XiuxianMaterialInventory)
            .filter(
                XiuxianMaterialInventory.tg == tg,
                XiuxianMaterialInventory.material_id == material_id,
            )
            .first()
        )
        if row is None:
            row = XiuxianMaterialInventory(tg=tg, material_id=material_id, quantity=0)
            session.add(row)
        row.quantity += max(int(quantity), 1)
        row.updated_at = utcnow()
        session.commit()
        material = session.query(XiuxianMaterial).filter(XiuxianMaterial.id == material_id).first()
        return {
            "material": serialize_material(material),
            "quantity": row.quantity,
        }


def list_user_materials(tg: int) -> list[dict[str, Any]]:
    with Session() as session:
        rows = (
            session.query(XiuxianMaterialInventory, XiuxianMaterial)
            .join(XiuxianMaterial, XiuxianMaterial.id == XiuxianMaterialInventory.material_id)
            .filter(XiuxianMaterialInventory.tg == tg)
            .order_by(XiuxianMaterial.id.desc())
            .all()
        )
        return [
            {
                "quantity": inventory.quantity,
                "material": serialize_material(material),
            }
            for inventory, material in rows
        ]


def consume_user_materials(tg: int, material_id: int, quantity: int = 1) -> bool:
    with Session() as session:
        row = (
            session.query(XiuxianMaterialInventory)
            .filter(
                XiuxianMaterialInventory.tg == tg,
                XiuxianMaterialInventory.material_id == material_id,
            )
            .with_for_update()
            .first()
        )
        if row is None or row.quantity < quantity:
            return False
        row.quantity -= quantity
        row.updated_at = utcnow()
        if row.quantity <= 0:
            session.delete(row)
        session.commit()
        return True


def get_recipe(recipe_id: int) -> XiuxianRecipe | None:
    with Session() as session:
        return session.query(XiuxianRecipe).filter(XiuxianRecipe.id == recipe_id).first()


def list_recipes(enabled_only: bool = False) -> list[dict[str, Any]]:
    with Session() as session:
        query = session.query(XiuxianRecipe)
        if enabled_only:
            query = query.filter(XiuxianRecipe.enabled.is_(True))
        return [serialize_recipe(row) for row in query.order_by(XiuxianRecipe.id.desc()).all()]


def list_user_recipes(tg: int, enabled_only: bool = False) -> list[dict[str, Any]]:
    with Session() as session:
        rows = (
            session.query(XiuxianUserRecipe)
            .filter(XiuxianUserRecipe.tg == tg)
            .order_by(XiuxianUserRecipe.created_at.asc(), XiuxianUserRecipe.id.asc())
            .all()
        )
        recipe_ids = [item.recipe_id for item in rows] or [-1]
        recipe_map = {
            row.id: row
            for row in session.query(XiuxianRecipe).filter(XiuxianRecipe.id.in_(recipe_ids)).all()
        }
        payloads: list[dict[str, Any]] = []
        for row in rows:
            recipe = serialize_recipe(recipe_map.get(row.recipe_id))
            if enabled_only and not (recipe or {}).get("enabled"):
                continue
            payloads.append(serialize_user_recipe(row, recipe))
        return payloads


def user_has_recipe(tg: int, recipe_id: int) -> bool:
    with Session() as session:
        row = (
            session.query(XiuxianUserRecipe)
            .filter(XiuxianUserRecipe.tg == tg, XiuxianUserRecipe.recipe_id == recipe_id)
            .first()
        )
        return row is not None


def grant_recipe_to_user(
    tg: int,
    recipe_id: int,
    *,
    source: str | None = None,
    obtained_note: str | None = None,
) -> dict[str, Any]:
    with Session() as session:
        recipe = session.query(XiuxianRecipe).filter(XiuxianRecipe.id == recipe_id).first()
        if recipe is None:
            raise ValueError("recipe not found")
        row = (
            session.query(XiuxianUserRecipe)
            .filter(XiuxianUserRecipe.tg == tg, XiuxianUserRecipe.recipe_id == recipe_id)
            .first()
        )
        if row is None:
            row = XiuxianUserRecipe(
                tg=tg,
                recipe_id=recipe_id,
                source=(source or "").strip() or None,
                obtained_note=(obtained_note or "").strip() or None,
            )
            session.add(row)
        else:
            row.source = (source or row.source or "").strip() or None
            if obtained_note is not None:
                row.obtained_note = (obtained_note or "").strip() or None
            row.updated_at = utcnow()
        session.commit()
        session.refresh(row)
        return serialize_user_recipe(row, serialize_recipe(recipe))


def revoke_recipe_from_user(tg: int, recipe_id: int) -> bool:
    with Session() as session:
        row = (
            session.query(XiuxianUserRecipe)
            .filter(XiuxianUserRecipe.tg == tg, XiuxianUserRecipe.recipe_id == recipe_id)
            .first()
        )
        if row is None:
            return False
        session.delete(row)
        session.commit()
        return True


def create_recipe(**fields) -> dict[str, Any]:
    with Session() as session:
        recipe = XiuxianRecipe(**fields)
        session.add(recipe)
        session.commit()
        session.refresh(recipe)
        return serialize_recipe(recipe)


def delete_recipe(recipe_id: int) -> bool:
    with Session() as session:
        row = session.query(XiuxianRecipe).filter(XiuxianRecipe.id == recipe_id).first()
        if row is None:
            return False
        session.delete(row)
        session.commit()
        return True


def replace_recipe_ingredients(recipe_id: int, ingredients: list[dict[str, Any]]) -> list[dict[str, Any]]:
    with Session() as session:
        session.query(XiuxianRecipeIngredient).filter(XiuxianRecipeIngredient.recipe_id == recipe_id).delete()
        rows = []
        for payload in ingredients:
            row = XiuxianRecipeIngredient(recipe_id=recipe_id, **payload)
            session.add(row)
            rows.append(row)
        session.commit()
        return [
            {
                "id": row.id,
                "recipe_id": row.recipe_id,
                "material_id": row.material_id,
                "quantity": row.quantity,
            }
            for row in rows
        ]


def list_recipe_ingredients(recipe_id: int) -> list[dict[str, Any]]:
    with Session() as session:
        rows = (
            session.query(XiuxianRecipeIngredient, XiuxianMaterial)
            .join(XiuxianMaterial, XiuxianMaterial.id == XiuxianRecipeIngredient.material_id)
            .filter(XiuxianRecipeIngredient.recipe_id == recipe_id)
            .order_by(XiuxianRecipeIngredient.id.asc())
            .all()
        )
        return [
            {
                "id": ingredient.id,
                "recipe_id": ingredient.recipe_id,
                "material_id": ingredient.material_id,
                "quantity": ingredient.quantity,
                "material": serialize_material(material),
            }
            for ingredient, material in rows
        ]


def get_scene(scene_id: int) -> XiuxianScene | None:
    with Session() as session:
        return session.query(XiuxianScene).filter(XiuxianScene.id == scene_id).first()


def list_scenes(enabled_only: bool = False) -> list[dict[str, Any]]:
    with Session() as session:
        query = session.query(XiuxianScene)
        if enabled_only:
            query = query.filter(XiuxianScene.enabled.is_(True))
        return [serialize_scene(row) for row in query.order_by(XiuxianScene.id.desc()).all()]


def create_scene(**fields) -> dict[str, Any]:
    fields = dict(fields)
    fields["name"] = str(fields.get("name") or "").strip()
    fields["description"] = str(fields.get("description") or "").strip()
    fields["image_url"] = str(fields.get("image_url") or "").strip()
    fields["max_minutes"] = max(_coerce_int(fields.get("max_minutes"), 60), 1)
    min_realm_stage = fields.get("min_realm_stage")
    fields["min_realm_stage"] = normalize_realm_stage(min_realm_stage) if min_realm_stage else None
    fields["min_realm_layer"] = max(_coerce_int(fields.get("min_realm_layer"), 1), 1)
    fields["min_combat_power"] = max(_coerce_int(fields.get("min_combat_power"), 0), 0)
    fields["event_pool"] = _normalize_scene_event_pool(fields.get("event_pool"))
    fields["enabled"] = _coerce_bool(fields.get("enabled"), True)
    with Session() as session:
        scene = XiuxianScene(**fields)
        session.add(scene)
        session.commit()
        session.refresh(scene)
        return serialize_scene(scene)


def delete_scene(scene_id: int) -> bool:
    with Session() as session:
        row = session.query(XiuxianScene).filter(XiuxianScene.id == scene_id).first()
        if row is None:
            return False
        session.delete(row)
        session.commit()
        return True


def create_scene_drop(**fields) -> dict[str, Any]:
    with Session() as session:
        drop = XiuxianSceneDrop(**fields)
        session.add(drop)
        session.commit()
        session.refresh(drop)
        return serialize_scene_drop(drop)


def list_scene_drops(scene_id: int) -> list[dict[str, Any]]:
    with Session() as session:
        rows = (
            session.query(XiuxianSceneDrop)
            .filter(XiuxianSceneDrop.scene_id == scene_id)
            .order_by(XiuxianSceneDrop.id.asc())
            .all()
        )
        return [serialize_scene_drop(row) for row in rows]


def get_encounter_template(template_id: int) -> XiuxianEncounterTemplate | None:
    with Session() as session:
        return session.query(XiuxianEncounterTemplate).filter(XiuxianEncounterTemplate.id == template_id).first()


def list_encounter_templates(enabled_only: bool = False) -> list[dict[str, Any]]:
    with Session() as session:
        query = session.query(XiuxianEncounterTemplate)
        if enabled_only:
            query = query.filter(XiuxianEncounterTemplate.enabled.is_(True))
        return [serialize_encounter_template(row) for row in query.order_by(XiuxianEncounterTemplate.id.desc()).all()]


def _normalize_encounter_template_fields(fields: dict[str, Any]) -> dict[str, Any]:
    payload = dict(fields)
    payload["name"] = str(payload.get("name") or "").strip()
    payload["description"] = str(payload.get("description") or "").strip() or None
    payload["image_url"] = str(payload.get("image_url") or "").strip() or None
    payload["button_text"] = str(payload.get("button_text") or "").strip() or "抢夺机缘"
    payload["success_text"] = str(payload.get("success_text") or "").strip() or None
    payload["broadcast_text"] = str(payload.get("broadcast_text") or "").strip() or None
    payload["weight"] = max(_coerce_int(payload.get("weight"), 1), 1)
    payload["active_seconds"] = max(_coerce_int(payload.get("active_seconds"), 90), 15)
    min_realm_stage = payload.get("min_realm_stage")
    payload["min_realm_stage"] = normalize_realm_stage(min_realm_stage) if min_realm_stage else None
    payload["min_realm_layer"] = max(_coerce_int(payload.get("min_realm_layer"), 1), 1)
    payload["min_combat_power"] = max(_coerce_int(payload.get("min_combat_power"), 0), 0)
    payload["reward_stone_min"] = max(_coerce_int(payload.get("reward_stone_min"), 0), 0)
    payload["reward_stone_max"] = max(_coerce_int(payload.get("reward_stone_max"), payload["reward_stone_min"]), payload["reward_stone_min"])
    payload["reward_cultivation_min"] = max(_coerce_int(payload.get("reward_cultivation_min"), 0), 0)
    payload["reward_cultivation_max"] = max(_coerce_int(payload.get("reward_cultivation_max"), payload["reward_cultivation_min"]), payload["reward_cultivation_min"])
    reward_item_kind = str(payload.get("reward_item_kind") or "").strip() or None
    if reward_item_kind and reward_item_kind not in {"artifact", "pill", "talisman", "material", "recipe", "technique"}:
        raise ValueError("奇遇奖励物类型不支持")
    payload["reward_item_kind"] = reward_item_kind
    payload["reward_item_ref_id"] = _coerce_int(payload.get("reward_item_ref_id"), 0) or None
    payload["reward_item_quantity_min"] = max(_coerce_int(payload.get("reward_item_quantity_min"), 1), 1)
    payload["reward_item_quantity_max"] = max(_coerce_int(payload.get("reward_item_quantity_max"), payload["reward_item_quantity_min"]), payload["reward_item_quantity_min"])
    payload["reward_willpower"] = _coerce_int(payload.get("reward_willpower"), 0)
    payload["reward_charisma"] = _coerce_int(payload.get("reward_charisma"), 0)
    payload["reward_karma"] = _coerce_int(payload.get("reward_karma"), 0)
    payload["enabled"] = _coerce_bool(payload.get("enabled"), True)
    if not payload["name"]:
        raise ValueError("奇遇名称不能为空")
    if payload["reward_item_kind"] and not payload["reward_item_ref_id"]:
        raise ValueError("奇遇奖励物已选择类型，但没有指定具体物品")
    return payload


def create_encounter_template(**fields) -> dict[str, Any]:
    payload = _normalize_encounter_template_fields(fields)
    with Session() as session:
        row = XiuxianEncounterTemplate(**payload)
        session.add(row)
        session.commit()
        session.refresh(row)
        return serialize_encounter_template(row)


def sync_encounter_template_by_name(**fields) -> dict[str, Any]:
    payload = _normalize_encounter_template_fields(fields)
    with Session() as session:
        row = session.query(XiuxianEncounterTemplate).filter(XiuxianEncounterTemplate.name == payload["name"]).first()
        if row is None:
            row = XiuxianEncounterTemplate(**payload)
            session.add(row)
        else:
            for key, value in payload.items():
                setattr(row, key, value)
            row.updated_at = utcnow()
        session.commit()
        session.refresh(row)
        return serialize_encounter_template(row)


def patch_encounter_template(template_id: int, **fields) -> dict[str, Any] | None:
    with Session() as session:
        row = session.query(XiuxianEncounterTemplate).filter(XiuxianEncounterTemplate.id == template_id).first()
        if row is None:
            return None
        current = serialize_encounter_template(row) or {}
        current.update({key: value for key, value in fields.items() if value is not None})
        payload = _normalize_encounter_template_fields(current)
        for key, value in payload.items():
            setattr(row, key, value)
        row.updated_at = utcnow()
        session.commit()
        session.refresh(row)
        return serialize_encounter_template(row)


def delete_encounter_template(template_id: int) -> bool:
    with Session() as session:
        row = session.query(XiuxianEncounterTemplate).filter(XiuxianEncounterTemplate.id == template_id).first()
        if row is None:
            return False
        session.delete(row)
        session.commit()
        return True


def create_encounter_instance(
    *,
    template_id: int | None,
    template_name: str,
    group_chat_id: int,
    button_text: str,
    reward_payload: dict[str, Any],
    expires_at,
) -> dict[str, Any]:
    with Session() as session:
        row = XiuxianEncounterInstance(
            template_id=template_id,
            template_name=template_name,
            group_chat_id=group_chat_id,
            button_text=button_text,
            reward_payload=_sanitize_json_value(reward_payload),
            expires_at=expires_at,
            status="active",
        )
        session.add(row)
        session.commit()
        session.refresh(row)
        return serialize_encounter_instance(row)


def get_encounter_instance(instance_id: int) -> XiuxianEncounterInstance | None:
    with Session() as session:
        return session.query(XiuxianEncounterInstance).filter(XiuxianEncounterInstance.id == instance_id).first()


def patch_encounter_instance(instance_id: int, **fields) -> dict[str, Any] | None:
    with Session() as session:
        row = session.query(XiuxianEncounterInstance).filter(XiuxianEncounterInstance.id == instance_id).first()
        if row is None:
            return None
        for key, value in fields.items():
            if key == "reward_payload":
                value = _sanitize_json_value(value)
            setattr(row, key, value)
        row.updated_at = utcnow()
        session.commit()
        session.refresh(row)
        return serialize_encounter_instance(row)


def find_active_group_encounter(group_chat_id: int) -> dict[str, Any] | None:
    with Session() as session:
        row = (
            session.query(XiuxianEncounterInstance)
            .filter(
                XiuxianEncounterInstance.group_chat_id == group_chat_id,
                XiuxianEncounterInstance.status == "active",
                XiuxianEncounterInstance.expires_at > utcnow(),
            )
            .order_by(XiuxianEncounterInstance.id.desc())
            .first()
        )
        return serialize_encounter_instance(row)


def get_latest_group_encounter_time(group_chat_id: int):
    with Session() as session:
        row = (
            session.query(XiuxianEncounterInstance)
            .filter(XiuxianEncounterInstance.group_chat_id == group_chat_id)
            .order_by(XiuxianEncounterInstance.id.desc())
            .first()
        )
        return row.created_at if row is not None else None


def get_task(task_id: int) -> XiuxianTask | None:
    with Session() as session:
        return session.query(XiuxianTask).filter(XiuxianTask.id == task_id).first()


def list_tasks(enabled_only: bool = True) -> list[dict[str, Any]]:
    with Session() as session:
        query = session.query(XiuxianTask)
        if enabled_only:
            query = query.filter(XiuxianTask.enabled.is_(True))
        return [serialize_task(row) for row in query.order_by(XiuxianTask.id.desc()).all()]


def create_task(**fields) -> dict[str, Any]:
    fields = dict(fields)
    if fields.get("required_item_kind"):
        fields["required_item_kind"] = str(fields.get("required_item_kind")).strip() or None
    fields["required_item_ref_id"] = int(fields.get("required_item_ref_id") or 0) or None
    fields["required_item_quantity"] = max(int(fields.get("required_item_quantity") or 0), 0)
    if fields.get("reward_item_kind"):
        fields["reward_item_kind"] = str(fields.get("reward_item_kind")).strip() or None
    fields["reward_item_ref_id"] = int(fields.get("reward_item_ref_id") or 0) or None
    fields["reward_item_quantity"] = max(int(fields.get("reward_item_quantity") or 0), 0)
    with Session() as session:
        task = XiuxianTask(**fields)
        session.add(task)
        session.commit()
        session.refresh(task)
        return serialize_task(task)


def delete_task(task_id: int) -> bool:
    with Session() as session:
        row = session.query(XiuxianTask).filter(XiuxianTask.id == task_id).first()
        if row is None:
            return False
        session.delete(row)
        session.commit()
        return True


def list_task_claims(task_id: int) -> list[dict[str, Any]]:
    with Session() as session:
        rows = (
            session.query(XiuxianTaskClaim)
            .filter(XiuxianTaskClaim.task_id == task_id)
            .order_by(XiuxianTaskClaim.id.asc())
            .all()
        )
        return [
            {
                "id": row.id,
                "task_id": row.task_id,
                "tg": row.tg,
                "status": row.status,
                "submitted_answer": row.submitted_answer,
            }
            for row in rows
        ]


def create_journal(tg: int, action_type: str, title: str, detail: str | None = None) -> dict[str, Any]:
    with Session() as session:
        row = XiuxianJournal(
            tg=tg,
            action_type=(action_type or "system").strip()[:32],
            title=(title or "未知操作").strip()[:128],
            detail=(detail or "").strip() or None,
        )
        session.add(row)
        session.commit()
        session.refresh(row)
        return serialize_journal(row)


def list_recent_journals(tg: int, hours: int = 24) -> list[dict[str, Any]]:
    since = utcnow() - timedelta(hours=max(int(hours or 24), 1))
    with Session() as session:
        rows = (
            session.query(XiuxianJournal)
            .filter(XiuxianJournal.tg == tg, XiuxianJournal.created_at >= since)
            .order_by(XiuxianJournal.created_at.desc(), XiuxianJournal.id.desc())
            .all()
        )
        return [serialize_journal(row) for row in rows]


def create_title(**fields) -> dict[str, Any]:
    payload = _normalize_title_fields(dict(fields))
    with Session() as session:
        row = XiuxianTitle(**payload)
        session.add(row)
        session.commit()
        session.refresh(row)
        return serialize_title(row)


def sync_title_by_name(**fields) -> dict[str, Any]:
    return _sync_named_entity(XiuxianTitle, serialize_title, _normalize_title_fields(dict(fields)))


def get_title(title_id: int) -> XiuxianTitle | None:
    with Session() as session:
        return session.query(XiuxianTitle).filter(XiuxianTitle.id == title_id).first()


def list_titles(enabled_only: bool = False) -> list[dict[str, Any]]:
    with Session() as session:
        query = session.query(XiuxianTitle)
        if enabled_only:
            query = query.filter(XiuxianTitle.enabled.is_(True))
        rows = query.order_by(XiuxianTitle.id.desc()).all()
        return [serialize_title(row) for row in rows]


def patch_title(title_id: int, **fields) -> dict[str, Any] | None:
    patch = dict(fields)
    with Session() as session:
        row = session.query(XiuxianTitle).filter(XiuxianTitle.id == title_id).first()
        if row is None:
            return None
        current = serialize_title(row) or {}
        current.update(patch)
        payload = _normalize_title_fields(current)
        for key, value in payload.items():
            setattr(row, key, value)
        row.updated_at = utcnow()
        session.commit()
        session.refresh(row)
        return serialize_title(row)


def delete_title(title_id: int) -> bool:
    with Session() as session:
        row = session.query(XiuxianTitle).filter(XiuxianTitle.id == title_id).first()
        if row is None:
            return False
        session.query(XiuxianProfile).filter(XiuxianProfile.current_title_id == title_id).update(
            {"current_title_id": None, "updated_at": utcnow()},
            synchronize_session=False,
        )
        session.delete(row)
        session.commit()
        return True


def list_user_titles(tg: int, enabled_only: bool = False) -> list[dict[str, Any]]:
    with Session() as session:
        rows = (
            session.query(XiuxianUserTitle)
            .filter(XiuxianUserTitle.tg == tg)
            .order_by(XiuxianUserTitle.created_at.asc(), XiuxianUserTitle.id.asc())
            .all()
        )
        titles = {
            row.id: row
            for row in session.query(XiuxianTitle)
            .filter(XiuxianTitle.id.in_([item.title_id for item in rows] or [-1]))
            .all()
        }
        serialized: list[dict[str, Any]] = []
        for row in rows:
            title = serialize_title(titles.get(row.title_id))
            if enabled_only and not (title or {}).get("enabled"):
                continue
            serialized.append(serialize_user_title(row, title))
        return serialized


def get_current_title(tg: int, enabled_only: bool = False) -> dict[str, Any] | None:
    with Session() as session:
        profile = session.query(XiuxianProfile).filter(XiuxianProfile.tg == tg).first()
        if profile is None or not profile.current_title_id:
            return None
        row = session.query(XiuxianTitle).filter(XiuxianTitle.id == profile.current_title_id).first()
        if row is None or (enabled_only and not row.enabled):
            return None
        return serialize_title(row)


def grant_title_to_user(
    tg: int,
    title_id: int,
    *,
    source: str | None = None,
    obtained_note: str | None = None,
    equip: bool = False,
    auto_equip_if_empty: bool = False,
) -> dict[str, Any]:
    with Session() as session:
        title = session.query(XiuxianTitle).filter(XiuxianTitle.id == title_id).first()
        if title is None:
            raise ValueError("title not found")
        row = (
            session.query(XiuxianUserTitle)
            .filter(XiuxianUserTitle.tg == tg, XiuxianUserTitle.title_id == title_id)
            .first()
        )
        if row is None:
            row = XiuxianUserTitle(
                tg=tg,
                title_id=title_id,
                source=(source or "").strip() or None,
                obtained_note=(obtained_note or "").strip() or None,
            )
            session.add(row)
        else:
            if source is not None:
                row.source = (source or "").strip() or None
            if obtained_note is not None:
                row.obtained_note = (obtained_note or "").strip() or None
            row.updated_at = utcnow()
        profile = session.query(XiuxianProfile).filter(XiuxianProfile.tg == tg).first()
        if profile is None:
            profile = XiuxianProfile(tg=tg)
            session.add(profile)
        if equip or (auto_equip_if_empty and not profile.current_title_id):
            profile.current_title_id = title_id
            profile.updated_at = utcnow()
        session.commit()
        session.refresh(row)
        return serialize_user_title(row, serialize_title(title))


def revoke_title_from_user(tg: int, title_id: int) -> bool:
    with Session() as session:
        row = (
            session.query(XiuxianUserTitle)
            .filter(XiuxianUserTitle.tg == tg, XiuxianUserTitle.title_id == title_id)
            .first()
        )
        if row is None:
            return False
        profile = session.query(XiuxianProfile).filter(XiuxianProfile.tg == tg).first()
        if profile is not None and int(profile.current_title_id or 0) == int(title_id):
            profile.current_title_id = None
            profile.updated_at = utcnow()
        session.delete(row)
        session.commit()
        return True


def set_current_title(tg: int, title_id: int | None) -> dict[str, Any] | None:
    with Session() as session:
        profile = session.query(XiuxianProfile).filter(XiuxianProfile.tg == tg).first()
        if profile is None:
            profile = XiuxianProfile(tg=tg)
            session.add(profile)
        if title_id in {None, 0}:
            profile.current_title_id = None
            profile.updated_at = utcnow()
            session.commit()
            return None
        owned = (
            session.query(XiuxianUserTitle)
            .filter(XiuxianUserTitle.tg == tg, XiuxianUserTitle.title_id == int(title_id))
            .first()
        )
        if owned is None:
            raise ValueError("user does not own this title")
        title = session.query(XiuxianTitle).filter(XiuxianTitle.id == int(title_id)).first()
        if title is None:
            raise ValueError("title not found")
        profile.current_title_id = int(title_id)
        profile.updated_at = utcnow()
        session.commit()
        return serialize_title(title)


def create_achievement(**fields) -> dict[str, Any]:
    payload = _normalize_achievement_fields(dict(fields))
    with Session() as session:
        row = XiuxianAchievement(**payload)
        session.add(row)
        session.commit()
        session.refresh(row)
        return serialize_achievement(row)


def sync_achievement_by_key(**fields) -> dict[str, Any]:
    payload = _normalize_achievement_fields(dict(fields))
    with Session() as session:
        row = (
            session.query(XiuxianAchievement)
            .filter(XiuxianAchievement.achievement_key == payload["achievement_key"])
            .first()
        )
        if row is None:
            row = XiuxianAchievement(**payload)
            session.add(row)
            session.commit()
            session.refresh(row)
            return serialize_achievement(row)
        changed = False
        for key, value in payload.items():
            if getattr(row, key) != value:
                setattr(row, key, value)
                changed = True
        if changed:
            row.updated_at = utcnow()
            session.commit()
            session.refresh(row)
        return serialize_achievement(row)


def get_achievement(achievement_id: int) -> XiuxianAchievement | None:
    with Session() as session:
        return session.query(XiuxianAchievement).filter(XiuxianAchievement.id == achievement_id).first()


def list_achievements(enabled_only: bool = False) -> list[dict[str, Any]]:
    with Session() as session:
        query = session.query(XiuxianAchievement)
        if enabled_only:
            query = query.filter(XiuxianAchievement.enabled.is_(True))
        rows = (
            query.order_by(
                XiuxianAchievement.sort_order.asc(),
                XiuxianAchievement.target_value.asc(),
                XiuxianAchievement.id.asc(),
            )
            .all()
        )
        return [serialize_achievement(row) for row in rows]


def list_achievements_by_metric(metric_keys: list[str], enabled_only: bool = True) -> list[dict[str, Any]]:
    metric_keys = [str(item).strip() for item in metric_keys if str(item).strip()]
    if not metric_keys:
        return []
    with Session() as session:
        query = session.query(XiuxianAchievement).filter(XiuxianAchievement.metric_key.in_(metric_keys))
        if enabled_only:
            query = query.filter(XiuxianAchievement.enabled.is_(True))
        rows = (
            query.order_by(
                XiuxianAchievement.sort_order.asc(),
                XiuxianAchievement.target_value.asc(),
                XiuxianAchievement.id.asc(),
            )
            .all()
        )
        return [serialize_achievement(row) for row in rows]


def patch_achievement(achievement_id: int, **fields) -> dict[str, Any] | None:
    patch = dict(fields)
    with Session() as session:
        row = session.query(XiuxianAchievement).filter(XiuxianAchievement.id == achievement_id).first()
        if row is None:
            return None
        current = serialize_achievement(row) or {}
        current.update(patch)
        payload = _normalize_achievement_fields(current)
        for key, value in payload.items():
            setattr(row, key, value)
        row.updated_at = utcnow()
        session.commit()
        session.refresh(row)
        return serialize_achievement(row)


def delete_achievement(achievement_id: int) -> bool:
    with Session() as session:
        row = session.query(XiuxianAchievement).filter(XiuxianAchievement.id == achievement_id).first()
        if row is None:
            return False
        session.delete(row)
        session.commit()
        return True


def list_user_achievement_progress(tg: int) -> list[dict[str, Any]]:
    with Session() as session:
        rows = (
            session.query(XiuxianAchievementProgress)
            .filter(XiuxianAchievementProgress.tg == tg)
            .order_by(XiuxianAchievementProgress.metric_key.asc())
            .all()
        )
        return [serialize_achievement_progress(row) for row in rows]


def get_user_achievement_progress_map(tg: int) -> dict[str, int]:
    with Session() as session:
        rows = session.query(XiuxianAchievementProgress).filter(XiuxianAchievementProgress.tg == tg).all()
        return {row.metric_key: int(row.current_value or 0) for row in rows}


def apply_achievement_progress_deltas(tg: int, deltas: dict[str, int | float]) -> dict[str, int]:
    sanitized: dict[str, int] = {}
    for key, value in (deltas or {}).items():
        metric_key = str(key or "").strip()
        if not metric_key:
            continue
        amount = int(value or 0)
        if amount == 0:
            continue
        sanitized[metric_key] = sanitized.get(metric_key, 0) + amount
    if not sanitized:
        return {}
    with Session() as session:
        result: dict[str, int] = {}
        for metric_key, amount in sanitized.items():
            row = (
                session.query(XiuxianAchievementProgress)
                .filter(
                    XiuxianAchievementProgress.tg == tg,
                    XiuxianAchievementProgress.metric_key == metric_key,
                )
                .first()
            )
            if row is None:
                row = XiuxianAchievementProgress(tg=tg, metric_key=metric_key, current_value=0)
                session.add(row)
            row.current_value = max(int(row.current_value or 0) + amount, 0)
            row.updated_at = utcnow()
            result[metric_key] = int(row.current_value or 0)
        session.commit()
        return result


def list_user_achievements(tg: int) -> list[dict[str, Any]]:
    with Session() as session:
        rows = (
            session.query(XiuxianUserAchievement)
            .filter(XiuxianUserAchievement.tg == tg)
            .order_by(XiuxianUserAchievement.unlocked_at.asc(), XiuxianUserAchievement.id.asc())
            .all()
        )
        achievements = {
            row.id: row
            for row in session.query(XiuxianAchievement)
            .filter(XiuxianAchievement.id.in_([item.achievement_id for item in rows] or [-1]))
            .all()
        }
        return [
            serialize_user_achievement(row, serialize_achievement(achievements.get(row.achievement_id)))
            for row in rows
        ]


def unlock_user_achievement(
    tg: int,
    achievement_id: int,
    *,
    reward_snapshot: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    with Session() as session:
        existing = (
            session.query(XiuxianUserAchievement)
            .filter(
                XiuxianUserAchievement.tg == tg,
                XiuxianUserAchievement.achievement_id == achievement_id,
            )
            .first()
        )
        if existing is not None:
            achievement = session.query(XiuxianAchievement).filter(XiuxianAchievement.id == achievement_id).first()
            payload = serialize_user_achievement(existing, serialize_achievement(achievement))
            if payload is not None:
                payload["created"] = False
            return payload
        achievement = session.query(XiuxianAchievement).filter(XiuxianAchievement.id == achievement_id).first()
        if achievement is None:
            return None
        row = XiuxianUserAchievement(
            tg=tg,
            achievement_id=achievement_id,
            reward_snapshot=reward_snapshot or {},
        )
        session.add(row)
        session.commit()
        session.refresh(row)
        payload = serialize_user_achievement(row, serialize_achievement(achievement))
        if payload is not None:
            payload["created"] = True
        return payload


def get_user_achievement(tg: int, achievement_id: int) -> dict[str, Any] | None:
    with Session() as session:
        row = (
            session.query(XiuxianUserAchievement)
            .filter(
                XiuxianUserAchievement.tg == tg,
                XiuxianUserAchievement.achievement_id == achievement_id,
            )
            .first()
        )
        if row is None:
            return None
        achievement = session.query(XiuxianAchievement).filter(XiuxianAchievement.id == achievement_id).first()
        return serialize_user_achievement(row, serialize_achievement(achievement))


def mark_user_achievement_notification(tg: int, achievement_id: int, channel: str) -> dict[str, Any] | None:
    channel = str(channel or "").strip().lower()
    if channel not in {"private", "group"}:
        raise ValueError("unsupported achievement notify channel")
    with Session() as session:
        row = (
            session.query(XiuxianUserAchievement)
            .filter(
                XiuxianUserAchievement.tg == tg,
                XiuxianUserAchievement.achievement_id == achievement_id,
            )
            .first()
        )
        if row is None:
            return None
        if channel == "private":
            row.private_notified_at = utcnow()
        else:
            row.group_notified_at = utcnow()
        row.updated_at = utcnow()
        session.commit()
        achievement = session.query(XiuxianAchievement).filter(XiuxianAchievement.id == achievement_id).first()
        return serialize_user_achievement(row, serialize_achievement(achievement))


def create_red_envelope(**fields) -> dict[str, Any]:
    with Session() as session:
        envelope = XiuxianRedEnvelope(**fields)
        session.add(envelope)
        session.commit()
        session.refresh(envelope)
        return serialize_red_envelope(envelope)


def get_red_envelope(envelope_id: int) -> XiuxianRedEnvelope | None:
    with Session() as session:
        return session.query(XiuxianRedEnvelope).filter(XiuxianRedEnvelope.id == envelope_id).first()


def list_red_envelope_claims(envelope_id: int) -> list[dict[str, Any]]:
    with Session() as session:
        rows = (
            session.query(XiuxianRedEnvelopeClaim)
            .filter(XiuxianRedEnvelopeClaim.envelope_id == envelope_id)
            .order_by(XiuxianRedEnvelopeClaim.id.asc())
            .all()
        )
        payload = [
            {
                "id": row.id,
                "envelope_id": row.envelope_id,
                "tg": row.tg,
                "amount": row.amount,
                "created_at": serialize_datetime(row.created_at),
            }
            for row in rows
        ]
    name_map = get_emby_name_map([int(item["tg"]) for item in payload])
    for item in payload:
        item["name"] = name_map.get(int(item["tg"]), f"TG {item['tg']}")
    return payload


def cancel_personal_shop_item(owner_tg: int, item_id: int) -> dict[str, Any]:
    with Session() as session:
        item = (
            session.query(XiuxianShopItem)
            .filter(
                XiuxianShopItem.id == item_id,
                XiuxianShopItem.owner_tg == owner_tg,
                XiuxianShopItem.is_official.is_(False),
            )
            .with_for_update()
            .first()
        )
        if item is None:
            raise ValueError("未找到可取消的个人上架商品")

        restore_quantity = max(int(item.quantity or 0), 0)
        if restore_quantity > 0:
            if item.item_kind == "artifact":
                row = (
                    session.query(XiuxianArtifactInventory)
                    .filter(
                        XiuxianArtifactInventory.tg == owner_tg,
                        XiuxianArtifactInventory.artifact_id == item.item_ref_id,
                    )
                    .first()
                )
                if row is None:
                    row = XiuxianArtifactInventory(tg=owner_tg, artifact_id=item.item_ref_id, quantity=0)
                    session.add(row)
                row.quantity += restore_quantity
                row.updated_at = utcnow()
            elif item.item_kind == "pill":
                row = (
                    session.query(XiuxianPillInventory)
                    .filter(
                        XiuxianPillInventory.tg == owner_tg,
                        XiuxianPillInventory.pill_id == item.item_ref_id,
                    )
                    .first()
                )
                if row is None:
                    row = XiuxianPillInventory(tg=owner_tg, pill_id=item.item_ref_id, quantity=0)
                    session.add(row)
                row.quantity += restore_quantity
                row.updated_at = utcnow()
            elif item.item_kind == "talisman":
                row = (
                    session.query(XiuxianTalismanInventory)
                    .filter(
                        XiuxianTalismanInventory.tg == owner_tg,
                        XiuxianTalismanInventory.talisman_id == item.item_ref_id,
                    )
                    .first()
                )
                if row is None:
                    row = XiuxianTalismanInventory(tg=owner_tg, talisman_id=item.item_ref_id, quantity=0)
                    session.add(row)
                row.quantity += restore_quantity
                row.updated_at = utcnow()
            else:
                raise ValueError("暂不支持该类型商品取消上架")

        item.quantity = 0
        item.enabled = False
        item.updated_at = utcnow()
        session.commit()
        session.refresh(item)
        return {
            "item": serialize_shop_item(item),
            "restored_quantity": restore_quantity,
        }


def create_duel_bet_pool(**fields) -> dict[str, Any]:
    with Session() as session:
        pool = XiuxianDuelBetPool(**fields)
        session.add(pool)
        session.commit()
        session.refresh(pool)
        return {
            "id": pool.id,
            "challenger_tg": pool.challenger_tg,
            "defender_tg": pool.defender_tg,
            "stake": pool.stake,
            "group_chat_id": pool.group_chat_id,
            "duel_message_id": pool.duel_message_id,
            "bet_message_id": pool.bet_message_id,
            "bets_close_at": serialize_datetime(pool.bets_close_at),
            "resolved": pool.resolved,
            "winner_tg": pool.winner_tg,
        }


def get_duel_bet_pool(pool_id: int) -> XiuxianDuelBetPool | None:
    with Session() as session:
        return session.query(XiuxianDuelBetPool).filter(XiuxianDuelBetPool.id == pool_id).first()

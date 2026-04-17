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


REALM_ORDER = [
    "炼气",
    "筑基",
    "金丹",
    "元婴",
    "化神",
    "炼虚",
    "合体",
    "大乘",
    "渡劫",
    "人仙",
    "地仙",
    "天仙",
    "金仙",
    "大罗金仙",
    "仙君",
    "仙王",
    "仙尊",
    "仙帝",
]
LEGACY_REALM_ORDER = ["凡人", "炼气", "筑基", "结丹", "元婴", "化神", "须弥", "芥子", "混元一体", "炼虚", "合体", "渡劫", "真仙"]
REALM_LAYER_LIMIT = 9
LEGACY_REALM_ALIASES = {
    "练气": "炼气",
    "浑元一体": "混元一体",
}
LEGACY_TO_NEW_REALM_STAGE = {
    "凡人": "炼气",
    "炼气": "炼气",
    "筑基": "筑基",
    "结丹": "金丹",
    "元婴": "元婴",
    "化神": "化神",
    "须弥": "炼虚",
    "芥子": "合体",
    "混元一体": "大乘",
    "炼虚": "炼虚",
    "合体": "合体",
    "渡劫": "渡劫",
    "真仙": "人仙",
}
REALM_STAGE_RULE_ROWS = [
    ("炼气", 180, 36, 8, 16, 2, 4, 24, 90),
    ("筑基", 420, 72, 10, 20, 2, 5, 34, 84),
    ("金丹", 900, 140, 14, 26, 3, 6, 48, 78),
    ("元婴", 1800, 260, 18, 34, 4, 8, 68, 72),
    ("化神", 3400, 420, 24, 44, 5, 10, 96, 66),
    ("炼虚", 6200, 680, 30, 56, 6, 12, 136, 60),
    ("合体", 10800, 1080, 38, 70, 8, 14, 190, 54),
    ("大乘", 18000, 1680, 48, 86, 10, 16, 260, 48),
    ("渡劫", 29400, 2580, 60, 104, 12, 18, 350, 42),
    ("人仙", 46800, 3900, 76, 126, 14, 22, 470, 36),
    ("地仙", 73200, 5820, 94, 152, 16, 26, 620, 32),
    ("天仙", 112000, 8520, 116, 182, 18, 30, 810, 28),
    ("金仙", 168000, 12300, 140, 216, 20, 34, 1040, 24),
    ("大罗金仙", 248000, 17400, 168, 256, 22, 38, 1320, 20),
    ("仙君", 360000, 24600, 198, 302, 24, 42, 1660, 16),
    ("仙王", 516000, 34200, 230, 354, 26, 48, 2060, 12),
    ("仙尊", 730000, 47000, 264, 414, 28, 54, 2520, 8),
    ("仙帝", 1024000, 64000, 300, 480, 32, 60, 3060, 0),
]
REALM_STAGE_RULES = {
    stage: {
        "threshold_base": threshold_base,
        "threshold_step": threshold_step,
        "practice_gain_min": practice_gain_min,
        "practice_gain_max": practice_gain_max,
        "practice_stone_min": practice_stone_min,
        "practice_stone_max": practice_stone_max,
        "retreat_hourly_base": retreat_hourly_base,
        "breakthrough_base_rate": breakthrough_base_rate,
    }
    for (
        stage,
        threshold_base,
        threshold_step,
        practice_gain_min,
        practice_gain_max,
        practice_stone_min,
        practice_stone_max,
        retreat_hourly_base,
        breakthrough_base_rate,
    ) in REALM_STAGE_RULE_ROWS
}
IMMORTAL_REBASE_START_STAGE = "人仙"
IMMORTAL_REBASE_START_INDEX = REALM_ORDER.index(IMMORTAL_REBASE_START_STAGE)
IMMORTAL_REBASE_SOURCE_STAGES = REALM_ORDER[IMMORTAL_REBASE_START_INDEX:]
IMMORTAL_REBASE_TARGET_STAGES = REALM_ORDER[: len(IMMORTAL_REBASE_SOURCE_STAGES)]
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
STARTER_ARTIFACT_NAME = "凡铁剑"
STARTER_ARTIFACT_GRANTED_ACTION = "starter_artifact_grant"
STARTER_ARTIFACT_RELEASED_ACTION = "starter_artifact_release"
DUEL_MODE_LABELS = {
    "standard": "普通斗法",
    "master": "炉鼎对决",
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
DEFAULT_ACTIVITY_STAT_GROWTH_RULES = {
    "practice": {"chance_percent": 18, "gain_min": 1, "gain_max": 2, "attribute_count": 1},
    "commission": {"chance_percent": 22, "gain_min": 1, "gain_max": 2, "attribute_count": 1},
    "exploration": {"chance_percent": 26, "gain_min": 1, "gain_max": 3, "attribute_count": 1},
    "duel": {"chance_percent": 20, "gain_min": 1, "gain_max": 2, "attribute_count": 2},
}
DEFAULT_GAMBLING_QUALITY_WEIGHT_RULES = {
    "凡品": {"weight_multiplier": 1.0},
    "下品": {"weight_multiplier": 0.72},
    "中品": {"weight_multiplier": 0.44},
    "上品": {"weight_multiplier": 0.22},
    "极品": {"weight_multiplier": 0.1},
    "仙品": {"weight_multiplier": 0.04},
    "先天至宝": {"weight_multiplier": 0.015},
}
DEFAULT_GAMBLING_REWARD_POOL = [
    {"item_kind": "material", "item_name": "灵露滴", "quantity_min": 2, "quantity_max": 5, "base_weight": 120, "enabled": True},
    {"item_kind": "artifact", "item_name": "凡铁剑", "quantity_min": 1, "quantity_max": 1, "base_weight": 90, "enabled": True},
    {"item_kind": "material", "item_name": "霜凌草", "quantity_min": 1, "quantity_max": 3, "base_weight": 84, "enabled": True},
    {"item_kind": "pill", "item_name": "聚气丹", "quantity_min": 1, "quantity_max": 2, "base_weight": 72, "enabled": True},
    {"item_kind": "talisman", "item_name": "御风符", "quantity_min": 1, "quantity_max": 1, "base_weight": 60, "enabled": True},
    {"item_kind": "material", "item_name": "冰魄珠", "quantity_min": 1, "quantity_max": 2, "base_weight": 54, "enabled": True},
    {"item_kind": "artifact", "item_name": "青罡剑", "quantity_min": 1, "quantity_max": 1, "base_weight": 38, "enabled": True},
    {"item_kind": "pill", "item_name": "回春丹", "quantity_min": 1, "quantity_max": 2, "base_weight": 36, "enabled": True},
    {"item_kind": "material", "item_name": "玄冰精髓", "quantity_min": 1, "quantity_max": 1, "base_weight": 18, "enabled": True},
    {"item_kind": "talisman", "item_name": "镇岳符", "quantity_min": 1, "quantity_max": 1, "base_weight": 14, "enabled": True},
    {"item_kind": "material", "item_name": "九幽寒莲", "quantity_min": 1, "quantity_max": 1, "base_weight": 8, "enabled": True},
    {"item_kind": "talisman", "item_name": "摄魂符", "quantity_min": 1, "quantity_max": 1, "base_weight": 6, "enabled": True},
    {"item_kind": "material", "item_name": "鸿蒙紫莲", "quantity_min": 1, "quantity_max": 1, "base_weight": 3, "enabled": True},
    {"item_kind": "talisman", "item_name": "裂空符", "quantity_min": 1, "quantity_max": 1, "base_weight": 2, "enabled": True},
    {"item_kind": "material", "item_name": "开天神石", "quantity_min": 1, "quantity_max": 1, "base_weight": 1, "enabled": True},
]
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
    "auction_fee_percent": 5,
    "auction_duration_minutes": 60,
    "allow_user_task_publish": True,
    "task_publish_cost": 20,
    "user_task_daily_limit": 3,
    "artifact_equip_limit": 3,
    "duel_bet_enabled": True,
    "duel_bet_seconds": 120,
    "duel_bet_min_amount": 10,
    "duel_bet_max_amount": 100,
    "duel_bet_amount_options": [10, 50, 100],
    "duel_winner_steal_percent": 25,
    "duel_invite_timeout_seconds": 90,
    "allow_non_admin_image_upload": False,
    "chat_cultivation_chance": 8,
    "chat_cultivation_min_gain": 1,
    "chat_cultivation_max_gain": 3,
    "robbery_daily_limit": 3,
    "robbery_max_steal": 180,
    "high_quality_broadcast_level": 4,
    "gambling_exchange_cost_stone": 120,
    "gambling_exchange_max_count": 20,
    "gambling_open_max_count": 20,
    "gambling_broadcast_quality_level": 5,
    "gambling_fortune_divisor": 6,
    "gambling_fortune_bonus_per_quality_percent": 8,
    "gambling_quality_weight_rules": DEFAULT_GAMBLING_QUALITY_WEIGHT_RULES,
    "gambling_reward_pool": DEFAULT_GAMBLING_REWARD_POOL,
    "root_quality_value_rules": DEFAULT_ROOT_QUALITY_VALUE_RULES,
    "exploration_drop_weight_rules": DEFAULT_EXPLORATION_DROP_WEIGHT_RULES,
    "item_quality_value_rules": DEFAULT_ITEM_QUALITY_VALUE_RULES,
    "activity_stat_growth_rules": DEFAULT_ACTIVITY_STAT_GROWTH_RULES,
    "immortal_touch_infusion_layers": 1,
    "encounter_spawn_chance": 5,
    "encounter_group_cooldown_minutes": 12,
    "encounter_active_seconds": 90,
    "slave_tribute_percent": 20,
    "slave_challenge_cooldown_hours": 24,
    "rebirth_cooldown_enabled": False,
    "rebirth_cooldown_base_hours": 12,
    "rebirth_cooldown_increment_hours": 6,
    "furnace_harvest_cultivation_percent": 10,
    "sect_salary_min_stay_days": 30,
    "sect_betrayal_cooldown_days": 7,
    "sect_betrayal_stone_percent": 10,
    "sect_betrayal_stone_min": 20,
    "sect_betrayal_stone_max": 300,
    "error_log_retention_count": 500,
    "seclusion_cultivation_efficiency_percent": 60,
}
DEFAULT_SETTINGS["duel_bet_minutes"] = 2
STALE_DUEL_LOCK_GRACE_SECONDS = 120

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

SOCIAL_MODE_LABELS = {
    "worldly": "入世",
    "secluded": "避世",
}
GENDER_LABELS = {
    "male": "男",
    "female": "女",
}
MENTORSHIP_REQUEST_ROLE_LABELS = {
    "mentor": "收徒邀请",
    "disciple": "拜师申请",
}
MENTORSHIP_STATUS_LABELS = {
    "active": "师徒在籍",
    "graduated": "已出师",
    "dissolved": "已解除",
}
MENTORSHIP_REQUEST_STATUS_LABELS = {
    "pending": "待处理",
    "accepted": "已接受",
    "rejected": "已婉拒",
    "cancelled": "已撤回",
    "expired": "已过期",
}
MARRIAGE_STATUS_LABELS = {
    "active": "已结为道侣",
    "divorced": "已和离",
}
MARRIAGE_REQUEST_STATUS_LABELS = {
    "pending": "待处理",
    "accepted": "已接受",
    "rejected": "已婉拒",
    "cancelled": "已撤回",
    "expired": "已过期",
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
    "charisma": "影响官坊成交折扣、坊市播报成本与部分身份门槛",
    "karma": "影响突破把握、委托收益、秘境趋吉避凶与斗法综合评价",
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
        return REALM_ORDER[0]
    normalized = LEGACY_REALM_ALIASES.get(raw, raw)
    if normalized in REALM_ORDER:
        return normalized
    return LEGACY_TO_NEW_REALM_STAGE.get(normalized, REALM_ORDER[0])


def _normalize_legacy_realm_stage(stage: str | None) -> str:
    raw = str(stage or "").strip()
    if not raw:
        return LEGACY_REALM_ORDER[0]
    normalized = LEGACY_REALM_ALIASES.get(raw, raw)
    return normalized if normalized in LEGACY_REALM_ORDER else LEGACY_REALM_ORDER[0]


def normalize_realm_layer(layer: int | str | None, default: int = 1) -> int:
    try:
        value = int(layer or default)
    except (TypeError, ValueError):
        value = default
    return max(1, min(value, REALM_LAYER_LIMIT))


def get_realm_stage_rule(stage: str | None) -> dict[str, int]:
    normalized = normalize_realm_stage(stage)
    return REALM_STAGE_RULES.get(normalized, REALM_STAGE_RULES[REALM_ORDER[0]])


def calculate_realm_threshold(stage: str | None, layer: int | str | None) -> int:
    rule = get_realm_stage_rule(stage)
    current_layer = normalize_realm_layer(layer)
    return int(rule["threshold_base"]) + (current_layer - 1) * int(rule["threshold_step"])


def calculate_legacy_realm_threshold(stage: str | None, layer: int | str | None) -> int:
    current_stage = _normalize_legacy_realm_stage(stage)
    current_layer = normalize_realm_layer(layer)
    return 80 + LEGACY_REALM_ORDER.index(current_stage) * 30 + current_layer * 18


def is_legacy_realm_stage(stage: str | None) -> bool:
    normalized = _normalize_legacy_realm_stage(stage)
    return normalized in LEGACY_REALM_ORDER and normalized not in REALM_ORDER


def migrate_legacy_realm_state(stage: str | None, layer: int | str | None, cultivation: int | str | None) -> dict[str, Any]:
    raw_stage = str(stage or "").strip()
    target_stage = normalize_realm_stage(raw_stage)
    normalized_layer = normalize_realm_layer(layer)
    try:
        current_cultivation = max(int(cultivation or 0), 0)
    except (TypeError, ValueError):
        current_cultivation = 0
    try:
        original_layer = int(layer or normalized_layer)
    except (TypeError, ValueError):
        original_layer = normalized_layer

    if raw_stage in REALM_ORDER:
        threshold = calculate_realm_threshold(target_stage, normalized_layer)
        capped_cultivation = min(current_cultivation, threshold)
        return {
            "source_stage": raw_stage or target_stage,
            "target_stage": target_stage,
            "target_layer": normalized_layer,
            "target_cultivation": capped_cultivation,
            "changed": (
                target_stage != raw_stage
                or normalized_layer != original_layer
                or capped_cultivation != current_cultivation
            ),
            "legacy": False,
        }

    legacy_stage = _normalize_legacy_realm_stage(raw_stage)
    if legacy_stage not in LEGACY_REALM_ORDER:
        threshold = calculate_realm_threshold(target_stage, normalized_layer)
        capped_cultivation = min(current_cultivation, threshold)
        return {
            "source_stage": raw_stage or target_stage,
            "target_stage": target_stage,
            "target_layer": normalized_layer,
            "target_cultivation": capped_cultivation,
            "changed": (
                target_stage != raw_stage
                or normalized_layer != original_layer
                or capped_cultivation != current_cultivation
            ),
            "legacy": False,
        }

    legacy_threshold = calculate_legacy_realm_threshold(legacy_stage, normalized_layer)
    capped_cultivation = min(current_cultivation, legacy_threshold)
    legacy_progress = min(capped_cultivation / max(legacy_threshold, 1), 1.0)
    final_stage = normalize_realm_stage(legacy_stage)
    final_layer = normalized_layer
    final_threshold = calculate_realm_threshold(final_stage, final_layer)
    final_cultivation = min(int(round(final_threshold * legacy_progress)), final_threshold)

    return {
        "source_stage": legacy_stage,
        "target_stage": final_stage,
        "target_layer": final_layer,
        "target_cultivation": final_cultivation,
        "changed": (
            final_stage != raw_stage
            or final_layer != original_layer
            or final_cultivation != current_cultivation
        ),
        "legacy": True,
    }


def rebase_immortal_realm_state(stage: str | None, layer: int | str | None, cultivation: int | str | None) -> dict[str, Any]:
    raw_stage = str(stage or "").strip()
    target_stage = normalize_realm_stage(raw_stage)
    normalized_layer = normalize_realm_layer(layer)
    try:
        current_cultivation = max(int(cultivation or 0), 0)
    except (TypeError, ValueError):
        current_cultivation = 0
    try:
        original_layer = int(layer or normalized_layer)
    except (TypeError, ValueError):
        original_layer = normalized_layer

    if target_stage not in IMMORTAL_REBASE_SOURCE_STAGES:
        threshold = calculate_realm_threshold(target_stage, normalized_layer)
        capped_cultivation = min(current_cultivation, threshold)
        return {
            "source_stage": raw_stage or target_stage,
            "target_stage": target_stage,
            "target_layer": normalized_layer,
            "target_cultivation": capped_cultivation,
            "changed": (
                target_stage != raw_stage
                or normalized_layer != original_layer
                or capped_cultivation != current_cultivation
            ),
            "rebased": False,
        }

    source_index = IMMORTAL_REBASE_SOURCE_STAGES.index(target_stage)
    final_stage = IMMORTAL_REBASE_TARGET_STAGES[source_index]
    source_threshold = calculate_realm_threshold(target_stage, normalized_layer)
    capped_cultivation = min(current_cultivation, source_threshold)
    progress_ratio = min(capped_cultivation / max(source_threshold, 1), 1.0)
    final_threshold = calculate_realm_threshold(final_stage, normalized_layer)
    final_cultivation = min(int(round(final_threshold * progress_ratio)), final_threshold)
    return {
        "source_stage": raw_stage or target_stage,
        "target_stage": final_stage,
        "target_layer": normalized_layer,
        "target_cultivation": final_cultivation,
        "changed": (
            final_stage != raw_stage
            or normalized_layer != original_layer
            or final_cultivation != current_cultivation
        ),
        "rebased": True,
    }


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
    gender = Column(String(16), nullable=True)
    root_type = Column(String(32), nullable=True)
    root_primary = Column(String(8), nullable=True)
    root_secondary = Column(String(8), nullable=True)
    root_relation = Column(String(16), nullable=True)
    root_bonus = Column(Integer, default=0, nullable=False)
    root_quality = Column(String(32), nullable=True)
    root_quality_level = Column(Integer, default=1, nullable=False)
    root_quality_color = Column(String(32), nullable=True)
    realm_stage = Column(String(32), default=REALM_ORDER[0], nullable=False)
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
    furnace_harvested_at = Column(DateTime, nullable=True)
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
    social_mode = Column(String(16), default="worldly", nullable=False)
    social_mode_updated_at = Column(DateTime, nullable=True)
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


class XiuxianErrorLog(Base):
    __tablename__ = "xiuxian_error_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    tg = Column(BigInteger, nullable=True)
    username = Column(String(64), nullable=True)
    display_name = Column(String(128), nullable=True)
    scope = Column(String(32), nullable=False, default="user")
    level = Column(String(16), nullable=False, default="ERROR")
    operation = Column(String(128), nullable=True)
    method = Column(String(16), nullable=True)
    path = Column(String(255), nullable=True)
    status_code = Column(Integer, nullable=True)
    message = Column(Text, nullable=False)
    detail = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utcnow, nullable=False)


class XiuxianTitle(Base):
    __tablename__ = "xiuxian_titles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(64), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    color = Column(String(255), nullable=True)
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


class XiuxianMentorship(Base):
    __tablename__ = "xiuxian_mentorships"
    __table_args__ = (UniqueConstraint("mentor_tg", "disciple_tg", name="uq_xiuxian_mentorship_pair"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    mentor_tg = Column(BigInteger, nullable=False)
    disciple_tg = Column(BigInteger, nullable=False)
    status = Column(String(16), default="active", nullable=False)
    bond_value = Column(Integer, default=0, nullable=False)
    teach_count = Column(Integer, default=0, nullable=False)
    consult_count = Column(Integer, default=0, nullable=False)
    last_teach_at = Column(DateTime, nullable=True)
    last_consult_at = Column(DateTime, nullable=True)
    mentor_realm_stage_snapshot = Column(String(32), nullable=True)
    mentor_realm_layer_snapshot = Column(Integer, default=0, nullable=False)
    disciple_realm_stage_snapshot = Column(String(32), nullable=True)
    disciple_realm_layer_snapshot = Column(Integer, default=0, nullable=False)
    graduated_at = Column(DateTime, nullable=True)
    ended_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utcnow, nullable=False)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)


class XiuxianMentorshipRequest(Base):
    __tablename__ = "xiuxian_mentorship_requests"

    id = Column(Integer, primary_key=True, autoincrement=True)
    sponsor_tg = Column(BigInteger, nullable=False)
    target_tg = Column(BigInteger, nullable=False)
    sponsor_role = Column(String(16), nullable=False)
    message = Column(String(255), nullable=True)
    status = Column(String(16), default="pending", nullable=False)
    expires_at = Column(DateTime, nullable=True)
    responded_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utcnow, nullable=False)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)


class XiuxianMarriage(Base):
    __tablename__ = "xiuxian_marriages"
    __table_args__ = (UniqueConstraint("husband_tg", "wife_tg", name="uq_xiuxian_marriage_pair"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    husband_tg = Column(BigInteger, nullable=False)
    wife_tg = Column(BigInteger, nullable=False)
    status = Column(String(16), default="active", nullable=False)
    bond_value = Column(Integer, default=0, nullable=False)
    dual_cultivation_count = Column(Integer, default=0, nullable=False)
    last_dual_cultivation_at = Column(DateTime, nullable=True)
    ended_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utcnow, nullable=False)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)


class XiuxianMarriageRequest(Base):
    __tablename__ = "xiuxian_marriage_requests"

    id = Column(Integer, primary_key=True, autoincrement=True)
    sponsor_tg = Column(BigInteger, nullable=False)
    target_tg = Column(BigInteger, nullable=False)
    message = Column(String(255), nullable=True)
    status = Column(String(16), default="pending", nullable=False)
    expires_at = Column(DateTime, nullable=True)
    responded_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utcnow, nullable=False)
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
    salary_min_stay_days = Column(Integer, default=30, nullable=False)
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
    can_plant = Column(Boolean, default=False, nullable=False)
    seed_price_stone = Column(Integer, default=0, nullable=False)
    growth_minutes = Column(Integer, default=0, nullable=False)
    yield_min = Column(Integer, default=0, nullable=False)
    yield_max = Column(Integer, default=0, nullable=False)
    unlock_realm_stage = Column(String(32), nullable=True)
    unlock_realm_layer = Column(Integer, default=1, nullable=False)
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


class XiuxianFarmPlot(Base):
    __tablename__ = "xiuxian_farm_plots"
    __table_args__ = (UniqueConstraint("tg", "slot_index", name="uq_xiuxian_farm_plot_slot"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    tg = Column(BigInteger, nullable=False)
    slot_index = Column(Integer, nullable=False)
    unlocked = Column(Boolean, default=False, nullable=False)
    current_material_id = Column(Integer, ForeignKey("xiuxian_materials.id", ondelete="SET NULL"), nullable=True)
    planted_at = Column(DateTime, nullable=True)
    mature_at = Column(DateTime, nullable=True)
    harvest_deadline_at = Column(DateTime, nullable=True)
    base_yield = Column(Integer, default=0, nullable=False)
    needs_watering = Column(Boolean, default=False, nullable=False)
    watered = Column(Boolean, default=False, nullable=False)
    pest_risk = Column(Boolean, default=False, nullable=False)
    pest_cleared = Column(Boolean, default=False, nullable=False)
    fertilized = Column(Boolean, default=False, nullable=False)
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


class XiuxianAuctionItem(Base):
    __tablename__ = "xiuxian_auction_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    owner_tg = Column(BigInteger, nullable=False)
    owner_display_name = Column(String(128), nullable=True)
    item_kind = Column(String(16), nullable=False)
    item_ref_id = Column(Integer, nullable=False)
    item_name = Column(String(64), nullable=False)
    quantity = Column(Integer, default=1, nullable=False)
    opening_price_stone = Column(Integer, default=0, nullable=False)
    current_price_stone = Column(Integer, default=0, nullable=False)
    bid_increment_stone = Column(Integer, default=1, nullable=False)
    buyout_price_stone = Column(Integer, nullable=True)
    fee_percent = Column(Integer, default=0, nullable=False)
    highest_bidder_tg = Column(BigInteger, nullable=True)
    highest_bidder_display_name = Column(String(128), nullable=True)
    winner_tg = Column(BigInteger, nullable=True)
    winner_display_name = Column(String(128), nullable=True)
    bid_count = Column(Integer, default=0, nullable=False)
    status = Column(String(16), default="active", nullable=False)
    group_chat_id = Column(BigInteger, nullable=True)
    group_message_id = Column(Integer, nullable=True)
    final_price_stone = Column(Integer, nullable=True)
    seller_income_stone = Column(Integer, nullable=True)
    fee_amount_stone = Column(Integer, nullable=True)
    end_at = Column(DateTime, nullable=False)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utcnow, nullable=False)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)


class XiuxianAuctionBid(Base):
    __tablename__ = "xiuxian_auction_bids"

    id = Column(Integer, primary_key=True, autoincrement=True)
    auction_id = Column(Integer, ForeignKey("xiuxian_auction_items.id", ondelete="CASCADE"), nullable=False)
    bidder_tg = Column(BigInteger, nullable=False)
    bidder_display_name = Column(String(128), nullable=True)
    bid_amount_stone = Column(Integer, default=0, nullable=False)
    action_type = Column(String(16), default="bid", nullable=False)
    created_at = Column(DateTime, default=utcnow, nullable=False)


class XiuxianArena(Base):
    __tablename__ = "xiuxian_arenas"

    id = Column(Integer, primary_key=True, autoincrement=True)
    owner_tg = Column(BigInteger, nullable=False)
    owner_display_name = Column(String(128), nullable=True)
    champion_tg = Column(BigInteger, nullable=False)
    champion_display_name = Column(String(128), nullable=True)
    group_chat_id = Column(BigInteger, nullable=False)
    group_message_id = Column(Integer, nullable=True)
    duration_minutes = Column(Integer, default=120, nullable=False)
    challenge_count = Column(Integer, default=0, nullable=False)
    defense_success_count = Column(Integer, default=0, nullable=False)
    champion_change_count = Column(Integer, default=0, nullable=False)
    battle_in_progress = Column(Boolean, default=False, nullable=False)
    current_challenger_tg = Column(BigInteger, nullable=True)
    current_challenger_display_name = Column(String(128), nullable=True)
    last_winner_tg = Column(BigInteger, nullable=True)
    last_winner_display_name = Column(String(128), nullable=True)
    last_loser_tg = Column(BigInteger, nullable=True)
    last_loser_display_name = Column(String(128), nullable=True)
    latest_result_summary = Column(Text, nullable=True)
    status = Column(String(16), default="active", nullable=False)
    end_at = Column(DateTime, nullable=False)
    completed_at = Column(DateTime, nullable=True)
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


def normalize_social_mode(mode: str | None) -> str:
    value = str(mode or "").strip().lower()
    aliases = {
        "worldly": "worldly",
        "world": "worldly",
        "public": "worldly",
        "visible": "worldly",
        "入世": "worldly",
        "出世": "worldly",
        "secluded": "secluded",
        "hidden": "secluded",
        "hide": "secluded",
        "private": "secluded",
        "避世": "secluded",
        "隐世": "secluded",
    }
    return aliases.get(value, "worldly")


def normalize_mentorship_request_role(role: str | None) -> str:
    value = str(role or "").strip().lower()
    aliases = {
        "mentor": "mentor",
        "master": "mentor",
        "teacher": "mentor",
        "收徒": "mentor",
        "invite": "mentor",
        "disciple": "disciple",
        "student": "disciple",
        "apprentice": "disciple",
        "拜师": "disciple",
        "apply": "disciple",
    }
    return aliases.get(value, "disciple")


def normalize_gender(gender: str | None) -> str | None:
    value = str(gender or "").strip().lower()
    if not value:
        return None
    aliases = {
        "male": "male",
        "man": "male",
        "boy": "male",
        "m": "male",
        "男": "male",
        "female": "female",
        "woman": "female",
        "girl": "female",
        "f": "female",
        "女": "female",
    }
    return aliases.get(value)


def normalize_mentorship_status(status: str | None) -> str:
    value = str(status or "").strip().lower()
    aliases = {
        "active": "active",
        "ongoing": "active",
        "在籍": "active",
        "graduated": "graduated",
        "graduate": "graduated",
        "出师": "graduated",
        "dissolved": "dissolved",
        "ended": "dissolved",
        "leave": "dissolved",
        "解除": "dissolved",
    }
    return aliases.get(value, "active")


def normalize_mentorship_request_status(status: str | None) -> str:
    value = str(status or "").strip().lower()
    aliases = {
        "pending": "pending",
        "wait": "pending",
        "待处理": "pending",
        "accepted": "accepted",
        "accept": "accepted",
        "同意": "accepted",
        "rejected": "rejected",
        "reject": "rejected",
        "拒绝": "rejected",
        "cancelled": "cancelled",
        "canceled": "cancelled",
        "cancel": "cancelled",
        "撤回": "cancelled",
        "expired": "expired",
        "过期": "expired",
    }
    return aliases.get(value, "pending")


def normalize_marriage_status(status: str | None) -> str:
    value = str(status or "").strip().lower()
    aliases = {
        "active": "active",
        "married": "active",
        "已婚": "active",
        "结为道侣": "active",
        "divorced": "divorced",
        "divorce": "divorced",
        "ended": "divorced",
        "离婚": "divorced",
        "和离": "divorced",
        "解除": "divorced",
    }
    return aliases.get(value, "active")


def normalize_marriage_request_status(status: str | None) -> str:
    value = str(status or "").strip().lower()
    aliases = {
        "pending": "pending",
        "wait": "pending",
        "待处理": "pending",
        "accepted": "accepted",
        "accept": "accepted",
        "同意": "accepted",
        "rejected": "rejected",
        "reject": "rejected",
        "拒绝": "rejected",
        "cancelled": "cancelled",
        "canceled": "cancelled",
        "cancel": "cancelled",
        "撤回": "cancelled",
        "expired": "expired",
        "过期": "expired",
    }
    return aliases.get(value, "pending")


def serialize_profile(profile: XiuxianProfile | None) -> dict[str, Any] | None:
    if profile is None:
        return None

    realm_stage = normalize_realm_stage(profile.realm_stage)
    social_mode = normalize_social_mode(profile.social_mode)
    gender = normalize_gender(profile.gender)
    return {
        "tg": profile.tg,
        "display_name": profile.display_name,
        "username": profile.username,
        "display_label": profile.display_name or (f"@{profile.username}" if profile.username else f"TG {profile.tg}"),
        "consented": profile.consented,
        "gender": gender,
        "gender_label": GENDER_LABELS.get(gender, ""),
        "gender_set": gender in GENDER_LABELS,
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
        "furnace_harvested_at": serialize_datetime(profile.furnace_harvested_at),
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
        "social_mode": social_mode,
        "social_mode_label": SOCIAL_MODE_LABELS.get(social_mode, "入世"),
        "is_secluded": social_mode == "secluded",
        "social_mode_updated_at": serialize_datetime(profile.social_mode_updated_at),
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


def serialize_mentorship(row: XiuxianMentorship | None) -> dict[str, Any] | None:
    if row is None:
        return None
    status = normalize_mentorship_status(row.status)
    mentor_stage = normalize_realm_stage(row.mentor_realm_stage_snapshot)
    disciple_stage = normalize_realm_stage(row.disciple_realm_stage_snapshot)
    return {
        "id": row.id,
        "mentor_tg": int(row.mentor_tg or 0),
        "disciple_tg": int(row.disciple_tg or 0),
        "status": status,
        "status_label": MENTORSHIP_STATUS_LABELS.get(status, "师徒在籍"),
        "bond_value": max(int(row.bond_value or 0), 0),
        "teach_count": max(int(row.teach_count or 0), 0),
        "consult_count": max(int(row.consult_count or 0), 0),
        "last_teach_at": serialize_datetime(row.last_teach_at),
        "last_consult_at": serialize_datetime(row.last_consult_at),
        "mentor_realm_stage_snapshot": mentor_stage,
        "mentor_realm_layer_snapshot": max(int(row.mentor_realm_layer_snapshot or 0), 0),
        "disciple_realm_stage_snapshot": disciple_stage,
        "disciple_realm_layer_snapshot": max(int(row.disciple_realm_layer_snapshot or 0), 0),
        "mentor_realm_snapshot_text": f"{mentor_stage}{max(int(row.mentor_realm_layer_snapshot or 0), 0)}层" if mentor_stage else "",
        "disciple_realm_snapshot_text": f"{disciple_stage}{max(int(row.disciple_realm_layer_snapshot or 0), 0)}层" if disciple_stage else "",
        "graduated_at": serialize_datetime(row.graduated_at),
        "ended_at": serialize_datetime(row.ended_at),
        "created_at": serialize_datetime(row.created_at),
        "updated_at": serialize_datetime(row.updated_at),
    }


def serialize_mentorship_request(row: XiuxianMentorshipRequest | None) -> dict[str, Any] | None:
    if row is None:
        return None
    sponsor_role = normalize_mentorship_request_role(row.sponsor_role)
    status = normalize_mentorship_request_status(row.status)
    mentor_tg = int(row.sponsor_tg if sponsor_role == "mentor" else row.target_tg)
    disciple_tg = int(row.target_tg if sponsor_role == "mentor" else row.sponsor_tg)
    return {
        "id": row.id,
        "sponsor_tg": int(row.sponsor_tg or 0),
        "target_tg": int(row.target_tg or 0),
        "sponsor_role": sponsor_role,
        "sponsor_role_label": MENTORSHIP_REQUEST_ROLE_LABELS.get(sponsor_role, "拜师申请"),
        "mentor_tg": mentor_tg,
        "disciple_tg": disciple_tg,
        "message": str(row.message or "").strip(),
        "status": status,
        "status_label": MENTORSHIP_REQUEST_STATUS_LABELS.get(status, "待处理"),
        "expires_at": serialize_datetime(row.expires_at),
        "responded_at": serialize_datetime(row.responded_at),
        "created_at": serialize_datetime(row.created_at),
        "updated_at": serialize_datetime(row.updated_at),
    }


def serialize_marriage(row: XiuxianMarriage | None) -> dict[str, Any] | None:
    if row is None:
        return None
    status = normalize_marriage_status(row.status)
    return {
        "id": row.id,
        "husband_tg": int(row.husband_tg or 0),
        "wife_tg": int(row.wife_tg or 0),
        "status": status,
        "status_label": MARRIAGE_STATUS_LABELS.get(status, "已结为道侣"),
        "bond_value": max(int(row.bond_value or 0), 0),
        "dual_cultivation_count": max(int(row.dual_cultivation_count or 0), 0),
        "last_dual_cultivation_at": serialize_datetime(row.last_dual_cultivation_at),
        "ended_at": serialize_datetime(row.ended_at),
        "created_at": serialize_datetime(row.created_at),
        "updated_at": serialize_datetime(row.updated_at),
    }


def serialize_marriage_request(row: XiuxianMarriageRequest | None) -> dict[str, Any] | None:
    if row is None:
        return None
    status = normalize_marriage_request_status(row.status)
    return {
        "id": row.id,
        "sponsor_tg": int(row.sponsor_tg or 0),
        "target_tg": int(row.target_tg or 0),
        "message": str(row.message or "").strip(),
        "status": status,
        "status_label": MARRIAGE_REQUEST_STATUS_LABELS.get(status, "待处理"),
        "expires_at": serialize_datetime(row.expires_at),
        "responded_at": serialize_datetime(row.responded_at),
        "created_at": serialize_datetime(row.created_at),
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
        "min_realm_stage": normalize_realm_stage(sect.min_realm_stage) if sect.min_realm_stage else None,
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
        "salary_min_stay_days": max(int(sect.salary_min_stay_days or 0), 1),
        "entry_hint": sect.entry_hint,
        "enabled": sect.enabled,
    }


def serialize_error_log(row: XiuxianErrorLog | None) -> dict[str, Any] | None:
    if row is None:
        return None
    return {
        "id": row.id,
        "tg": row.tg,
        "username": row.username,
        "display_name": row.display_name,
        "scope": row.scope,
        "level": row.level,
        "operation": row.operation,
        "method": row.method,
        "path": row.path,
        "status_code": row.status_code,
        "message": row.message,
        "detail": row.detail,
        "created_at": serialize_datetime(row.created_at),
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
    can_plant = bool(material.can_plant)
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
        "can_plant": can_plant,
        "seed_price_stone": int(material.seed_price_stone or 0),
        "growth_minutes": int(material.growth_minutes or 0),
        "yield_min": int(material.yield_min or 0),
        "yield_max": int(material.yield_max or 0),
        "unlock_realm_stage": normalize_realm_stage(material.unlock_realm_stage) if material.unlock_realm_stage else None,
        "unlock_realm_layer": int(material.unlock_realm_layer or 1),
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
        "reward_willpower": 0,
        "reward_charisma": 0,
        "reward_karma": 0,
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
    target_display_name = ""
    if envelope.target_tg:
        target_display_name = get_emby_name_map([int(envelope.target_tg)]).get(int(envelope.target_tg), "")
    return {
        "id": envelope.id,
        "creator_tg": envelope.creator_tg,
        "cover_text": envelope.cover_text,
        "image_url": envelope.image_url,
        "mode": envelope.mode,
        "mode_label": ENVELOPE_MODE_LABELS.get(envelope.mode, envelope.mode),
        "target_tg": envelope.target_tg,
        "target_display_name": target_display_name,
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
        "min_realm_stage": normalize_realm_stage(artifact.min_realm_stage) if artifact.min_realm_stage else None,
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
        "min_realm_stage": normalize_realm_stage(pill.min_realm_stage) if pill.min_realm_stage else None,
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
        "min_realm_stage": normalize_realm_stage(talisman.min_realm_stage) if talisman.min_realm_stage else None,
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


def serialize_auction_item(item: XiuxianAuctionItem | None) -> dict[str, Any] | None:
    if item is None:
        return None

    current_price = max(int(item.current_price_stone or 0), 0)
    opening_price = max(int(item.opening_price_stone or 0), 0)
    bid_increment = max(int(item.bid_increment_stone or 0), 1)
    has_bid = current_price > 0 and int(item.bid_count or 0) > 0
    next_bid_price = opening_price if not has_bid else current_price + bid_increment
    buyout_price = int(item.buyout_price_stone or 0)
    current_display_price = current_price if has_bid else opening_price
    status_label = {
        "active": "竞拍中",
        "sold": "已成交",
        "expired": "已流拍",
        "cancelled": "已取消",
    }.get(str(item.status or "active"), str(item.status or "active"))

    return {
        "id": item.id,
        "owner_tg": item.owner_tg,
        "owner_display_name": item.owner_display_name or "",
        "item_kind": item.item_kind,
        "item_kind_label": ITEM_KIND_LABELS.get(item.item_kind, item.item_kind),
        "item_ref_id": item.item_ref_id,
        "item_name": item.item_name,
        "quantity": max(int(item.quantity or 0), 0),
        "opening_price_stone": opening_price,
        "current_price_stone": current_price,
        "current_display_price_stone": current_display_price,
        "bid_increment_stone": bid_increment,
        "next_bid_price_stone": next_bid_price,
        "buyout_price_stone": buyout_price,
        "fee_percent": max(int(item.fee_percent or 0), 0),
        "highest_bidder_tg": item.highest_bidder_tg,
        "highest_bidder_display_name": item.highest_bidder_display_name or "",
        "winner_tg": item.winner_tg,
        "winner_display_name": item.winner_display_name or "",
        "bid_count": max(int(item.bid_count or 0), 0),
        "has_bid": has_bid,
        "status": item.status,
        "status_label": status_label,
        "group_chat_id": item.group_chat_id,
        "group_message_id": item.group_message_id,
        "final_price_stone": int(item.final_price_stone or 0),
        "seller_income_stone": int(item.seller_income_stone or 0),
        "fee_amount_stone": int(item.fee_amount_stone or 0),
        "end_at": serialize_datetime(item.end_at),
        "completed_at": serialize_datetime(item.completed_at),
        "created_at": serialize_datetime(item.created_at),
        "updated_at": serialize_datetime(item.updated_at),
    }


def serialize_auction_bid(item: XiuxianAuctionBid | None) -> dict[str, Any] | None:
    if item is None:
        return None
    return {
        "id": item.id,
        "auction_id": item.auction_id,
        "bidder_tg": item.bidder_tg,
        "bidder_display_name": item.bidder_display_name or "",
        "bid_amount_stone": int(item.bid_amount_stone or 0),
        "action_type": item.action_type,
        "created_at": serialize_datetime(item.created_at),
    }


def serialize_arena(item: XiuxianArena | None) -> dict[str, Any] | None:
    if item is None:
        return None
    remaining_seconds = 0
    if item.end_at is not None:
        remaining_seconds = max(int((item.end_at - utcnow()).total_seconds()), 0)
    status = str(item.status or "active")
    status_label = {
        "active": "开放挑战",
        "finished": "已结束",
        "cancelled": "已取消",
    }.get(status, status)
    if status == "active" and bool(item.battle_in_progress):
        status_label = "攻擂中"
    return {
        "id": item.id,
        "owner_tg": int(item.owner_tg or 0),
        "owner_display_name": item.owner_display_name or "",
        "champion_tg": int(item.champion_tg or 0),
        "champion_display_name": item.champion_display_name or "",
        "group_chat_id": int(item.group_chat_id or 0),
        "group_message_id": int(item.group_message_id or 0) or None,
        "duration_minutes": max(int(item.duration_minutes or 0), 0),
        "challenge_count": max(int(item.challenge_count or 0), 0),
        "defense_success_count": max(int(item.defense_success_count or 0), 0),
        "champion_change_count": max(int(item.champion_change_count or 0), 0),
        "battle_in_progress": bool(item.battle_in_progress),
        "current_challenger_tg": int(item.current_challenger_tg or 0) or None,
        "current_challenger_display_name": item.current_challenger_display_name or "",
        "last_winner_tg": int(item.last_winner_tg or 0) or None,
        "last_winner_display_name": item.last_winner_display_name or "",
        "last_loser_tg": int(item.last_loser_tg or 0) or None,
        "last_loser_display_name": item.last_loser_display_name or "",
        "latest_result_summary": item.latest_result_summary or "",
        "status": status,
        "status_label": status_label,
        "end_at": serialize_datetime(item.end_at),
        "completed_at": serialize_datetime(item.completed_at),
        "created_at": serialize_datetime(item.created_at),
        "updated_at": serialize_datetime(item.updated_at),
        "remaining_seconds": remaining_seconds,
        "ended": item.end_at <= utcnow() if item.end_at is not None else False,
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
    if "duel_bet_seconds" not in settings and "duel_bet_minutes" in settings:
        merged["duel_bet_seconds"] = max(_coerce_int(settings.get("duel_bet_minutes"), DEFAULT_SETTINGS["duel_bet_minutes"]), 1) * 60
    merged.update(resolve_duel_bet_settings(merged))
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
        return profile


def migrate_all_profile_realms(preview_limit: int = 20) -> dict[str, Any]:
    preview: list[dict[str, Any]] = []
    migrated = 0
    repaired = 0
    unchanged = 0
    with Session() as session:
        rows = (
            session.query(XiuxianProfile)
            .filter(XiuxianProfile.consented.is_(True))
            .order_by(XiuxianProfile.updated_at.desc(), XiuxianProfile.tg.asc())
            .all()
        )
        for row in rows:
            result = migrate_legacy_realm_state(row.realm_stage, row.realm_layer, row.cultivation)
            if not result["changed"]:
                result = rebase_immortal_realm_state(row.realm_stage, row.realm_layer, row.cultivation)
            if not result["changed"]:
                unchanged += 1
                continue
            before_stage = str(row.realm_stage or "").strip() or REALM_ORDER[0]
            before_layer = int(row.realm_layer or 0)
            before_cultivation = int(row.cultivation or 0)
            row.realm_stage = result["target_stage"]
            row.realm_layer = int(result["target_layer"])
            row.cultivation = int(result["target_cultivation"])
            row.updated_at = utcnow()
            if result.get("legacy"):
                migrated += 1
            else:
                repaired += 1
            if len(preview) < max(int(preview_limit or 0), 0):
                preview.append(
                    {
                        "tg": int(row.tg),
                        "before_stage": before_stage,
                        "before_layer": before_layer,
                        "before_cultivation": before_cultivation,
                        "after_stage": row.realm_stage,
                        "after_layer": int(row.realm_layer or 0),
                        "after_cultivation": int(row.cultivation or 0),
                        "legacy": bool(result.get("legacy")),
                        "rebased": bool(result.get("rebased")),
                    }
                )
        session.commit()
    return {
        "checked": migrated + repaired + unchanged,
        "migrated": migrated,
        "repaired": repaired,
        "unchanged": unchanged,
        "preview": preview,
    }


def clear_all_xiuxian_user_data() -> dict[str, Any]:
    with Session() as session:
        counts = {
            "duel_bets": session.query(XiuxianDuelBet).delete(synchronize_session=False),
            "duel_pools": session.query(XiuxianDuelBetPool).delete(synchronize_session=False),
            "auction_bids": session.query(XiuxianAuctionBid).delete(synchronize_session=False),
            "auction_items": session.query(XiuxianAuctionItem).delete(synchronize_session=False),
            "arenas": session.query(XiuxianArena).delete(synchronize_session=False),
            "equipped_artifacts": session.query(XiuxianEquippedArtifact).delete(synchronize_session=False),
            "artifact_inventory": session.query(XiuxianArtifactInventory).delete(synchronize_session=False),
            "pill_inventory": session.query(XiuxianPillInventory).delete(synchronize_session=False),
            "talisman_inventory": session.query(XiuxianTalismanInventory).delete(synchronize_session=False),
            "material_inventory": session.query(XiuxianMaterialInventory).delete(synchronize_session=False),
            "farm_plots": session.query(XiuxianFarmPlot).delete(synchronize_session=False),
            "user_titles": session.query(XiuxianUserTitle).delete(synchronize_session=False),
            "user_techniques": session.query(XiuxianUserTechnique).delete(synchronize_session=False),
            "user_recipes": session.query(XiuxianUserRecipe).delete(synchronize_session=False),
            "achievement_progress": session.query(XiuxianAchievementProgress).delete(synchronize_session=False),
            "user_achievements": session.query(XiuxianUserAchievement).delete(synchronize_session=False),
            "marriage_requests": session.query(XiuxianMarriageRequest).delete(synchronize_session=False),
            "marriages": session.query(XiuxianMarriage).delete(synchronize_session=False),
            "mentorship_requests": session.query(XiuxianMentorshipRequest).delete(synchronize_session=False),
            "mentorships": session.query(XiuxianMentorship).delete(synchronize_session=False),
            "explorations": session.query(XiuxianExploration).delete(synchronize_session=False),
            "task_claims": session.query(XiuxianTaskClaim).delete(synchronize_session=False),
            "encounter_instances": session.query(XiuxianEncounterInstance).delete(synchronize_session=False),
            "red_envelope_claims": session.query(XiuxianRedEnvelopeClaim).delete(synchronize_session=False),
            "red_envelopes": session.query(XiuxianRedEnvelope).delete(synchronize_session=False),
            "journals": session.query(XiuxianJournal).delete(synchronize_session=False),
            "duel_records": session.query(XiuxianDuelRecord).delete(synchronize_session=False),
            "player_shop_items": session.query(XiuxianShopItem).filter(XiuxianShopItem.owner_tg.isnot(None)).delete(synchronize_session=False),
            "player_tasks": session.query(XiuxianTask).filter(XiuxianTask.owner_tg.isnot(None)).delete(synchronize_session=False),
            "profiles": session.query(XiuxianProfile).delete(synchronize_session=False),
        }
        counts["official_tasks_reset"] = (
            session.query(XiuxianTask)
            .filter(XiuxianTask.owner_tg.is_(None))
            .update(
                {
                    XiuxianTask.claimants_count: 0,
                    XiuxianTask.winner_tg: None,
                    XiuxianTask.status: "open",
                    XiuxianTask.group_message_id: None,
                    XiuxianTask.updated_at: utcnow(),
                },
                synchronize_session=False,
            )
        )
        session.commit()
    return counts


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
    stale_cutoff = utcnow() - timedelta(seconds=STALE_DUEL_LOCK_GRACE_SECONDS)
    query = session.query(XiuxianDuelBetPool).filter(
        XiuxianDuelBetPool.resolved.is_(False),
        XiuxianDuelBetPool.bets_close_at > stale_cutoff,
        or_(XiuxianDuelBetPool.challenger_tg == tg, XiuxianDuelBetPool.defender_tg == tg),
    )
    if for_update:
        query = query.with_for_update()
    return query.order_by(XiuxianDuelBetPool.id.desc()).first()


def _cleanup_stale_duel_locks(
    session: Session,
    tg: int,
    *,
    for_update: bool = False,
) -> list[int]:
    stale_cutoff = utcnow() - timedelta(seconds=STALE_DUEL_LOCK_GRACE_SECONDS)
    query = session.query(XiuxianDuelBetPool).filter(
        XiuxianDuelBetPool.resolved.is_(False),
        XiuxianDuelBetPool.bets_close_at <= stale_cutoff,
        or_(XiuxianDuelBetPool.challenger_tg == tg, XiuxianDuelBetPool.defender_tg == tg),
    )
    if for_update:
        query = query.with_for_update()
    stale_pools = query.order_by(XiuxianDuelBetPool.id.asc()).all()
    cleaned_ids: list[int] = []

    for pool in stale_pools:
        bets = session.query(XiuxianDuelBet).filter(XiuxianDuelBet.pool_id == pool.id).all()
        for bet in bets:
            refund_amount = max(int(bet.amount or 0), 0)
            if refund_amount <= 0:
                continue
            profile = session.query(XiuxianProfile).filter(XiuxianProfile.tg == int(bet.tg)).with_for_update().first()
            if profile is None:
                continue
            apply_spiritual_stone_delta(
                session,
                int(bet.tg),
                refund_amount,
                action_text="退还过期斗法押注",
                allow_dead=True,
                apply_tribute=True,
            )
        pool.resolved = True
        pool.winner_tg = None
        pool.updated_at = utcnow()
        cleaned_ids.append(int(pool.id))

    if cleaned_ids:
        session.flush()
    return cleaned_ids


def get_active_duel_lock(tg: int) -> dict[str, Any] | None:
    with Session() as session:
        cleaned_ids = _cleanup_stale_duel_locks(session, tg, for_update=False)
        if cleaned_ids:
            session.commit()
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
        cleaned_ids = _cleanup_stale_duel_locks(active_session, tg, for_update=not own_session)
        if cleaned_ids and own_session:
            active_session.commit()
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
    profile.furnace_harvested_at = None


def _active_marriage_for_user(session: Session, tg: int, *, for_update: bool = False) -> XiuxianMarriage | None:
    query = session.query(XiuxianMarriage).filter(
        XiuxianMarriage.status == "active",
        (XiuxianMarriage.husband_tg == int(tg)) | (XiuxianMarriage.wife_tg == int(tg)),
    )
    if for_update:
        query = query.with_for_update()
    return query.order_by(XiuxianMarriage.id.desc()).first()


def _marriage_partner_tg(session: Session, tg: int, *, for_update: bool = False) -> int | None:
    relation = _active_marriage_for_user(session, tg, for_update=for_update)
    if relation is None:
        return None
    if int(relation.husband_tg or 0) == int(tg):
        return int(relation.wife_tg or 0) or None
    return int(relation.husband_tg or 0) or None


def _shared_profile_tgs(session: Session, tg: int, *, for_update: bool = False) -> list[int]:
    actor_tg = int(tg or 0)
    if actor_tg <= 0:
        return []
    partner_tg = _marriage_partner_tg(session, actor_tg, for_update=for_update)
    if not partner_tg or int(partner_tg) == actor_tg:
        return [actor_tg]
    return [actor_tg, int(partner_tg)]


def _shared_profile_rows(session: Session, tg: int, *, for_update: bool = False) -> list[XiuxianProfile]:
    tgs = _shared_profile_tgs(session, tg, for_update=for_update)
    if not tgs:
        return []
    query = session.query(XiuxianProfile).filter(XiuxianProfile.tg.in_(tgs))
    if for_update:
        query = query.with_for_update()
    rows = {int(row.tg): row for row in query.all()}
    return [rows[item] for item in tgs if int(item) in rows]


def get_shared_spiritual_stone_total(tg: int, *, session: Session | None = None, for_update: bool = False) -> int:
    own_session = session is None
    active_session = session or Session()
    try:
        rows = _shared_profile_rows(active_session, tg, for_update=for_update and not own_session)
        return sum(max(int(row.spiritual_stone or 0), 0) for row in rows)
    finally:
        if own_session:
            active_session.close()


def _deduct_shared_spiritual_stone(
    session: Session,
    actor: XiuxianProfile,
    amount: int,
    *,
    action_text: str,
) -> None:
    need = max(int(amount or 0), 0)
    if need <= 0:
        return
    rows = _shared_profile_rows(session, int(actor.tg or 0), for_update=True)
    if not rows:
        raise ValueError("你还没有踏入仙途")
    total = sum(max(int(row.spiritual_stone or 0), 0) for row in rows)
    if total < need:
        raise ValueError("灵石不足")
    ordered_rows = sorted(rows, key=lambda row: (0 if int(row.tg or 0) == int(actor.tg or 0) else 1, int(row.tg or 0)))
    now = utcnow()
    for row in ordered_rows:
        if need <= 0:
            break
        current = max(int(row.spiritual_stone or 0), 0)
        if current <= 0:
            continue
        delta = min(current, need)
        row.spiritual_stone = current - delta
        row.updated_at = now
        need -= delta
    if need > 0:
        raise ValueError(f"{action_text}失败：共享灵石扣减异常。")


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
    if amount < 0:
        _deduct_shared_spiritual_stone(session, profile, -amount, action_text=action_text)
        return {
            "profile": profile,
            "tribute_amount": 0,
            "tribute_master": None,
            "net_delta": amount,
        }

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
        rows = [serialize_artifact(item) for item in query.order_by(XiuxianArtifact.id.desc()).all()]
        return sorted(rows, key=lambda item: _named_quality_sort_key(item or {}, "rarity_level"))


def list_pills(enabled_only: bool = False) -> list[dict[str, Any]]:
    with Session() as session:
        query = session.query(XiuxianPill)
        if enabled_only:
            query = query.filter(XiuxianPill.enabled.is_(True))
        rows = [serialize_pill(item) for item in query.order_by(XiuxianPill.id.desc()).all()]
        return sorted(rows, key=lambda item: _named_quality_sort_key(item or {}, "rarity_level"))


def list_talismans(enabled_only: bool = False) -> list[dict[str, Any]]:
    with Session() as session:
        query = session.query(XiuxianTalisman)
        if enabled_only:
            query = query.filter(XiuxianTalisman.enabled.is_(True))
        rows = [serialize_talisman(item) for item in query.order_by(XiuxianTalisman.id.desc()).all()]
        return sorted(rows, key=lambda item: _named_quality_sort_key(item or {}, "rarity_level"))


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


def _named_quality_sort_key(payload: dict[str, Any], quality_key: str = "rarity_level") -> tuple[int, str, int]:
    return (
        -_coerce_int(payload.get(quality_key), 0),
        str(payload.get("name") or ""),
        -_coerce_int(payload.get("id"), 0),
    )


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


def _fallback_duel_bet_amount_options(minimum: int, maximum: int) -> list[int]:
    if maximum <= minimum:
        return [minimum]
    midpoint = (minimum + maximum) // 2
    values = [minimum]
    if midpoint not in {minimum, maximum}:
        values.append(midpoint)
    values.append(maximum)
    return sorted(set(values))


def _normalize_duel_bet_amount_options(
    raw_value: Any,
    *,
    minimum: int,
    maximum: int,
) -> list[int]:
    if isinstance(raw_value, str):
        items = [part for part in re.split(r"[\s,，、;；|/]+", raw_value.strip()) if part]
    elif isinstance(raw_value, (list, tuple, set)):
        items = list(raw_value)
    elif raw_value is None:
        items = list(DEFAULT_SETTINGS.get("duel_bet_amount_options") or [])
    else:
        items = [raw_value]

    values: list[int] = []
    seen: set[int] = set()
    for item in items:
        amount = _coerce_int(item, 0)
        if amount < minimum or amount > maximum or amount in seen:
            continue
        seen.add(amount)
        values.append(amount)
    values.sort()
    return values[:8]


def resolve_duel_bet_settings(settings: dict[str, Any] | None = None) -> dict[str, Any]:
    source = settings if isinstance(settings, dict) else {}
    default_options = list(DEFAULT_SETTINGS.get("duel_bet_amount_options") or [10, 50, 100])
    default_minimum = max(_coerce_int(DEFAULT_SETTINGS.get("duel_bet_min_amount"), min(default_options or [10])), 1)
    default_maximum = max(
        _coerce_int(DEFAULT_SETTINGS.get("duel_bet_max_amount"), max(default_options or [100])),
        default_minimum,
    )
    legacy_minutes = max(_coerce_int(source.get("duel_bet_minutes"), DEFAULT_SETTINGS.get("duel_bet_minutes", 2)), 1)
    raw_seconds = source.get("duel_bet_seconds")
    if raw_seconds is None:
        raw_seconds = legacy_minutes * 60
    seconds = min(max(_coerce_int(raw_seconds, DEFAULT_SETTINGS.get("duel_bet_seconds", 120)), 10), 3600)
    enabled = _coerce_bool(source.get("duel_bet_enabled"), _coerce_bool(DEFAULT_SETTINGS.get("duel_bet_enabled"), True))
    minimum = min(max(_coerce_int(source.get("duel_bet_min_amount"), default_minimum), 1), 1_000_000)
    maximum = min(max(_coerce_int(source.get("duel_bet_max_amount"), default_maximum), minimum), 1_000_000)
    options = _normalize_duel_bet_amount_options(
        source.get("duel_bet_amount_options"),
        minimum=minimum,
        maximum=maximum,
    )
    if not options:
        options = _fallback_duel_bet_amount_options(minimum, maximum)
    return {
        "duel_bet_enabled": enabled,
        "duel_bet_seconds": seconds,
        "duel_bet_min_amount": minimum,
        "duel_bet_max_amount": maximum,
        "duel_bet_amount_options": options,
    }


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
        "color": str(fields.get("color") or "").strip()[:255],
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
        "salary_min_stay_days": max(_coerce_int(fields.get("salary_min_stay_days"), DEFAULT_SETTINGS["sect_salary_min_stay_days"]), 1),
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


def _shared_inventory_owner_tgs(session: Session, tg: int, *, for_update: bool = False) -> list[int]:
    owner_tgs = _shared_profile_tgs(session, tg, for_update=for_update)
    return [int(item) for item in owner_tgs if int(item) > 0]


def _ordered_owner_rows(session: Session, model_cls, tg: int, ref_field: str, ref_id: int) -> list[Any]:
    owner_tgs = _shared_inventory_owner_tgs(session, tg, for_update=True)
    if not owner_tgs:
        return []
    ref_column = getattr(model_cls, ref_field)
    rows = (
        session.query(model_cls)
        .filter(model_cls.tg.in_(owner_tgs), ref_column == int(ref_id))
        .with_for_update()
        .all()
    )
    row_map = {int(row.tg or 0): row for row in rows}
    return [row_map[item] for item in owner_tgs if item in row_map]


def list_user_artifacts(tg: int) -> list[dict[str, Any]]:
    with Session() as session:
        owner_tgs = _shared_inventory_owner_tgs(session, tg)
        if not owner_tgs:
            return []
        rows = (
            session.query(XiuxianArtifactInventory, XiuxianArtifact)
            .join(XiuxianArtifact, XiuxianArtifact.id == XiuxianArtifactInventory.artifact_id)
            .filter(XiuxianArtifactInventory.tg.in_(owner_tgs))
            .order_by(XiuxianArtifact.id.desc())
            .all()
        )
        equipped_counts: dict[int, int] = {}
        for equipped in (
            session.query(XiuxianEquippedArtifact)
            .filter(XiuxianEquippedArtifact.tg.in_(owner_tgs))
            .all()
        ):
            artifact_id = int(equipped.artifact_id or 0)
            if artifact_id <= 0:
                continue
            equipped_counts[artifact_id] = equipped_counts.get(artifact_id, 0) + 1
        payload_map: dict[int, dict[str, Any]] = {}
        for inventory, artifact in rows:
            artifact_id = int(inventory.artifact_id or 0)
            entry = payload_map.get(artifact_id)
            if entry is None:
                entry = {
                    "quantity": 0,
                    "bound_quantity": 0,
                    "equipped_quantity": equipped_counts.get(artifact_id, 0),
                    "artifact": serialize_artifact(artifact),
                }
                payload_map[artifact_id] = entry
            quantity = max(int(inventory.quantity or 0), 0)
            entry["quantity"] += quantity
            entry["bound_quantity"] += max(min(int(inventory.bound_quantity or 0), quantity), 0)
        payload = list(payload_map.values())
        return sorted(
            payload,
            key=lambda row: _named_quality_sort_key((row.get("artifact") or {}), "rarity_level"),
        )


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

        starter_artifact_id = _starter_artifact_id_in_session(session)
        starter_protection_active = bool(starter_artifact_id) and _starter_artifact_protection_active_in_session(session, owner_tg)
        equipped_rows = (
            session.query(XiuxianEquippedArtifact)
            .filter(XiuxianEquippedArtifact.tg == owner_tg)
            .order_by(XiuxianEquippedArtifact.slot.asc(), XiuxianEquippedArtifact.id.asc())
            .with_for_update()
            .all()
        )
        equipped_count_map: dict[int, int] = {}
        for row in equipped_rows:
            artifact_id = int(row.artifact_id or 0)
            equipped_count_map[artifact_id] = equipped_count_map.get(artifact_id, 0) + 1

        weighted_ids: list[int] = []
        for row in owner_rows:
            total_quantity = int(row.quantity or 0)
            bound_quantity = max(min(int(row.bound_quantity or 0), total_quantity), 0)
            protected_quantity = min(total_quantity, bound_quantity + equipped_count_map.get(int(row.artifact_id), 0))
            if starter_protection_active and int(row.artifact_id or 0) == int(starter_artifact_id or 0):
                protected_quantity = max(protected_quantity, min(total_quantity, 1))
            weighted_ids.extend([int(row.artifact_id)] * max(total_quantity - protected_quantity, 0))
        if not weighted_ids:
            return None

        artifact_id = random.choice(weighted_ids)
        owner_row = next((row for row in owner_rows if int(row.artifact_id) == artifact_id), None)
        if owner_row is None:
            return None

        owner_row.quantity = max(int(owner_row.quantity or 0) - 1, 0)
        owner_row.bound_quantity = max(min(int(owner_row.bound_quantity or 0), int(owner_row.quantity or 0)), 0)
        owner_row.updated_at = utcnow()

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
            "was_equipped": False,
            "owner_remaining": owner_remaining,
            "receiver_quantity": receiver_quantity,
        }


def list_user_pills(tg: int) -> list[dict[str, Any]]:
    with Session() as session:
        owner_tgs = _shared_inventory_owner_tgs(session, tg)
        if not owner_tgs:
            return []
        rows = (
            session.query(XiuxianPillInventory, XiuxianPill)
            .join(XiuxianPill, XiuxianPill.id == XiuxianPillInventory.pill_id)
            .filter(XiuxianPillInventory.tg.in_(owner_tgs))
            .order_by(XiuxianPill.id.desc())
            .all()
        )
        payload_map: dict[int, dict[str, Any]] = {}
        for inventory, pill in rows:
            pill_id = int(inventory.pill_id or 0)
            entry = payload_map.get(pill_id)
            if entry is None:
                entry = {"quantity": 0, "pill": serialize_pill(pill)}
                payload_map[pill_id] = entry
            entry["quantity"] += max(int(inventory.quantity or 0), 0)
        payload = list(payload_map.values())
        return sorted(
            payload,
            key=lambda row: _named_quality_sort_key((row.get("pill") or {}), "rarity_level"),
        )


def list_user_talismans(tg: int) -> list[dict[str, Any]]:
    with Session() as session:
        owner_tgs = _shared_inventory_owner_tgs(session, tg)
        if not owner_tgs:
            return []
        rows = (
            session.query(XiuxianTalismanInventory, XiuxianTalisman)
            .join(XiuxianTalisman, XiuxianTalisman.id == XiuxianTalismanInventory.talisman_id)
            .filter(XiuxianTalismanInventory.tg.in_(owner_tgs))
            .order_by(XiuxianTalisman.id.desc())
            .all()
        )
        payload_map: dict[int, dict[str, Any]] = {}
        for inventory, talisman in rows:
            talisman_id = int(inventory.talisman_id or 0)
            entry = payload_map.get(talisman_id)
            if entry is None:
                entry = {
                    "quantity": 0,
                    "bound_quantity": 0,
                    "talisman": serialize_talisman(talisman),
                }
                payload_map[talisman_id] = entry
            quantity = max(int(inventory.quantity or 0), 0)
            entry["quantity"] += quantity
            entry["bound_quantity"] += max(min(int(inventory.bound_quantity or 0), quantity), 0)
        payload = list(payload_map.values())
        return sorted(
            payload,
            key=lambda row: _named_quality_sort_key((row.get("talisman") or {}), "rarity_level"),
        )


def consume_user_pill(tg: int, pill_id: int, quantity: int = 1) -> bool:
    with Session() as session:
        remaining = max(int(quantity or 0), 1)
        rows = _ordered_owner_rows(session, XiuxianPillInventory, tg, "pill_id", pill_id)
        total_quantity = sum(max(int(row.quantity or 0), 0) for row in rows)
        if total_quantity < remaining:
            return False

        now = utcnow()
        for row in rows:
            if remaining <= 0:
                break
            available = max(int(row.quantity or 0), 0)
            if available <= 0:
                continue
            delta = min(available, remaining)
            row.quantity = available - delta
            row.updated_at = now
            remaining -= delta
            if row.quantity <= 0:
                session.delete(row)
        session.commit()
        return True


def consume_user_talisman(tg: int, talisman_id: int, quantity: int = 1) -> bool:
    with Session() as session:
        remaining = max(int(quantity or 0), 1)
        rows = _ordered_owner_rows(session, XiuxianTalismanInventory, tg, "talisman_id", talisman_id)
        total_quantity = sum(max(int(row.quantity or 0), 0) for row in rows)
        if total_quantity < remaining:
            return False

        now = utcnow()
        for row in rows:
            if remaining <= 0:
                break
            available = max(int(row.quantity or 0), 0)
            if available <= 0:
                continue
            delta = min(available, remaining)
            row.quantity = available - delta
            row.bound_quantity = max(min(int(row.bound_quantity or 0), int(row.quantity or 0)), 0)
            row.updated_at = now
            remaining -= delta
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
        remaining = max(int(quantity or 0), 1)
        rows = _ordered_owner_rows(session, XiuxianArtifactInventory, tg, "artifact_id", artifact_id)
        if not rows:
            return False
        starter_artifact_id = _starter_artifact_id_in_session(session)
        owner_tgs = _shared_inventory_owner_tgs(session, tg, for_update=True)
        equipped_count = 0
        for _equipped in (
            session.query(XiuxianEquippedArtifact)
            .filter(
                XiuxianEquippedArtifact.tg.in_(owner_tgs),
                XiuxianEquippedArtifact.artifact_id == int(artifact_id),
            )
            .with_for_update()
            .all()
        ):
            equipped_count += 1
        total_quantity = sum(max(int(row.quantity or 0), 0) for row in rows)
        total_bound_quantity = sum(
            max(min(int(row.bound_quantity or 0), max(int(row.quantity or 0), 0)), 0)
            for row in rows
        )
        total_available = max(total_quantity - total_bound_quantity - equipped_count, 0)
        if total_available < remaining:
            return False

        now = utcnow()
        release_owner_tgs: set[int] = set()
        for row in rows:
            if remaining <= 0:
                break
            quantity_value = max(int(row.quantity or 0), 0)
            bound_quantity = max(min(int(row.bound_quantity or 0), quantity_value), 0)
            available = max(quantity_value - bound_quantity, 0)
            if available <= 0:
                continue
            delta = min(available, remaining)
            row.quantity = quantity_value - delta
            row.bound_quantity = max(min(bound_quantity, int(row.quantity or 0)), 0)
            row.updated_at = now
            if delta > 0 and int(artifact_id or 0) == int(starter_artifact_id or 0):
                release_owner_tgs.add(int(row.tg or 0))
            remaining -= delta
            if row.quantity <= 0:
                session.delete(row)
        session.commit()
        for owner_tg in release_owner_tgs:
            release_starter_artifact_protection(
                owner_tg,
                reason="你将新手法宝用于上架出售或拍卖，此后它不再受新手保护，日后重修也不会再次补发。",
            )
        return True


def use_user_pill_listing_stock(tg: int, pill_id: int, quantity: int = 1) -> bool:
    with Session() as session:
        remaining = max(int(quantity or 0), 1)
        rows = _ordered_owner_rows(session, XiuxianPillInventory, tg, "pill_id", pill_id)
        total_quantity = sum(max(int(row.quantity or 0), 0) for row in rows)
        if total_quantity < remaining:
            return False

        now = utcnow()
        for row in rows:
            if remaining <= 0:
                break
            available = max(int(row.quantity or 0), 0)
            if available <= 0:
                continue
            delta = min(available, remaining)
            row.quantity = available - delta
            row.updated_at = now
            remaining -= delta
            if row.quantity <= 0:
                session.delete(row)
        session.commit()
        return True


def use_user_material_listing_stock(tg: int, material_id: int, quantity: int = 1) -> bool:
    with Session() as session:
        remaining = max(int(quantity or 0), 1)
        rows = _ordered_owner_rows(session, XiuxianMaterialInventory, tg, "material_id", material_id)
        total_quantity = sum(max(int(row.quantity or 0), 0) for row in rows)
        if total_quantity < remaining:
            return False

        now = utcnow()
        for row in rows:
            if remaining <= 0:
                break
            available = max(int(row.quantity or 0), 0)
            if available <= 0:
                continue
            delta = min(available, remaining)
            row.quantity = available - delta
            row.updated_at = now
            remaining -= delta
            if row.quantity <= 0:
                session.delete(row)
        session.commit()
        return True


def use_user_talisman_listing_stock(tg: int, talisman_id: int, quantity: int = 1) -> bool:
    with Session() as session:
        remaining = max(int(quantity or 0), 1)
        rows = _ordered_owner_rows(session, XiuxianTalismanInventory, tg, "talisman_id", talisman_id)
        if not rows:
            return False
        total_available = 0
        for row in rows:
            quantity_value = max(int(row.quantity or 0), 0)
            bound_quantity = max(min(int(row.bound_quantity or 0), quantity_value), 0)
            total_available += max(quantity_value - bound_quantity, 0)
        if total_available < remaining:
            return False

        now = utcnow()
        for row in rows:
            if remaining <= 0:
                break
            quantity_value = max(int(row.quantity or 0), 0)
            bound_quantity = max(min(int(row.bound_quantity or 0), quantity_value), 0)
            available = max(quantity_value - bound_quantity, 0)
            if available <= 0:
                continue
            delta = min(available, remaining)
            row.quantity = quantity_value - delta
            row.bound_quantity = max(min(bound_quantity, int(row.quantity or 0)), 0)
            row.updated_at = now
            remaining -= delta
            if row.quantity <= 0:
                session.delete(row)
        session.commit()
        return True


def bind_user_artifact(tg: int, artifact_id: int, quantity: int = 1) -> dict[str, Any]:
    amount = max(int(quantity or 0), 1)
    with Session() as session:
        rows = _ordered_owner_rows(session, XiuxianArtifactInventory, tg, "artifact_id", artifact_id)
        if not rows:
            raise ValueError("你的背包里没有这件法宝。")
        bindable_quantity = 0
        for row in rows:
            quantity_value = max(int(row.quantity or 0), 0)
            bound_quantity = max(min(int(row.bound_quantity or 0), quantity_value), 0)
            bindable_quantity += max(quantity_value - bound_quantity, 0)
        if bindable_quantity < amount:
            raise ValueError("没有足够的未绑定法宝可供绑定。")
        remaining = amount
        now = utcnow()
        for row in rows:
            if remaining <= 0:
                break
            quantity_value = max(int(row.quantity or 0), 0)
            bound_quantity = max(min(int(row.bound_quantity or 0), quantity_value), 0)
            available = max(quantity_value - bound_quantity, 0)
            if available <= 0:
                continue
            delta = min(available, remaining)
            row.bound_quantity = bound_quantity + delta
            row.updated_at = now
            remaining -= delta
        session.commit()
        total_quantity = sum(max(int(row.quantity or 0), 0) for row in rows)
        total_bound_quantity = sum(
            max(min(int(row.bound_quantity or 0), max(int(row.quantity or 0), 0)), 0)
            for row in rows
        )
        return {
            "quantity": total_quantity,
            "bound_quantity": total_bound_quantity,
        }


def unbind_user_artifact(tg: int, artifact_id: int, cost: int, quantity: int = 1) -> dict[str, Any]:
    amount = max(int(quantity or 0), 1)
    unit_cost = max(int(cost or 0), 0)
    total_cost = unit_cost * amount
    with Session() as session:
        profile = session.query(XiuxianProfile).filter(XiuxianProfile.tg == tg).with_for_update().first()
        rows = _ordered_owner_rows(session, XiuxianArtifactInventory, tg, "artifact_id", artifact_id)
        if profile is None or not rows:
            raise ValueError("你的背包里没有这件法宝。")
        total_bound_quantity = sum(
            max(min(int(row.bound_quantity or 0), max(int(row.quantity or 0), 0)), 0)
            for row in rows
        )
        if total_bound_quantity < amount:
            raise ValueError("没有足够的已绑定法宝可供解绑。")
        if total_cost > 0:
            apply_spiritual_stone_delta(
                session,
                tg,
                -total_cost,
                action_text="解绑法宝",
                allow_dead=False,
                apply_tribute=False,
            )
        remaining = amount
        now = utcnow()
        for row in rows:
            if remaining <= 0:
                break
            bound_quantity = max(min(int(row.bound_quantity or 0), max(int(row.quantity or 0), 0)), 0)
            if bound_quantity <= 0:
                continue
            delta = min(bound_quantity, remaining)
            row.bound_quantity = bound_quantity - delta
            row.updated_at = now
            remaining -= delta
        session.commit()
        total_quantity = sum(max(int(row.quantity or 0), 0) for row in rows)
        refreshed_bound_quantity = sum(
            max(min(int(row.bound_quantity or 0), max(int(row.quantity or 0), 0)), 0)
            for row in rows
        )
        return {
            "quantity": total_quantity,
            "bound_quantity": refreshed_bound_quantity,
            "cost": total_cost,
            "balance": get_shared_spiritual_stone_total(tg, session=session, for_update=False),
        }


def bind_user_talisman(tg: int, talisman_id: int, quantity: int = 1) -> dict[str, Any]:
    amount = max(int(quantity or 0), 1)
    with Session() as session:
        rows = _ordered_owner_rows(session, XiuxianTalismanInventory, tg, "talisman_id", talisman_id)
        if not rows:
            raise ValueError("你的背包里没有这张符箓。")
        bindable_quantity = 0
        for row in rows:
            quantity_value = max(int(row.quantity or 0), 0)
            bound_quantity = max(min(int(row.bound_quantity or 0), quantity_value), 0)
            bindable_quantity += max(quantity_value - bound_quantity, 0)
        if bindable_quantity < amount:
            raise ValueError("没有足够的未绑定符箓可供绑定。")
        remaining = amount
        now = utcnow()
        for row in rows:
            if remaining <= 0:
                break
            quantity_value = max(int(row.quantity or 0), 0)
            bound_quantity = max(min(int(row.bound_quantity or 0), quantity_value), 0)
            available = max(quantity_value - bound_quantity, 0)
            if available <= 0:
                continue
            delta = min(available, remaining)
            row.bound_quantity = bound_quantity + delta
            row.updated_at = now
            remaining -= delta
        session.commit()
        total_quantity = sum(max(int(row.quantity or 0), 0) for row in rows)
        total_bound_quantity = sum(
            max(min(int(row.bound_quantity or 0), max(int(row.quantity or 0), 0)), 0)
            for row in rows
        )
        return {
            "quantity": total_quantity,
            "bound_quantity": total_bound_quantity,
        }


def unbind_user_talisman(tg: int, talisman_id: int, cost: int, quantity: int = 1) -> dict[str, Any]:
    amount = max(int(quantity or 0), 1)
    unit_cost = max(int(cost or 0), 0)
    total_cost = unit_cost * amount
    with Session() as session:
        profile = session.query(XiuxianProfile).filter(XiuxianProfile.tg == tg).with_for_update().first()
        rows = _ordered_owner_rows(session, XiuxianTalismanInventory, tg, "talisman_id", talisman_id)
        if profile is None or not rows:
            raise ValueError("你的背包里没有这张符箓。")
        total_bound_quantity = sum(
            max(min(int(row.bound_quantity or 0), max(int(row.quantity or 0), 0)), 0)
            for row in rows
        )
        if total_bound_quantity < amount:
            raise ValueError("没有足够的已绑定符箓可供解绑。")
        if total_cost > 0:
            apply_spiritual_stone_delta(
                session,
                tg,
                -total_cost,
                action_text="解绑符箓",
                allow_dead=False,
                apply_tribute=False,
            )
        remaining = amount
        now = utcnow()
        for row in rows:
            if remaining <= 0:
                break
            bound_quantity = max(min(int(row.bound_quantity or 0), max(int(row.quantity or 0), 0)), 0)
            if bound_quantity <= 0:
                continue
            delta = min(bound_quantity, remaining)
            row.bound_quantity = bound_quantity - delta
            row.updated_at = now
            remaining -= delta
        session.commit()
        total_quantity = sum(max(int(row.quantity or 0), 0) for row in rows)
        refreshed_bound_quantity = sum(
            max(min(int(row.bound_quantity or 0), max(int(row.quantity or 0), 0)), 0)
            for row in rows
        )
        return {
            "quantity": total_quantity,
            "bound_quantity": refreshed_bound_quantity,
            "cost": total_cost,
            "balance": get_shared_spiritual_stone_total(tg, session=session, for_update=False),
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
        return serialize_profile(profile)


def set_current_technique(tg: int, technique_id: int | None) -> dict[str, Any] | None:
    with Session() as session:
        profile = session.query(XiuxianProfile).filter(XiuxianProfile.tg == tg).first()
        if profile is None:
            return None
        profile.current_technique_id = technique_id
        profile.updated_at = utcnow()
        session.commit()
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


def _auction_has_bid(item: XiuxianAuctionItem) -> bool:
    return max(int(item.current_price_stone or 0), 0) > 0 and max(int(item.bid_count or 0), 0) > 0


def _auction_next_bid_price(item: XiuxianAuctionItem) -> int:
    opening_price = max(int(item.opening_price_stone or 0), 0)
    current_price = max(int(item.current_price_stone or 0), 0)
    bid_increment = max(int(item.bid_increment_stone or 0), 1)
    return opening_price if not _auction_has_bid(item) else current_price + bid_increment


def _grant_auction_item_to_inventory(
    session: Session,
    *,
    tg: int,
    item_kind: str,
    item_ref_id: int,
    quantity: int,
) -> None:
    amount = max(int(quantity or 0), 0)
    if amount <= 0:
        return

    if item_kind == "artifact":
        row = (
            session.query(XiuxianArtifactInventory)
            .filter(
                XiuxianArtifactInventory.tg == int(tg),
                XiuxianArtifactInventory.artifact_id == int(item_ref_id),
            )
            .with_for_update()
            .first()
        )
        if row is None:
            row = XiuxianArtifactInventory(tg=int(tg), artifact_id=int(item_ref_id), quantity=0, bound_quantity=0)
            session.add(row)
        row.quantity = int(row.quantity or 0) + amount
        row.bound_quantity = max(min(int(row.bound_quantity or 0), int(row.quantity or 0)), 0)
        row.updated_at = utcnow()
        return

    if item_kind == "pill":
        row = (
            session.query(XiuxianPillInventory)
            .filter(
                XiuxianPillInventory.tg == int(tg),
                XiuxianPillInventory.pill_id == int(item_ref_id),
            )
            .with_for_update()
            .first()
        )
        if row is None:
            row = XiuxianPillInventory(tg=int(tg), pill_id=int(item_ref_id), quantity=0)
            session.add(row)
        row.quantity = int(row.quantity or 0) + amount
        row.updated_at = utcnow()
        return

    if item_kind == "talisman":
        row = (
            session.query(XiuxianTalismanInventory)
            .filter(
                XiuxianTalismanInventory.tg == int(tg),
                XiuxianTalismanInventory.talisman_id == int(item_ref_id),
            )
            .with_for_update()
            .first()
        )
        if row is None:
            row = XiuxianTalismanInventory(tg=int(tg), talisman_id=int(item_ref_id), quantity=0, bound_quantity=0)
            session.add(row)
        row.quantity = int(row.quantity or 0) + amount
        row.bound_quantity = max(min(int(row.bound_quantity or 0), int(row.quantity or 0)), 0)
        row.updated_at = utcnow()
        return

    if item_kind == "material":
        row = (
            session.query(XiuxianMaterialInventory)
            .filter(
                XiuxianMaterialInventory.tg == int(tg),
                XiuxianMaterialInventory.material_id == int(item_ref_id),
            )
            .with_for_update()
            .first()
        )
        if row is None:
            row = XiuxianMaterialInventory(tg=int(tg), material_id=int(item_ref_id), quantity=0)
            session.add(row)
        row.quantity = int(row.quantity or 0) + amount
        row.updated_at = utcnow()
        return

    raise ValueError("不支持的拍卖物品类型")


def list_auction_items(
    owner_tg: int | None = None,
    *,
    status: str | None = None,
    include_inactive: bool = False,
    exclude_owner_tg: int | None = None,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    with Session() as session:
        query = session.query(XiuxianAuctionItem)
        if owner_tg is not None:
            query = query.filter(XiuxianAuctionItem.owner_tg == int(owner_tg))
        if exclude_owner_tg is not None:
            query = query.filter(XiuxianAuctionItem.owner_tg != int(exclude_owner_tg))
        if status:
            query = query.filter(XiuxianAuctionItem.status == str(status))
        elif not include_inactive:
            query = query.filter(XiuxianAuctionItem.status == "active")
        query = query.order_by(XiuxianAuctionItem.id.desc())
        if limit is not None:
            query = query.limit(max(int(limit or 0), 1))
        return [serialize_auction_item(item) for item in query.all()]


def get_auction_item(auction_id: int) -> dict[str, Any] | None:
    with Session() as session:
        row = session.query(XiuxianAuctionItem).filter(XiuxianAuctionItem.id == int(auction_id)).first()
        return serialize_auction_item(row)


def create_auction_item(
    *,
    owner_tg: int,
    owner_display_name: str,
    item_kind: str,
    item_ref_id: int,
    item_name: str,
    quantity: int,
    opening_price_stone: int,
    bid_increment_stone: int,
    buyout_price_stone: int | None,
    fee_percent: int,
    end_at: datetime,
    group_chat_id: int | None = None,
    group_message_id: int | None = None,
) -> dict[str, Any]:
    opening_price = max(int(opening_price_stone or 0), 0)
    bid_increment = max(int(bid_increment_stone or 0), 1)
    buyout_price = max(int(buyout_price_stone or 0), 0) or None
    if buyout_price is not None and buyout_price < opening_price:
        raise ValueError("一口价不能低于起拍价")

    with Session() as session:
        item = XiuxianAuctionItem(
            owner_tg=int(owner_tg),
            owner_display_name=str(owner_display_name or "").strip(),
            item_kind=str(item_kind or "").strip(),
            item_ref_id=int(item_ref_id),
            item_name=str(item_name or "").strip(),
            quantity=max(int(quantity or 0), 1),
            opening_price_stone=opening_price,
            current_price_stone=0,
            bid_increment_stone=bid_increment,
            buyout_price_stone=buyout_price,
            fee_percent=max(int(fee_percent or 0), 0),
            status="active",
            group_chat_id=int(group_chat_id) if group_chat_id is not None else None,
            group_message_id=int(group_message_id) if group_message_id is not None else None,
            end_at=end_at,
        )
        session.add(item)
        session.commit()
        session.refresh(item)
        return serialize_auction_item(item)


def update_auction_item(auction_id: int, **fields) -> dict[str, Any] | None:
    with Session() as session:
        item = session.query(XiuxianAuctionItem).filter(XiuxianAuctionItem.id == int(auction_id)).first()
        if item is None:
            return None
        for key, value in fields.items():
            if not hasattr(item, key):
                continue
            setattr(item, key, value)
        item.updated_at = utcnow()
        session.commit()
        session.refresh(item)
        return serialize_auction_item(item)


def list_auction_bids(auction_id: int, *, limit: int = 50) -> list[dict[str, Any]]:
    with Session() as session:
        rows = (
            session.query(XiuxianAuctionBid)
            .filter(XiuxianAuctionBid.auction_id == int(auction_id))
            .order_by(XiuxianAuctionBid.id.desc())
            .limit(max(int(limit or 50), 1))
            .all()
        )
        return [serialize_auction_bid(item) for item in rows]


def _settle_auction_row(session: Session, auction: XiuxianAuctionItem) -> dict[str, Any]:
    now = utcnow()
    current_price = max(int(auction.current_price_stone or 0), 0)
    fee_percent = max(int(auction.fee_percent or 0), 0)
    has_bid = _auction_has_bid(auction)

    auction.updated_at = now
    auction.completed_at = now

    if not has_bid:
        _grant_auction_item_to_inventory(
            session,
            tg=int(auction.owner_tg),
            item_kind=str(auction.item_kind or ""),
            item_ref_id=int(auction.item_ref_id),
            quantity=int(auction.quantity or 0),
        )
        auction.status = "expired"
        auction.winner_tg = None
        auction.winner_display_name = None
        auction.final_price_stone = 0
        auction.seller_income_stone = 0
        auction.fee_amount_stone = 0
        return {
            "result": "expired",
            "auction": serialize_auction_item(auction),
            "winner_tg": None,
            "winner_display_name": None,
            "seller_tg": int(auction.owner_tg),
        }

    fee_amount = current_price * fee_percent // 100
    seller_income = max(current_price - fee_amount, 0)

    winner_tg = int(auction.highest_bidder_tg or 0)
    if winner_tg <= 0:
        raise ValueError("拍卖状态异常，缺少最高出价者")

    seller = (
        session.query(XiuxianProfile)
        .filter(XiuxianProfile.tg == int(auction.owner_tg))
        .with_for_update()
        .first()
    )
    if seller is not None and seller_income > 0:
        apply_spiritual_stone_delta(
            session,
            int(auction.owner_tg),
            seller_income,
            action_text="拍卖成交入账",
            allow_dead=True,
            apply_tribute=False,
        )

    _grant_auction_item_to_inventory(
        session,
        tg=winner_tg,
        item_kind=str(auction.item_kind or ""),
        item_ref_id=int(auction.item_ref_id),
        quantity=int(auction.quantity or 0),
    )

    auction.status = "sold"
    auction.winner_tg = winner_tg
    auction.winner_display_name = str(auction.highest_bidder_display_name or "").strip() or None
    auction.final_price_stone = current_price
    auction.seller_income_stone = seller_income
    auction.fee_amount_stone = fee_amount

    return {
        "result": "sold",
        "auction": serialize_auction_item(auction),
        "winner_tg": winner_tg,
        "winner_display_name": auction.winner_display_name or "",
        "seller_tg": int(auction.owner_tg),
        "seller_income_stone": seller_income,
        "fee_amount_stone": fee_amount,
    }


def finalize_auction_item(auction_id: int, *, force: bool = False) -> dict[str, Any] | None:
    with Session() as session:
        auction = (
            session.query(XiuxianAuctionItem)
            .filter(XiuxianAuctionItem.id == int(auction_id))
            .with_for_update()
            .first()
        )
        if auction is None:
            return None
        if str(auction.status or "") != "active":
            return {
                "result": "noop",
                "auction": serialize_auction_item(auction),
                "winner_tg": int(auction.winner_tg or 0) or None,
                "winner_display_name": str(auction.winner_display_name or ""),
                "seller_tg": int(auction.owner_tg or 0) or None,
            }
        if not force and auction.end_at > utcnow():
            raise ValueError("拍卖尚未结束")
        payload = _settle_auction_row(session, auction)
        session.commit()
        return payload


def cancel_auction_item(auction_id: int, *, owner_tg: int | None = None) -> dict[str, Any] | None:
    with Session() as session:
        auction = (
            session.query(XiuxianAuctionItem)
            .filter(XiuxianAuctionItem.id == int(auction_id))
            .with_for_update()
            .first()
        )
        if auction is None:
            return None
        if owner_tg is not None and int(auction.owner_tg or 0) != int(owner_tg):
            raise ValueError("你无权取消这场拍卖")
        if str(auction.status or "") != "active":
            return {
                "result": "noop",
                "auction": serialize_auction_item(auction),
            }

        now = utcnow()
        current_price = max(int(auction.current_price_stone or 0), 0)
        current_bidder_tg = int(auction.highest_bidder_tg or 0)
        if current_bidder_tg > 0 and current_price > 0:
            bidder = (
                session.query(XiuxianProfile)
                .filter(XiuxianProfile.tg == current_bidder_tg)
                .with_for_update()
                .first()
            )
            if bidder is not None:
                apply_spiritual_stone_delta(
                    session,
                    current_bidder_tg,
                    current_price,
                    action_text="拍卖撤销返还灵石",
                    allow_dead=True,
                    apply_tribute=False,
                )

        _grant_auction_item_to_inventory(
            session,
            tg=int(auction.owner_tg),
            item_kind=str(auction.item_kind or ""),
            item_ref_id=int(auction.item_ref_id),
            quantity=int(auction.quantity or 0),
        )

        auction.status = "cancelled"
        auction.updated_at = now
        auction.completed_at = now
        auction.final_price_stone = 0
        auction.seller_income_stone = 0
        auction.fee_amount_stone = 0
        auction.winner_tg = None
        auction.winner_display_name = None

        session.commit()
        return {
            "result": "cancelled",
            "auction": serialize_auction_item(auction),
            "refunded_bidder_tg": current_bidder_tg or None,
        }


def place_auction_bid(
    auction_id: int,
    *,
    bidder_tg: int,
    bidder_display_name: str = "",
    use_buyout: bool = False,
) -> dict[str, Any]:
    with Session() as session:
        auction = (
            session.query(XiuxianAuctionItem)
            .filter(XiuxianAuctionItem.id == int(auction_id))
            .with_for_update()
            .first()
        )
        if auction is None:
            raise ValueError("拍卖不存在")
        if str(auction.status or "") != "active":
            raise ValueError("拍卖已经结束")
        if auction.end_at <= utcnow():
            raise ValueError("拍卖已经结束")
        if int(auction.owner_tg or 0) == int(bidder_tg):
            raise ValueError("不能给自己发起的拍卖加价")

        current_bidder_tg = int(auction.highest_bidder_tg or 0)
        current_price = max(int(auction.current_price_stone or 0), 0)
        buyout_price = max(int(auction.buyout_price_stone or 0), 0)
        next_price = _auction_next_bid_price(auction)
        is_buyout = bool(use_buyout)
        if is_buyout:
            if buyout_price <= 0:
                raise ValueError("这场拍卖没有设置一口价")
            next_price = buyout_price
        elif buyout_price > 0 and next_price >= buyout_price:
            next_price = buyout_price
            is_buyout = True

        bidder = (
            session.query(XiuxianProfile)
            .filter(XiuxianProfile.tg == int(bidder_tg))
            .with_for_update()
            .first()
        )
        if bidder is None or not bidder.consented:
            raise ValueError("你还没有踏入仙途")

        now = utcnow()
        bidder_name = str(bidder_display_name or "").strip()
        bid_action = "buyout" if is_buyout else "bid"

        if current_bidder_tg == int(bidder_tg):
            if not is_buyout:
                raise ValueError("你已经是当前领先者，无需重复加价")
            additional_cost = max(next_price - current_price, 0)
            if additional_cost <= 0:
                raise ValueError("当前价格已经达到一口价")
            if get_shared_spiritual_stone_total(int(bidder_tg), session=session, for_update=True) < additional_cost:
                raise ValueError("灵石不足，无法完成一口价")
            apply_spiritual_stone_delta(
                session,
                int(bidder_tg),
                -additional_cost,
                action_text="拍卖一口价补差",
                allow_dead=False,
                apply_tribute=False,
            )
        else:
            if get_shared_spiritual_stone_total(int(bidder_tg), session=session, for_update=True) < next_price:
                raise ValueError("灵石不足，无法完成出价")
            apply_spiritual_stone_delta(
                session,
                int(bidder_tg),
                -next_price,
                action_text="拍卖出价",
                allow_dead=False,
                apply_tribute=False,
            )
            if current_bidder_tg > 0 and current_price > 0:
                previous_bidder = (
                    session.query(XiuxianProfile)
                    .filter(XiuxianProfile.tg == current_bidder_tg)
                    .with_for_update()
                    .first()
                )
                if previous_bidder is not None:
                    apply_spiritual_stone_delta(
                        session,
                        current_bidder_tg,
                        current_price,
                        action_text="拍卖退还出价",
                        allow_dead=True,
                        apply_tribute=False,
                    )

        auction.current_price_stone = next_price
        auction.highest_bidder_tg = int(bidder_tg)
        auction.highest_bidder_display_name = bidder_name or auction.highest_bidder_display_name
        auction.bid_count = max(int(auction.bid_count or 0), 0) + 1
        auction.updated_at = now

        session.add(
            XiuxianAuctionBid(
                auction_id=int(auction.id),
                bidder_tg=int(bidder_tg),
                bidder_display_name=bidder_name or None,
                bid_amount_stone=next_price,
                action_type=bid_action,
            )
        )

        if is_buyout:
            payload = _settle_auction_row(session, auction)
            session.commit()
            return payload

        session.commit()
        return {
            "result": "bid",
            "auction": serialize_auction_item(auction),
            "winner_tg": None,
            "winner_display_name": None,
            "seller_tg": int(auction.owner_tg or 0) or None,
        }


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

        base_total_cost = item.price_stone * amount
        charisma_discount_percent = 0
        discount_amount = 0
        if item.owner_tg is None:
            charisma_discount_percent = min(max(int(buyer.charisma or 0) - 10, 0) // 4, 20)
            discount_amount = base_total_cost * charisma_discount_percent // 100
        total_cost = max(base_total_cost - discount_amount, 0)
        if get_shared_spiritual_stone_total(int(buyer_tg), session=session, for_update=True) < total_cost:
            raise ValueError("灵石不足")

        apply_spiritual_stone_delta(
            session,
            int(buyer_tg),
            -total_cost,
            action_text="购买商品",
            allow_dead=False,
            apply_tribute=False,
        )

        seller = None
        if item.owner_tg is not None:
            seller = (
                session.query(XiuxianProfile)
                .filter(XiuxianProfile.tg == item.owner_tg)
                .with_for_update()
                .first()
            )
            if seller is not None:
                apply_spiritual_stone_delta(
                    session,
                    int(item.owner_tg),
                    total_cost,
                    action_text="商品售出入账",
                    allow_dead=True,
                    apply_tribute=False,
                )

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
        buyer_balance = get_shared_spiritual_stone_total(int(buyer_tg), session=session, for_update=False)
        seller_balance = None if seller is None else get_shared_spiritual_stone_total(int(item.owner_tg), session=session, for_update=False)
        session.commit()

    name_map = get_emby_name_map([buyer_tg] + ([seller_tg] if seller_tg else []))
    return {
        "item": serialized_item,
        "buyer_balance": buyer_balance,
        "seller_balance": seller_balance,
        "total_cost": total_cost,
        "base_total_cost": base_total_cost,
        "discount_amount": discount_amount,
        "discount_percent": charisma_discount_percent,
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
    include_secluded: bool = True,
) -> dict[str, Any]:
    page = max(int(page or 1), 1)
    page_size = max(min(int(page_size or 20), 50), 1)
    offset = (page - 1) * page_size
    with Session() as session:
        q = session.query(XiuxianProfile).outerjoin(Emby, Emby.tg == XiuxianProfile.tg).filter(XiuxianProfile.consented.is_(True))
        if not include_secluded:
            q = q.filter(or_(XiuxianProfile.social_mode.is_(None), XiuxianProfile.social_mode != "secluded"))
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
ADMIN_INTEGER_PROFILE_FIELDS = ADMIN_EDITABLE_PROFILE_FIELDS - ADMIN_NULLABLE_STRING_FIELDS - {"realm_stage"}
ADMIN_NONNEGATIVE_PROFILE_FIELDS = {
    "spiritual_stone",
    "cultivation",
    "realm_layer",
    "bone",
    "comprehension",
    "divine_sense",
    "fortune",
    "willpower",
    "charisma",
    "karma",
    "qi_blood",
    "true_yuan",
    "body_movement",
    "attack_power",
    "defense_power",
    "insight_bonus",
    "sect_contribution",
    "technique_capacity",
    "root_quality_level",
}


def admin_patch_profile(tg: int, **fields) -> dict[str, Any] | None:
    safe = {k: v for k, v in fields.items() if k in ADMIN_EDITABLE_PROFILE_FIELDS}
    if not safe:
        raise ValueError("没有可更新的字段")
    for key in ADMIN_INTEGER_PROFILE_FIELDS:
        if key in safe:
            safe[key] = _coerce_int(safe.get(key), 0)
    if "realm_stage" in safe:
        safe["realm_stage"] = normalize_realm_stage(safe.get("realm_stage"))
    if "realm_layer" in safe:
        safe["realm_layer"] = normalize_realm_layer(safe.get("realm_layer"), 1)
    if "technique_capacity" in safe:
        safe["technique_capacity"] = max(_coerce_int(safe.get("technique_capacity"), 3), 1)
    for key in ADMIN_NONNEGATIVE_PROFILE_FIELDS:
        if key in safe:
            safe[key] = max(_coerce_int(safe.get(key), 0), 0)
    if "dan_poison" in safe:
        safe["dan_poison"] = max(min(_coerce_int(safe.get("dan_poison"), 0), 100), 0)
    for key in ADMIN_NULLABLE_STRING_FIELDS:
        if key in safe:
            safe[key] = None if safe[key] is None else (str(safe[key]).strip() or None)
    with Session() as session:
        profile = session.query(XiuxianProfile).filter(XiuxianProfile.tg == tg).first()
        if profile is None or not profile.consented:
            return None
        target_stage = safe.get("realm_stage", profile.realm_stage)
        target_layer = safe.get("realm_layer", profile.realm_layer)
        if {"cultivation", "realm_stage", "realm_layer"}.intersection(safe):
            cultivation = safe.get("cultivation", profile.cultivation)
            safe["cultivation"] = min(
                max(_coerce_int(cultivation, 0), 0),
                calculate_realm_threshold(target_stage, target_layer),
            )
        for key, value in safe.items():
            setattr(profile, key, value)
        profile.updated_at = utcnow()
        session.commit()
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


def _normalize_material_fields(fields: dict[str, Any]) -> dict[str, Any]:
    payload = {
        "name": str(fields.get("name") or "").strip(),
        "quality_level": normalize_quality_level(fields.get("quality_level")),
        "image_url": str(fields.get("image_url") or "").strip(),
        "description": str(fields.get("description") or "").strip(),
        "can_plant": _coerce_bool(fields.get("can_plant"), False),
        "seed_price_stone": max(int(fields.get("seed_price_stone") or 0), 0),
        "growth_minutes": max(int(fields.get("growth_minutes") or 0), 0),
        "yield_min": max(int(fields.get("yield_min") or 0), 0),
        "yield_max": max(int(fields.get("yield_max") or 0), 0),
        "unlock_realm_stage": normalize_realm_stage(fields.get("unlock_realm_stage")) if fields.get("unlock_realm_stage") else None,
        "unlock_realm_layer": max(int(fields.get("unlock_realm_layer") or 1), 1),
        "enabled": _coerce_bool(fields.get("enabled"), True),
    }
    if not payload["can_plant"]:
        payload["seed_price_stone"] = 0
        payload["growth_minutes"] = 0
        payload["yield_min"] = 0
        payload["yield_max"] = 0
        payload["unlock_realm_stage"] = None
        payload["unlock_realm_layer"] = 1
    else:
        payload["growth_minutes"] = max(payload["growth_minutes"], 1)
        payload["yield_min"] = max(payload["yield_min"], 1)
        payload["yield_max"] = max(payload["yield_max"], payload["yield_min"])
    if not payload["name"]:
        raise ValueError("material name is required")
    return payload


def list_materials(enabled_only: bool = False) -> list[dict[str, Any]]:
    with Session() as session:
        query = session.query(XiuxianMaterial)
        if enabled_only:
            query = query.filter(XiuxianMaterial.enabled.is_(True))
        rows = [serialize_material(row) for row in query.order_by(XiuxianMaterial.id.desc()).all()]
        return sorted(rows, key=lambda item: _named_quality_sort_key(item or {}, "quality_level"))


def list_plantable_materials(enabled_only: bool = True) -> list[dict[str, Any]]:
    return [
        row
        for row in list_materials(enabled_only=enabled_only)
        if bool((row or {}).get("can_plant"))
    ]


def create_material(**fields) -> dict[str, Any]:
    fields = _normalize_material_fields(dict(fields))
    with Session() as session:
        material = XiuxianMaterial(**fields)
        session.add(material)
        session.commit()
        session.refresh(material)
        return serialize_material(material)


def sync_material_by_name(**fields) -> dict[str, Any]:
    payload = _normalize_material_fields(dict(fields))
    return _sync_named_entity(XiuxianMaterial, serialize_material, payload)


def patch_material(material_id: int, **fields) -> dict[str, Any] | None:
    patch = dict(fields)
    with Session() as session:
        row = session.query(XiuxianMaterial).filter(XiuxianMaterial.id == material_id).first()
        if row is None:
            return None
        current = serialize_material(row) or {}
        current.update(patch)
        payload = _normalize_material_fields(current)
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
        owner_tgs = _shared_inventory_owner_tgs(session, tg)
        if not owner_tgs:
            return []
        rows = (
            session.query(XiuxianMaterialInventory, XiuxianMaterial)
            .join(XiuxianMaterial, XiuxianMaterial.id == XiuxianMaterialInventory.material_id)
            .filter(XiuxianMaterialInventory.tg.in_(owner_tgs))
            .order_by(XiuxianMaterial.id.desc())
            .all()
        )
        payload_map: dict[int, dict[str, Any]] = {}
        for inventory, material in rows:
            material_id = int(inventory.material_id or 0)
            entry = payload_map.get(material_id)
            if entry is None:
                entry = {"quantity": 0, "material": serialize_material(material)}
                payload_map[material_id] = entry
            entry["quantity"] += max(int(inventory.quantity or 0), 0)
        payload = list(payload_map.values())
        return sorted(
            payload,
            key=lambda row: _named_quality_sort_key((row.get("material") or {}), "quality_level"),
        )


def consume_user_materials(tg: int, material_id: int, quantity: int = 1) -> bool:
    with Session() as session:
        remaining = max(int(quantity or 0), 1)
        rows = _ordered_owner_rows(session, XiuxianMaterialInventory, tg, "material_id", material_id)
        total_quantity = sum(max(int(row.quantity or 0), 0) for row in rows)
        if total_quantity < remaining:
            return False
        now = utcnow()
        for row in rows:
            if remaining <= 0:
                break
            available = max(int(row.quantity or 0), 0)
            if available <= 0:
                continue
            delta = min(available, remaining)
            row.quantity = available - delta
            row.updated_at = now
            remaining -= delta
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
    # 历史版本的奇遇额外词条奖励已经退场，保留字段只做兼容，不再对外开放。
    payload["reward_willpower"] = 0
    payload["reward_charisma"] = 0
    payload["reward_karma"] = 0
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


def _has_journal_action_in_session(session: Session, tg: int, action_type: str) -> bool:
    row = (
        session.query(XiuxianJournal.id)
        .filter(
            XiuxianJournal.tg == int(tg),
            XiuxianJournal.action_type == str(action_type or "").strip(),
        )
        .first()
    )
    return row is not None


def _starter_artifact_id_in_session(session: Session) -> int | None:
    row = session.query(XiuxianArtifact.id).filter(XiuxianArtifact.name == STARTER_ARTIFACT_NAME).first()
    return int(row[0]) if row else None


def _starter_artifact_protection_active_in_session(session: Session, tg: int) -> bool:
    return _has_journal_action_in_session(session, tg, STARTER_ARTIFACT_GRANTED_ACTION) and not _has_journal_action_in_session(
        session,
        tg,
        STARTER_ARTIFACT_RELEASED_ACTION,
    )


def has_starter_artifact_claim_record(tg: int) -> bool:
    with Session() as session:
        return _has_journal_action_in_session(session, tg, STARTER_ARTIFACT_GRANTED_ACTION)


def starter_artifact_protection_active(tg: int) -> bool:
    with Session() as session:
        return _starter_artifact_protection_active_in_session(session, tg)


def grant_starter_artifact_once(tg: int, artifact_id: int) -> dict[str, Any]:
    with Session() as session:
        artifact = session.query(XiuxianArtifact).filter(XiuxianArtifact.id == int(artifact_id)).first()
        if artifact is None:
            raise ValueError("artifact not found")
        if _has_journal_action_in_session(session, tg, STARTER_ARTIFACT_GRANTED_ACTION):
            row = (
                session.query(XiuxianArtifactInventory)
                .filter(
                    XiuxianArtifactInventory.tg == int(tg),
                    XiuxianArtifactInventory.artifact_id == int(artifact_id),
                )
                .first()
            )
            return {
                "artifact": serialize_artifact(artifact),
                "quantity": max(int((row.quantity if row is not None else 0) or 0), 0),
                "bound_quantity": max(int((row.bound_quantity if row is not None else 0) or 0), 0),
                "granted": False,
            }
        row = (
            session.query(XiuxianArtifactInventory)
            .filter(
                XiuxianArtifactInventory.tg == int(tg),
                XiuxianArtifactInventory.artifact_id == int(artifact_id),
            )
            .with_for_update()
            .first()
        )
        if row is None:
            row = XiuxianArtifactInventory(tg=int(tg), artifact_id=int(artifact_id), quantity=0, bound_quantity=0)
            session.add(row)
        row.quantity = max(int(row.quantity or 0), 0) + 1
        row.bound_quantity = max(min(int(row.bound_quantity or 0), int(row.quantity or 0)), 0)
        row.updated_at = utcnow()
        session.add(
            XiuxianJournal(
                tg=int(tg),
                action_type=STARTER_ARTIFACT_GRANTED_ACTION,
                title="获赠新手法宝",
                detail="入道时获赠【凡铁剑】。此宝默认不会因击杀掠夺失去；若你将其用于上架出售或拍卖，则保护失效，且日后重修不会再次补发。",
            )
        )
        session.commit()
        return {
            "artifact": serialize_artifact(artifact),
            "quantity": max(int(row.quantity or 0), 0),
            "bound_quantity": max(int(row.bound_quantity or 0), 0),
            "granted": True,
        }


def release_starter_artifact_protection(tg: int, *, reason: str = "") -> bool:
    with Session() as session:
        if not _starter_artifact_protection_active_in_session(session, tg):
            return False
        session.add(
            XiuxianJournal(
                tg=int(tg),
                action_type=STARTER_ARTIFACT_RELEASED_ACTION,
                title="新手法宝保护失效",
                detail=(reason or "你已将新手法宝用于交易，它不再具备新手保护。").strip() or None,
            )
        )
        session.commit()
        return True


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


def _prune_error_logs(session, keep_count: int) -> None:
    keep = max(int(keep_count or 0), 1)
    stale_rows = (
        session.query(XiuxianErrorLog)
        .order_by(XiuxianErrorLog.id.desc())
        .offset(keep)
        .all()
    )
    for row in stale_rows:
        session.delete(row)


def create_error_log(
    *,
    tg: int | None = None,
    username: str | None = None,
    display_name: str | None = None,
    scope: str = "user",
    level: str = "ERROR",
    operation: str | None = None,
    method: str | None = None,
    path: str | None = None,
    status_code: int | None = None,
    message: str,
    detail: str | None = None,
) -> dict[str, Any]:
    settings = get_xiuxian_settings()
    retention = max(int(settings.get("error_log_retention_count", DEFAULT_SETTINGS["error_log_retention_count"]) or 0), 1)
    with Session() as session:
        row = XiuxianErrorLog(
            tg=tg,
            username=str(username or "").strip() or None,
            display_name=str(display_name or "").strip() or None,
            scope=str(scope or "user").strip() or "user",
            level=str(level or "ERROR").strip().upper() or "ERROR",
            operation=str(operation or "").strip() or None,
            method=str(method or "").strip().upper() or None,
            path=str(path or "").strip() or None,
            status_code=int(status_code) if status_code is not None else None,
            message=str(message or "unknown error").strip() or "unknown error",
            detail=str(detail or "").strip() or None,
        )
        session.add(row)
        session.flush()
        payload = serialize_error_log(row)
        _prune_error_logs(session, retention)
        session.commit()
        return payload


def list_error_logs(
    *,
    limit: int = 100,
    tg: int | None = None,
    level: str | None = None,
    keyword: str | None = None,
) -> list[dict[str, Any]]:
    with Session() as session:
        query = session.query(XiuxianErrorLog)
        if tg is not None:
            query = query.filter(XiuxianErrorLog.tg == int(tg))
        if level:
            query = query.filter(XiuxianErrorLog.level == str(level).strip().upper())
        if keyword:
            pattern = f"%{str(keyword).strip()}%"
            query = query.filter(
                or_(
                    XiuxianErrorLog.message.like(pattern),
                    XiuxianErrorLog.detail.like(pattern),
                    XiuxianErrorLog.operation.like(pattern),
                    XiuxianErrorLog.path.like(pattern),
                    XiuxianErrorLog.display_name.like(pattern),
                    XiuxianErrorLog.username.like(pattern),
                )
            )
        rows = query.order_by(XiuxianErrorLog.id.desc()).limit(max(int(limit or 0), 1)).all()
        return [serialize_error_log(row) for row in rows]


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

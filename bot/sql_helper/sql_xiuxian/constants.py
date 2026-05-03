"""修仙插件 ORM 模型与数据库读写封装。

定义表结构、序列化器，以及后台和玩法层会直接调用的增删改查函数。
"""

from __future__ import annotations

import copy
import random
import re
from datetime import datetime, timedelta, timezone
from typing import Any, Iterable

from sqlalchemy import event
from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    BigInteger,
    String,
    Text,
    UniqueConstraint,
    or_,
)
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session as OrmSession

from bot.plugins.xiuxian_game import cache as xiuxian_cache
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
DEFAULT_TECHNIQUE_CAPACITY = 2
MAX_TECHNIQUE_CAPACITY = 2
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
REALM_LAYER_THRESHOLD_GROWTH_RATE = 0.05
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
ARTIFACT_EQUIP_CATEGORY_LABELS = {
    "weapon": "武器",
    "armor": "防具",
    "accessory": "饰品",
    "other": "其他装备",
}
ARTIFACT_SLOT_CATEGORY_MAP = {
    "weapon": "weapon",
    "chest": "armor",
    "legs": "armor",
    "boots": "armor",
    "helmet": "armor",
    "bracelet": "armor",
    "necklace": "accessory",
    "ring": "accessory",
}
SECT_CAMP_LABELS = {
    "orthodox": "正道",
    "heterodox": "邪道",
}
PILL_TYPE_LABELS = {
    "foundation": "突破加成",
    "clear_poison": "解毒",
    "cultivation": "提升修为",
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
    "metric": "计数任务",
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
    "废灵根": {"cultivation_rate": 0.72, "breakthrough_bonus": -8, "combat_factor": 0.97},
    "下品灵根": {"cultivation_rate": 0.88, "breakthrough_bonus": -3, "combat_factor": 0.985},
    "中品灵根": {"cultivation_rate": 1.0, "breakthrough_bonus": 0, "combat_factor": 1.0},
    "上品灵根": {"cultivation_rate": 1.12, "breakthrough_bonus": 3, "combat_factor": 1.015},
    "极品灵根": {"cultivation_rate": 1.24, "breakthrough_bonus": 6, "combat_factor": 1.03},
    "天灵根": {"cultivation_rate": 1.38, "breakthrough_bonus": 12, "combat_factor": 1.045},
    "变异灵根": {"cultivation_rate": 1.3, "breakthrough_bonus": 9, "combat_factor": 1.04},
}
DEFAULT_EXPLORATION_DROP_WEIGHT_RULES = {
    "material_divine_sense_divisor": 7,
    "high_quality_threshold": 4,
    "high_quality_fortune_divisor": 8,
    "high_quality_root_level_start": 4,
}
DEFAULT_ITEM_QUALITY_VALUE_RULES = {
    "凡品": {"artifact_multiplier": 0.70, "pill_multiplier": 0.70, "talisman_multiplier": 0.65, "recipe_multiplier": 0.70},
    "下品": {"artifact_multiplier": 0.90, "pill_multiplier": 0.90, "talisman_multiplier": 0.85, "recipe_multiplier": 0.90},
    "中品": {"artifact_multiplier": 1.20, "pill_multiplier": 1.20, "talisman_multiplier": 1.15, "recipe_multiplier": 1.20},
    "上品": {"artifact_multiplier": 1.60, "pill_multiplier": 1.60, "talisman_multiplier": 1.55, "recipe_multiplier": 1.60},
    "极品": {"artifact_multiplier": 2.20, "pill_multiplier": 2.20, "talisman_multiplier": 2.10, "recipe_multiplier": 2.20},
    "仙品": {"artifact_multiplier": 3.10, "pill_multiplier": 3.10, "talisman_multiplier": 2.95, "recipe_multiplier": 3.10},
    "先天至宝": {"artifact_multiplier": 4.50, "pill_multiplier": 4.50, "talisman_multiplier": 4.25, "recipe_multiplier": 4.50},
}
DEFAULT_ACTIVITY_STAT_GROWTH_RULES = {
    "practice": {"chance_percent": 16, "gain_min": 1, "gain_max": 2, "attribute_count": 1},
    "commission": {"chance_percent": 18, "gain_min": 1, "gain_max": 2, "attribute_count": 1},
    "exploration": {"chance_percent": 26, "gain_min": 1, "gain_max": 3, "attribute_count": 1},
    "duel": {"chance_percent": 20, "gain_min": 1, "gain_max": 2, "attribute_count": 2},
}
DEFAULT_GAMBLING_QUALITY_WEIGHT_RULES = {
    "凡品": {"weight_multiplier": 1.0},
    "下品": {"weight_multiplier": 0.55},
    "中品": {"weight_multiplier": 0.28},
    "上品": {"weight_multiplier": 0.12},
    "极品": {"weight_multiplier": 0.045},
    "仙品": {"weight_multiplier": 0.014},
    "先天至宝": {"weight_multiplier": 0.004},
}
DEFAULT_FISHING_QUALITY_WEIGHT_RULES = {
    "凡品": {"weight_multiplier": 1.0},
    "下品": {"weight_multiplier": 0.42},
    "中品": {"weight_multiplier": 0.18},
    "上品": {"weight_multiplier": 0.065},
    "极品": {"weight_multiplier": 0.020},
    "仙品": {"weight_multiplier": 0.0055},
    "先天至宝": {"weight_multiplier": 0.0012},
}



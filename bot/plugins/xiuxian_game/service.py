from __future__ import annotations

import random
from datetime import timedelta
from math import ceil
from typing import Any

from pykeyboard import InlineButton, InlineKeyboard
from pyromod.helpers import ikb

from bot import api as api_config
from bot.func_helper.emby_currency import (
    convert_coin_to_stone,
    convert_stone_to_coin,
    get_emby_balance,
    get_exchange_settings,
)
from bot.sql_helper.sql_xiuxian import (
    DEFAULT_SETTINGS,
    ELEMENT_CONTROLS,
    ELEMENT_GENERATES,
    FIVE_ELEMENTS,
    ITEM_KIND_LABELS,
    PILL_TYPE_LABELS,
    REALM_ORDER,
    ROOT_QUALITY_COLORS,
    ROOT_QUALITY_LEVELS,
    ROOT_VARIANT_ELEMENTS,
    admin_patch_profile,
    create_journal,
    create_artifact,
    create_duel_record,
    create_pill,
    create_shop_item,
    create_technique,
    create_talisman,
    get_artifact,
    get_emby_name_map,
    get_pill,
    get_profile,
    get_technique,
    get_talisman,
    get_xiuxian_settings,
    grant_artifact_to_user,
    grant_material_to_user,
    grant_pill_to_user,
    grant_talisman_to_user,
    list_artifacts,
    list_equipped_artifacts,
    list_pills,
    list_profiles,
    list_shop_items,
    list_techniques,
    list_talismans,
    list_user_artifacts,
    list_user_pills,
    list_user_talismans,
    normalize_realm_stage,
    purchase_shop_item as sql_purchase_shop_item,
    realm_index,
    search_profiles,
    serialize_artifact,
    serialize_pill,
    serialize_profile,
    serialize_technique,
    serialize_talisman,
    set_current_technique,
    set_active_talisman,
    set_equipped_artifact,
    set_xiuxian_settings,
    update_shop_item,
    upsert_profile,
    use_user_artifact_listing_stock,
    use_user_pill_listing_stock,
    use_user_talisman_listing_stock,
    consume_user_pill,
    consume_user_talisman,
    utcnow,
)
from bot.plugins.xiuxian_game.world_service import get_sect_effects


ROOT_SPECIAL_BONUS = {
    "天灵根": 15,
    "地灵根": 10,
}

PERSONAL_SHOP_NAME = "游仙小铺"

DEFAULT_ARTIFACTS = [
    {
        "name": "凡铁剑",
        "rarity": "凡品",
        "artifact_type": "battle",
        "description": "最基础的入门法宝，适合刚踏入仙途的道友防身。",
        "attack_bonus": 12,
        "defense_bonus": 6,
        "duel_rate_bonus": 2,
        "cultivation_bonus": 0,
        "image_url": "",
        "enabled": True,
    }
]

DEFAULT_PILLS = [
    {
        "name": "筑基丹",
        "pill_type": "foundation",
        "description": "筑基突破时使用，提高本次突破成功率。",
        "effect_value": 50,
        "poison_delta": 12,
        "image_url": "",
        "enabled": True,
    },
    {
        "name": "清心丹",
        "pill_type": "clear_poison",
        "description": "化解丹毒，服用后可降低 50 点丹毒。",
        "effect_value": 50,
        "poison_delta": 0,
        "image_url": "",
        "enabled": True,
    },
]

DEFAULT_TALISMANS = [
    {
        "name": "疾风符",
        "rarity": "凡品",
        "description": "在下一场斗法中提高先机与攻击，增强胜率。",
        "attack_bonus": 6,
        "duel_rate_bonus": 4,
        "image_url": "",
        "enabled": True,
    }
]

DEFAULT_TECHNIQUES = [
    {
        "name": "长青诀",
        "rarity": "凡品",
        "technique_type": "cultivation",
        "description": "循序吐纳、温养经脉的入门功法，适合刚踏入仙途的修士稳扎稳打。",
        "comprehension_bonus": 2,
        "true_yuan_bonus": 18,
        "cultivation_bonus": 8,
        "breakthrough_bonus": 4,
        "min_realm_stage": "炼气",
        "min_realm_layer": 1,
        "enabled": True,
    },
    {
        "name": "金刚伏魔功",
        "rarity": "下品",
        "technique_type": "combat",
        "description": "以气血催动筋骨，重攻重势，适合偏战斗路线的修士。",
        "attack_bonus": 10,
        "defense_bonus": 6,
        "qi_blood_bonus": 36,
        "duel_rate_bonus": 5,
        "min_realm_stage": "筑基",
        "min_realm_layer": 1,
        "enabled": True,
    },
    {
        "name": "太虚凝神篇",
        "rarity": "下品",
        "technique_type": "balanced",
        "description": "偏重神识与悟性，可兼顾突破与斗法，是中前期泛用功法。",
        "comprehension_bonus": 4,
        "divine_sense_bonus": 5,
        "attack_bonus": 4,
        "defense_bonus": 4,
        "breakthrough_bonus": 6,
        "min_realm_stage": "筑基",
        "min_realm_layer": 3,
        "enabled": True,
    },
]

BREAKTHROUGH_BASE_RATE = {
    "炼气": 45,
    "筑基": 38,
    "结丹": 32,
    "元婴": 26,
    "化神": 21,
    "须弥": 17,
    "芥子": 13,
    "混元一体": 0,
}
ROOT_QUALITY_ROLLS = [
    ("天灵根", 1),
    ("变异灵根", 1),
    ("极品灵根", 10),
    ("上品灵根", 20),
    ("中品灵根", 32),
    ("下品灵根", 28),
    ("废灵根", 8),
]
ITEM_STAT_FIELDS = (
    "attack_bonus",
    "defense_bonus",
    "bone_bonus",
    "comprehension_bonus",
    "divine_sense_bonus",
    "fortune_bonus",
    "qi_blood_bonus",
    "true_yuan_bonus",
    "body_movement_bonus",
    "duel_rate_bonus",
    "cultivation_bonus",
)


def _coerce_float(value: Any, default: float, minimum: float | None = None) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError):
        result = float(default)
    if minimum is not None:
        result = max(result, minimum)
    return round(result, 4)


def _coerce_int(value: Any, default: int, minimum: int | None = None) -> int:
    try:
        result = int(value)
    except (TypeError, ValueError):
        result = int(default)
    if minimum is not None:
        result = max(result, minimum)
    return result


def _normalize_root_quality_value_rules(raw: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    defaults = DEFAULT_SETTINGS["root_quality_value_rules"]
    rules = {}
    raw = raw if isinstance(raw, dict) else {}
    for name, level in ROOT_QUALITY_LEVELS.items():
        default_rule = defaults.get(name, {})
        source = raw.get(name) if isinstance(raw.get(name), dict) else {}
        rules[name] = {
            "level": level,
            "cultivation_rate": _coerce_float(source.get("cultivation_rate"), default_rule.get("cultivation_rate", 1.0), 0.1),
            "breakthrough_bonus": _coerce_int(source.get("breakthrough_bonus"), default_rule.get("breakthrough_bonus", 0)),
            "combat_factor": _coerce_float(source.get("combat_factor"), default_rule.get("combat_factor", 1.0), 0.1),
            "color": ROOT_QUALITY_COLORS[name],
        }
    return rules


def _normalize_item_quality_value_rules(raw: dict[str, Any] | None) -> dict[str, dict[str, float]]:
    defaults = DEFAULT_SETTINGS["item_quality_value_rules"]
    rules = {}
    raw = raw if isinstance(raw, dict) else {}
    for name, default_rule in defaults.items():
        source = raw.get(name) if isinstance(raw.get(name), dict) else {}
        rules[name] = {
            "artifact_multiplier": _coerce_float(source.get("artifact_multiplier"), default_rule.get("artifact_multiplier", 1.0), 0.0),
            "pill_multiplier": _coerce_float(source.get("pill_multiplier"), default_rule.get("pill_multiplier", 1.0), 0.0),
            "talisman_multiplier": _coerce_float(source.get("talisman_multiplier"), default_rule.get("talisman_multiplier", 1.0), 0.0),
        }
    return rules


def _item_quality_multiplier(item: dict[str, Any] | None, item_kind: str) -> float:
    field_map = {
        "artifact": "artifact_multiplier",
        "pill": "pill_multiplier",
        "talisman": "talisman_multiplier",
    }
    rules = _normalize_item_quality_value_rules(
        get_xiuxian_settings().get("item_quality_value_rules", DEFAULT_SETTINGS["item_quality_value_rules"])
    )
    rarity = str((item or {}).get("rarity") or "凡品").strip() or "凡品"
    fallback = rules.get("凡品", DEFAULT_SETTINGS["item_quality_value_rules"]["凡品"])
    current = rules.get(rarity, fallback)
    value = current.get(field_map[item_kind], 1.0)
    return float(1.0 if value is None else value)


def _root_quality_payload(name: str | None) -> dict[str, Any]:
    rules = _normalize_root_quality_value_rules(
        get_xiuxian_settings().get("root_quality_value_rules", DEFAULT_SETTINGS["root_quality_value_rules"])
    )
    return rules.get(name or "中品灵根", rules["中品灵根"])


def _normalized_root_quality(profile: dict[str, Any] | None) -> str:
    profile = profile or {}

    raw_quality = str(profile.get("root_quality") or "").strip()
    if raw_quality in ROOT_QUALITY_LEVELS:
        return raw_quality
    if raw_quality == "地灵根":
        return "极品灵根"

    try:
        quality_level = int(profile.get("root_quality_level") or 0)
    except (TypeError, ValueError):
        quality_level = 0
    if quality_level > 0:
        for name, level in ROOT_QUALITY_LEVELS.items():
            if level == quality_level:
                return name

    root_type = str(profile.get("root_type") or "").strip()
    relation = str(profile.get("root_relation") or "").strip()
    try:
        root_bonus = int(profile.get("root_bonus") or 0)
    except (TypeError, ValueError):
        root_bonus = 0

    if root_type == "天灵根" or root_bonus >= ROOT_SPECIAL_BONUS["天灵根"]:
        return "天灵根"
    if root_type == "变异灵根":
        return "变异灵根"
    if root_type == "地灵根" or root_bonus >= ROOT_SPECIAL_BONUS["地灵根"]:
        return "极品灵根"
    if root_type == "双灵根":
        if relation == "相克" or root_bonus < 0:
            return "中品灵根"
        return "上品灵根"
    if root_type == "单灵根":
        return "中品灵根"
    return "中品灵根"


def _roll_root_quality() -> str:
    roll = random.randint(1, 100)
    cursor = 0
    for name, weight in ROOT_QUALITY_ROLLS:
        cursor += weight
        if roll <= cursor:
            return name
    return "中品灵根"


def _profile_root_elements(profile: dict[str, Any]) -> list[str]:
    elements = []
    primary = str(profile.get("root_primary") or "").strip()
    secondary = str(profile.get("root_secondary") or "").strip()
    if primary:
        elements.append(primary)
    if secondary and secondary != primary:
        elements.append(secondary)
    return elements


def _sum_item_stats(*effect_sets: dict[str, Any] | None) -> dict[str, float]:
    totals = {key: 0.0 for key in ITEM_STAT_FIELDS}
    for effects in effect_sets:
        for key in totals:
            totals[key] += float((effects or {}).get(key, 0) or 0)
    return totals


def _build_opening_stats(root_payload: dict[str, Any]) -> dict[str, int]:
    quality = _root_quality_payload(root_payload.get("root_quality"))
    quality_level = int(quality["level"])
    special_bonus = 4 if root_payload.get("root_type") == "天灵根" else 3 if root_payload.get("root_type") == "变异灵根" else 0
    bone = random.randint(10, 18) + quality_level + special_bonus
    comprehension = random.randint(10, 18) + quality_level + (2 if root_payload.get("root_type") in {"天灵根", "变异灵根"} else 0)
    divine_sense = random.randint(9, 17) + quality_level + (2 if root_payload.get("root_primary") in {"水", "雷", "风"} else 0)
    fortune = random.randint(8, 16) + quality_level + (2 if root_payload.get("root_quality") in {"极品灵根", "天灵根", "变异灵根"} else 0)
    body_movement = random.randint(8, 15) + quality_level + (2 if root_payload.get("root_primary") in {"风", "火", "雷"} else 0)
    attack_power = random.randint(10, 18) + quality_level * 2 + (3 if root_payload.get("root_primary") in {"火", "金", "雷"} else 0)
    defense_power = random.randint(10, 18) + quality_level * 2 + (3 if root_payload.get("root_primary") in {"土", "金", "水"} else 0)
    qi_blood = 160 + bone * 12 + defense_power * 4 + quality_level * 20
    true_yuan = 140 + comprehension * 9 + divine_sense * 6 + quality_level * 18
    return {
        "bone": bone,
        "comprehension": comprehension,
        "divine_sense": divine_sense,
        "fortune": fortune,
        "qi_blood": qi_blood,
        "true_yuan": true_yuan,
        "body_movement": body_movement,
        "attack_power": attack_power,
        "defense_power": defense_power,
    }


def _effective_stats(
    profile: dict[str, Any],
    artifact_effects: dict[str, Any] | None = None,
    talisman_effects: dict[str, Any] | None = None,
    sect_effects: dict[str, Any] | None = None,
    technique_effects: dict[str, Any] | None = None,
) -> dict[str, float]:
    totals = _sum_item_stats(artifact_effects, talisman_effects, sect_effects, technique_effects)
    stats = {
        "bone": float(profile.get("bone", 0) or 0) + totals["bone_bonus"],
        "comprehension": float(profile.get("comprehension", 0) or 0) + totals["comprehension_bonus"],
        "divine_sense": float(profile.get("divine_sense", 0) or 0) + totals["divine_sense_bonus"],
        "fortune": float(profile.get("fortune", 0) or 0) + totals["fortune_bonus"],
        "qi_blood": float(profile.get("qi_blood", 0) or 0) + totals["qi_blood_bonus"],
        "true_yuan": float(profile.get("true_yuan", 0) or 0) + totals["true_yuan_bonus"],
        "body_movement": float(profile.get("body_movement", 0) or 0) + totals["body_movement_bonus"],
        "attack_power": float(profile.get("attack_power", 0) or 0) + totals["attack_bonus"],
        "defense_power": float(profile.get("defense_power", 0) or 0) + totals["defense_bonus"],
        "duel_rate_bonus": totals["duel_rate_bonus"],
        "cultivation_bonus": totals["cultivation_bonus"],
    }
    stats["qi_blood"] = max(stats["qi_blood"], 1.0)
    stats["true_yuan"] = max(stats["true_yuan"], 1.0)
    return stats


def resolve_technique_effects(
    profile: dict[str, Any],
    technique: dict[str, Any] | None,
    opponent_profile: dict[str, Any] | None = None,
) -> dict[str, float]:
    if technique is None:
        return {
            "attack_bonus": 0.0,
            "defense_bonus": 0.0,
            "bone_bonus": 0.0,
            "comprehension_bonus": 0.0,
            "divine_sense_bonus": 0.0,
            "fortune_bonus": 0.0,
            "qi_blood_bonus": 0.0,
            "true_yuan_bonus": 0.0,
            "body_movement_bonus": 0.0,
            "duel_rate_bonus": 0.0,
            "cultivation_bonus": 0.0,
            "breakthrough_bonus": 0.0,
        }
    return {
        "attack_bonus": float(technique.get("attack_bonus", 0) or 0),
        "defense_bonus": float(technique.get("defense_bonus", 0) or 0),
        "bone_bonus": float(technique.get("bone_bonus", 0) or 0),
        "comprehension_bonus": float(technique.get("comprehension_bonus", 0) or 0),
        "divine_sense_bonus": float(technique.get("divine_sense_bonus", 0) or 0),
        "fortune_bonus": float(technique.get("fortune_bonus", 0) or 0),
        "qi_blood_bonus": float(technique.get("qi_blood_bonus", 0) or 0),
        "true_yuan_bonus": float(technique.get("true_yuan_bonus", 0) or 0),
        "body_movement_bonus": float(technique.get("body_movement_bonus", 0) or 0),
        "duel_rate_bonus": float(technique.get("duel_rate_bonus", 0) or 0),
        "cultivation_bonus": float(technique.get("cultivation_bonus", 0) or 0),
        "breakthrough_bonus": float(technique.get("breakthrough_bonus", 0) or 0),
    }


def _root_element_duel_modifier(attacker: dict[str, Any], defender: dict[str, Any]) -> float:
    attacker_elements = _profile_root_elements(attacker)
    defender_elements = _profile_root_elements(defender)
    modifier = 0.0
    for own in attacker_elements:
        for rival in defender_elements:
            if ELEMENT_CONTROLS.get(own) == rival:
                modifier += 0.025
            if ELEMENT_CONTROLS.get(rival) == own:
                modifier -= 0.025
            if ELEMENT_GENERATES.get(own) == rival:
                modifier += 0.01
            if ELEMENT_GENERATES.get(rival) == own:
                modifier -= 0.01
    return max(min(modifier, 0.08), -0.08)

def resolve_artifact_effects(
    profile: dict[str, Any],
    artifact: dict[str, Any] | None,
    opponent_profile: dict[str, Any] | None = None,
) -> dict[str, float]:
    if artifact is None:
        return {
            "attack_bonus": 0.0,
            "defense_bonus": 0.0,
            "bone_bonus": 0.0,
            "comprehension_bonus": 0.0,
            "divine_sense_bonus": 0.0,
            "fortune_bonus": 0.0,
            "qi_blood_bonus": 0.0,
            "true_yuan_bonus": 0.0,
            "body_movement_bonus": 0.0,
            "duel_rate_bonus": 0.0,
            "cultivation_bonus": 0.0,
        }
    multiplier = _item_quality_multiplier(artifact, "artifact")
    return {
        "attack_bonus": float(artifact.get("attack_bonus", 0) or 0) * multiplier,
        "defense_bonus": float(artifact.get("defense_bonus", 0) or 0) * multiplier,
        "bone_bonus": float(artifact.get("bone_bonus", 0) or 0) * multiplier,
        "comprehension_bonus": float(artifact.get("comprehension_bonus", 0) or 0) * multiplier,
        "divine_sense_bonus": float(artifact.get("divine_sense_bonus", 0) or 0) * multiplier,
        "fortune_bonus": float(artifact.get("fortune_bonus", 0) or 0) * multiplier,
        "qi_blood_bonus": float(artifact.get("qi_blood_bonus", 0) or 0) * multiplier,
        "true_yuan_bonus": float(artifact.get("true_yuan_bonus", 0) or 0) * multiplier,
        "body_movement_bonus": float(artifact.get("body_movement_bonus", 0) or 0) * multiplier,
        "duel_rate_bonus": float(artifact.get("duel_rate_bonus", 0) or 0) * multiplier,
        "cultivation_bonus": float(artifact.get("cultivation_bonus", 0) or 0) * multiplier,
    }


def resolve_talisman_effects(
    profile: dict[str, Any],
    talisman: dict[str, Any] | None,
    opponent_profile: dict[str, Any] | None = None,
) -> dict[str, float]:
    if talisman is None:
        return {
            "attack_bonus": 0.0,
            "defense_bonus": 0.0,
            "bone_bonus": 0.0,
            "comprehension_bonus": 0.0,
            "divine_sense_bonus": 0.0,
            "fortune_bonus": 0.0,
            "qi_blood_bonus": 0.0,
            "true_yuan_bonus": 0.0,
            "body_movement_bonus": 0.0,
            "duel_rate_bonus": 0.0,
        }
    multiplier = _item_quality_multiplier(talisman, "talisman")
    return {
        "attack_bonus": float(talisman.get("attack_bonus", 0) or 0) * multiplier,
        "defense_bonus": float(talisman.get("defense_bonus", 0) or 0) * multiplier,
        "bone_bonus": float(talisman.get("bone_bonus", 0) or 0) * multiplier,
        "comprehension_bonus": float(talisman.get("comprehension_bonus", 0) or 0) * multiplier,
        "divine_sense_bonus": float(talisman.get("divine_sense_bonus", 0) or 0) * multiplier,
        "fortune_bonus": float(talisman.get("fortune_bonus", 0) or 0) * multiplier,
        "qi_blood_bonus": float(talisman.get("qi_blood_bonus", 0) or 0) * multiplier,
        "true_yuan_bonus": float(talisman.get("true_yuan_bonus", 0) or 0) * multiplier,
        "body_movement_bonus": float(talisman.get("body_movement_bonus", 0) or 0) * multiplier,
        "duel_rate_bonus": float(talisman.get("duel_rate_bonus", 0) or 0) * multiplier,
    }


def resolve_pill_effects(
    profile: dict[str, Any],
    pill: dict[str, Any] | None,
    extra: dict[str, Any] | None = None,
) -> dict[str, float]:
    if pill is None:
        return {
            "effect_value": 0.0,
            "poison_delta": 0.0,
            "success_rate_bonus": 0.0,
            "clear_poison": 0.0,
            "cultivation_gain": 0.0,
            "stone_gain": 0.0,
            "insight_gain": 0.0,
            "attack_bonus": 0.0,
            "defense_bonus": 0.0,
            "bone_bonus": 0.0,
            "comprehension_bonus": 0.0,
            "divine_sense_bonus": 0.0,
            "fortune_bonus": 0.0,
            "qi_blood_bonus": 0.0,
            "true_yuan_bonus": 0.0,
            "body_movement_bonus": 0.0,
        }
    pill_type = pill.get("pill_type")
    multiplier = _item_quality_multiplier(pill, "pill")
    base_effect_value = float(pill.get("effect_value", 0) or 0) * multiplier
    payload = {
        "effect_value": base_effect_value,
        "poison_delta": float(pill.get("poison_delta", 0) or 0),
        "success_rate_bonus": 0.0,
        "clear_poison": base_effect_value if pill_type == "clear_poison" else 0.0,
        "cultivation_gain": base_effect_value if pill_type == "cultivation" else 0.0,
        "stone_gain": base_effect_value if pill_type == "stone" else 0.0,
        "insight_gain": 0.0,
        "attack_bonus": float(pill.get("attack_bonus", 0) or 0) * multiplier,
        "defense_bonus": float(pill.get("defense_bonus", 0) or 0) * multiplier,
        "bone_bonus": float(pill.get("bone_bonus", 0) or 0) * multiplier,
        "comprehension_bonus": float(pill.get("comprehension_bonus", 0) or 0) * multiplier,
        "divine_sense_bonus": float(pill.get("divine_sense_bonus", 0) or 0) * multiplier,
        "fortune_bonus": float(pill.get("fortune_bonus", 0) or 0) * multiplier,
        "qi_blood_bonus": float(pill.get("qi_blood_bonus", 0) or 0) * multiplier,
        "true_yuan_bonus": float(pill.get("true_yuan_bonus", 0) or 0) * multiplier,
        "body_movement_bonus": float(pill.get("body_movement_bonus", 0) or 0) * multiplier,
    }
    if pill_type == "foundation":
        payload["success_rate_bonus"] = base_effect_value
    elif pill_type == "comprehension":
        payload["comprehension_bonus"] += base_effect_value
    elif pill_type == "qi_blood":
        payload["qi_blood_bonus"] += base_effect_value
    elif pill_type == "true_yuan":
        payload["true_yuan_bonus"] += base_effect_value
    elif pill_type == "body_movement":
        payload["body_movement_bonus"] += base_effect_value
    elif pill_type == "attack":
        payload["attack_bonus"] += base_effect_value
    elif pill_type == "defense":
        payload["defense_bonus"] += base_effect_value
    return payload


def collect_equipped_artifacts(tg: int) -> list[dict[str, Any]]:
    return [row["artifact"] for row in list_equipped_artifacts(tg)]


def merge_artifact_effects(
    profile: dict[str, Any],
    equipped_artifacts: list[dict[str, Any]] | None,
    opponent_profile: dict[str, Any] | None = None,
) -> dict[str, float]:
    totals = {
        "attack_bonus": 0.0,
        "defense_bonus": 0.0,
        "bone_bonus": 0.0,
        "comprehension_bonus": 0.0,
        "divine_sense_bonus": 0.0,
        "fortune_bonus": 0.0,
        "qi_blood_bonus": 0.0,
        "true_yuan_bonus": 0.0,
        "body_movement_bonus": 0.0,
        "duel_rate_bonus": 0.0,
        "cultivation_bonus": 0.0,
    }
    for artifact in equipped_artifacts or []:
        effects = resolve_artifact_effects(profile, artifact, opponent_profile)
        for key in totals:
            totals[key] += float(effects.get(key, 0) or 0)
    return totals


def build_user_artifact_rows(
    profile_data: dict[str, Any],
    tg: int,
    retreating: bool,
    equip_limit: int,
    equipped_ids: set[int],
) -> list[dict[str, Any]]:
    rows = []
    for row in list_user_artifacts(tg):
        item = row["artifact"]
        item["resolved_effects"] = resolve_artifact_effects(profile_data, item)
        item["equipped"] = int(item["id"]) in equipped_ids
        usable = realm_requirement_met(profile_data, item.get("min_realm_stage"), item.get("min_realm_layer"))
        if usable:
            reason = ""
        else:
            reason = f"需要达到 {format_realm_requirement(item.get('min_realm_stage'), item.get('min_realm_layer'))}"
        if not item["equipped"] and len(equipped_ids) >= equip_limit:
            usable = False
            reason = f"当前最多只能装备 {equip_limit} 件法宝"
        if retreating:
            usable = False
            reason = "闭关期间无法切换法宝"
        item["usable"] = usable or item["equipped"]
        item["unusable_reason"] = "" if item["equipped"] else reason
        item["action_label"] = "卸下法宝" if item["equipped"] else "装备法宝"
        rows.append(row)
    return rows


def _build_user_technique_rows(profile_data: dict[str, Any]) -> list[dict[str, Any]]:
    current_id = int(profile_data.get("current_technique_id") or 0)
    rows = []
    for item in list_techniques(enabled_only=True):
        technique = dict(item)
        technique["resolved_effects"] = resolve_technique_effects(profile_data, technique)
        technique["active"] = int(technique.get("id") or 0) == current_id
        usable = realm_requirement_met(profile_data, technique.get("min_realm_stage"), technique.get("min_realm_layer"))
        reason = "" if usable else f"需要达到 {format_realm_requirement(technique.get('min_realm_stage'), technique.get('min_realm_layer'))}"
        technique["usable"] = usable or technique["active"]
        technique["unusable_reason"] = "" if technique["active"] else reason
        technique["action_label"] = "当前功法" if technique["active"] else "切换功法"
        rows.append(technique)
    return rows


def _current_technique_payload(profile_data: dict[str, Any]) -> dict[str, Any] | None:
    technique_id = int(profile_data.get("current_technique_id") or 0)
    if not technique_id:
        return None
    technique = serialize_technique(get_technique(technique_id))
    if not technique or not technique.get("enabled"):
        return None
    technique["resolved_effects"] = resolve_technique_effects(profile_data, technique)
    technique["active"] = True
    return technique


def ensure_seed_data() -> None:
    existing_artifact_names = {item["name"] for item in list_artifacts()}
    for payload in DEFAULT_ARTIFACTS:
        if payload["name"] not in existing_artifact_names:
            create_artifact(**payload)

    existing_pill_names = {item["name"] for item in list_pills()}
    for payload in DEFAULT_PILLS:
        if payload["name"] not in existing_pill_names:
            create_pill(**payload)

    existing_talisman_names = {item["name"] for item in list_talismans()}
    for payload in DEFAULT_TALISMANS:
        if payload["name"] not in existing_talisman_names:
            create_talisman(**payload)

    existing_technique_names = {item["name"] for item in list_techniques()}
    for payload in DEFAULT_TECHNIQUES:
        if payload["name"] not in existing_technique_names:
            create_technique(**payload)


def china_now():
    return utcnow() + timedelta(hours=8)


def is_same_china_day(left, right) -> bool:
    if left is None or right is None:
        return False
    return (left + timedelta(hours=8)).date() == (right + timedelta(hours=8)).date()


def realm_requirement_met(profile: dict[str, Any], min_stage: str | None, min_layer: int | None) -> bool:
    if not min_stage:
        return True

    current_stage = realm_index(profile.get("realm_stage"))
    required_stage = realm_index(min_stage)
    current_layer = int(profile.get("realm_layer") or 0)
    required_layer = int(min_layer or 1)
    if current_stage != required_stage:
        return current_stage > required_stage
    return current_layer >= required_layer


def format_realm_requirement(min_stage: str | None, min_layer: int | None) -> str:
    if not min_stage:
        return "无限制"
    return f"{min_stage}{int(min_layer or 1)}层"


def apply_cultivation_gain(stage: str, layer: int, cultivation: int, gain: int) -> tuple[int, int, list[int], int]:
    current_layer = max(int(layer or 1), 1)
    current_cultivation = max(int(cultivation or 0), 0) + max(int(gain or 0), 0)
    upgraded_layers: list[int] = []
    threshold = cultivation_threshold(stage, current_layer)

    while current_layer < 9 and current_cultivation >= threshold:
        current_cultivation -= threshold
        current_layer += 1
        upgraded_layers.append(current_layer)
        threshold = cultivation_threshold(stage, current_layer)

    if current_layer >= 9:
        current_cultivation = min(current_cultivation, threshold)

    remaining = max(threshold - current_cultivation, 0)
    return current_layer, current_cultivation, upgraded_layers, remaining


def _compute_immortal_touch_gain(stage: str, layer: int, cultivation: int, infusion_layers: int) -> int:
    simulated_layer = max(int(layer or 1), 1)
    simulated_cultivation = max(int(cultivation or 0), 0)
    remaining_layers = max(int(infusion_layers or 1), 1)
    total_gain = 0

    while remaining_layers > 0:
        threshold = cultivation_threshold(stage, simulated_layer)
        current = min(simulated_cultivation, threshold)
        total_gain += max(threshold - current, 0)
        if simulated_layer >= 9:
            break
        simulated_layer += 1
        simulated_cultivation = 0
        remaining_layers -= 1

    return total_gain


def immortal_touch_infuse_cultivation(actor_tg: int, target_tg: int) -> dict[str, Any]:
    if actor_tg == target_tg:
        raise ValueError("请回复其他道友后再施展仙人抚顶。")

    target = get_profile(target_tg, create=False)
    if target is None or not target.consented:
        raise ValueError("被回复的道友还没有踏入仙途。")

    ensure_not_in_retreat(target_tg)
    settings = get_xiuxian_settings()
    configured_layers = _coerce_int(
        settings.get("immortal_touch_infusion_layers"),
        DEFAULT_SETTINGS["immortal_touch_infusion_layers"],
        1,
    )
    stage = normalize_realm_stage(target.realm_stage or "炼气")
    current_layer = int(target.realm_layer or 1)
    current_cultivation = int(target.cultivation or 0)
    gain = _compute_immortal_touch_gain(stage, current_layer, current_cultivation, configured_layers)
    if gain <= 0:
        raise ValueError("对方当前修为已圆满，暂时无法继续灌注。")

    next_layer, next_cultivation, upgraded_layers, remaining = apply_cultivation_gain(
        stage,
        current_layer,
        current_cultivation,
        gain,
    )
    updated = upsert_profile(
        target_tg,
        cultivation=next_cultivation,
        realm_layer=next_layer,
    )
    threshold = cultivation_threshold(stage, next_layer)
    create_journal(actor_tg, "immortal_touch", "仙人抚顶", f"为 TG {target_tg} 灌注了 {gain} 点修为")
    create_journal(target_tg, "immortal_touch", "获仙人抚顶", f"获得 TG {actor_tg} 灌注的 {gain} 点修为")
    return {
        "gain": gain,
        "configured_layers": configured_layers,
        "upgraded_layers": upgraded_layers,
        "remaining": remaining,
        "breakthrough_ready": bool(next_layer >= 9 and next_cultivation >= threshold),
        "threshold": threshold,
        "profile": serialize_profile(updated),
    }


def build_progress(stage: str, layer: int, cultivation: int) -> dict[str, int | bool]:
    threshold = cultivation_threshold(stage, layer)
    current = min(max(int(cultivation or 0), 0), threshold)
    if layer < 9:
        return {
            "threshold": threshold,
            "current": current,
            "remaining": max(threshold - current, 0),
            "breakthrough_ready": False,
        }
    return {
        "threshold": threshold,
        "current": min(current, threshold),
        "remaining": max(threshold - min(current, threshold), 0),
        "breakthrough_ready": min(current, threshold) >= threshold,
    }


def _compute_retreat_plan(profile) -> dict[str, int]:
    profile_data = serialize_profile(profile)
    artifact_effects = merge_artifact_effects(profile_data, collect_equipped_artifacts(profile.tg))
    sect_effects = get_sect_effects(profile_data)
    technique_effects = resolve_technique_effects(profile_data, _current_technique_payload(profile_data))
    artifact_bonus = (
        int(artifact_effects.get("cultivation_bonus", 0))
        + int(sect_effects.get("cultivation_bonus", 0))
        + int(technique_effects.get("cultivation_bonus", 0))
        + int(profile_data.get("insight_bonus", 0) or 0)
    )
    poison_penalty = min(int(profile.dan_poison or 0) // 4, 25)
    gain_per_hour = max(90 + realm_index(profile.realm_stage) * 18 + int(profile.realm_layer or 1) * 10 + artifact_bonus * 2 - poison_penalty, 40)
    cost_per_hour = max(ceil(gain_per_hour / 12), 6)
    return {
        "gain_per_minute": max(gain_per_hour // 60, 1),
        "cost_per_minute": max(cost_per_hour // 60, 1),
    }


def _is_retreating(profile) -> bool:
    return bool(profile and profile.retreat_started_at and profile.retreat_end_at and int(profile.retreat_minutes_total or 0) > int(profile.retreat_minutes_resolved or 0))


def _settle_retreat_progress(tg: int) -> dict[str, Any] | None:
    profile = get_profile(tg, create=False)
    if profile is None or not _is_retreating(profile):
        return None

    now = utcnow()
    end_at = profile.retreat_end_at or now
    started_at = profile.retreat_started_at or now
    total_minutes = max(int(profile.retreat_minutes_total or 0), 0)
    resolved_minutes = max(int(profile.retreat_minutes_resolved or 0), 0)
    elapsed_minutes = int(max(min(now, end_at) - started_at, timedelta()).total_seconds() // 60)
    target_minutes = min(max(elapsed_minutes, 0), total_minutes)
    delta_minutes = max(target_minutes - resolved_minutes, 0)

    if delta_minutes <= 0:
        if now >= end_at and resolved_minutes >= total_minutes:
            upsert_profile(
                tg,
                retreat_started_at=None,
                retreat_end_at=None,
                retreat_gain_per_minute=0,
                retreat_cost_per_minute=0,
                retreat_minutes_total=0,
                retreat_minutes_resolved=0,
            )
        return None

    gain = delta_minutes * int(profile.retreat_gain_per_minute or 0)
    cost = delta_minutes * int(profile.retreat_cost_per_minute or 0)
    layer, cultivation, upgraded_layers, remaining = apply_cultivation_gain(
        profile.realm_stage or "炼气",
        int(profile.realm_layer or 1),
        int(profile.cultivation or 0),
        gain,
    )

    finished = target_minutes >= total_minutes or now >= end_at
    updated = upsert_profile(
        tg,
        cultivation=cultivation,
        realm_layer=layer,
        spiritual_stone=max(int(profile.spiritual_stone or 0) - cost, 0),
        retreat_minutes_resolved=target_minutes if not finished else total_minutes,
        retreat_started_at=None if finished else profile.retreat_started_at,
        retreat_end_at=None if finished else profile.retreat_end_at,
        retreat_gain_per_minute=0 if finished else int(profile.retreat_gain_per_minute or 0),
        retreat_cost_per_minute=0 if finished else int(profile.retreat_cost_per_minute or 0),
        retreat_minutes_total=0 if finished else total_minutes,
    )
    if finished:
        updated = upsert_profile(
            tg,
            retreat_minutes_resolved=0,
        )

    return {
        "gain": gain,
        "cost": cost,
        "upgraded_layers": upgraded_layers,
        "remaining": remaining,
        "finished": finished,
        "profile": serialize_profile(updated),
    }


def ensure_not_in_retreat(tg: int) -> None:
    profile = get_profile(tg, create=False)
    if profile is not None and _is_retreating(profile):
        raise ValueError("你正在闭关中，当前不能执行这个操作。")


def build_plugin_url(path: str) -> str | None:
    public_url = (api_config.public_url or "").rstrip("/")
    if not public_url:
        return None
    return f"{public_url}{path}"


def xiuxian_entry_button() -> InlineKeyboard:
    return ikb([[("初入仙途", "xiuxian:entry")]])


def xiuxian_confirm_keyboard() -> InlineKeyboard:
    app_url = build_plugin_url("/plugins/xiuxian/app")
    rows = [[("确认入道", "xiuxian:confirm"), ("返回", "back_start")]]
    if app_url:
        rows.append([("打开修仙面板", app_url, "url")])
    return ikb(rows)


def xiuxian_profile_keyboard() -> InlineKeyboard:
    app_url = build_plugin_url("/plugins/xiuxian/app")
    rows = [[("吐纳修炼", "xiuxian:train"), ("尝试突破", "xiuxian:break")]]
    if app_url:
        rows.append([("打开修仙面板", app_url, "url")])
    rows.append([("返回主页", "back_start")])
    return ikb(rows)


def leaderboard_keyboard(kind: str, page: int, total_pages: int) -> InlineKeyboard:
    keyboard = InlineKeyboard()
    keyboard.row(
        InlineButton("灵石榜", "xiuxian:rank:stone:1"),
        InlineButton("境界榜", "xiuxian:rank:realm:1"),
        InlineButton("法宝榜", "xiuxian:rank:artifact:1"),
    )
    pager = []
    if page > 1:
        pager.append(InlineButton("上一页", f"xiuxian:rank:{kind}:{page - 1}"))
    pager.append(InlineButton(f"{page}/{max(total_pages, 1)}", "xiuxian:noop"))
    if page < total_pages:
        pager.append(InlineButton("下一页", f"xiuxian:rank:{kind}:{page + 1}"))
    keyboard.row(*pager)
    return keyboard


def duel_keyboard(challenger_tg: int, defender_tg: int, stake: int, bet_minutes: int) -> InlineKeyboard:
    return ikb(
        [[
            ("接受斗法", f"xiuxian:duel:accept:{challenger_tg}:{defender_tg}:{stake}:{bet_minutes}"),
            ("拒绝斗法", f"xiuxian:duel:reject:{challenger_tg}:{defender_tg}:{stake}:{bet_minutes}"),
        ]]
    )


def cultivation_threshold(stage: str, layer: int) -> int:
    return 80 + realm_index(stage) * 30 + max(layer, 1) * 18


def next_realm_stage(stage: str) -> str | None:
    idx = realm_index(stage)
    if idx >= len(REALM_ORDER) - 1:
        return None
    return REALM_ORDER[idx + 1]


def determine_relation(primary: str, secondary: str) -> tuple[str, int]:
    if ELEMENT_GENERATES.get(primary) == secondary or ELEMENT_GENERATES.get(secondary) == primary:
        return "相生", 5
    if ELEMENT_CONTROLS.get(primary) == secondary or ELEMENT_CONTROLS.get(secondary) == primary:
        return "相克", -5
    return "平衡", 0


def ensure_xiuxian_profile(tg: int) -> dict[str, Any]:
    profile = get_profile(tg, create=True)
    return serialize_profile(profile)


def _legacy_serialize_full_profile(tg: int) -> dict[str, Any]:
    ensure_seed_data()
    profile = get_profile(tg, create=True)
    if profile and profile.consented:
        _settle_retreat_progress(tg)
        profile = get_profile(tg, create=False)

    profile_data = serialize_profile(profile)
    if profile_data is None:
        raise ValueError("未找到修仙档案。")

    progress = build_progress(
        profile_data["realm_stage"],
        int(profile_data["realm_layer"] or 1),
        int(profile_data["cultivation"] or 0),
    )
    retreating = _is_retreating(profile)
    xiuxian_settings = get_xiuxian_settings()
    equip_limit = max(int(xiuxian_settings.get("artifact_equip_limit", DEFAULT_SETTINGS["artifact_equip_limit"]) or 0), 1)
    equipped_rows = list_equipped_artifacts(tg)
    equipped = []
    equipped_ids: set[int] = set()
    for row in equipped_rows:
        item = row["artifact"]
        item["resolved_effects"] = resolve_artifact_effects(profile_data, item)
        item["equipped"] = True
        item["slot"] = row["slot"]
        equipped.append(item)
        equipped_ids.add(int(item["id"]))
    active_talisman = serialize_talisman(get_talisman(profile.active_talisman_id)) if profile and profile.active_talisman_id else None
    if active_talisman:
        active_talisman["resolved_effects"] = resolve_talisman_effects(profile_data, active_talisman)
    current_technique = _current_technique_payload(profile_data)

    artifacts = build_user_artifact_rows(profile_data, tg, retreating, equip_limit, equipped_ids)
    techniques = _build_user_technique_rows(profile_data)
    pills = []
    for row in list_user_pills(tg):
        item = row["pill"]
        item["resolved_effects"] = resolve_pill_effects(profile_data, item)
        usable = realm_requirement_met(profile_data, item.get("min_realm_stage"), item.get("min_realm_layer"))
        reason = "" if usable else f"需要达到 {format_realm_requirement(item.get('min_realm_stage'), item.get('min_realm_layer'))}"
        if item.get("pill_type") == "foundation":
            usable = False
            reason = "筑基丹只能在突破时配合使用"
        row["pill"]["usable"] = usable and not retreating
        row["pill"]["unusable_reason"] = "闭关期间无法使用丹药" if usable and retreating else reason
        pills.append(row)

    talismans = []
    for row in list_user_talismans(tg):
        item = row["talisman"]
        item["resolved_effects"] = resolve_talisman_effects(profile_data, item)
        usable = realm_requirement_met(profile_data, item.get("min_realm_stage"), item.get("min_realm_layer"))
        reason = "" if usable else f"需要达到 {format_realm_requirement(item.get('min_realm_stage'), item.get('min_realm_layer'))}"
        if profile_data.get("active_talisman_id") and profile_data.get("active_talisman_id") != item["id"]:
            usable = False
            reason = "你已经预装了一张待生效的符箓"
        item["usable"] = usable and not retreating
        item["active"] = profile_data.get("active_talisman_id") == item["id"]
        item["unusable_reason"] = "闭关期间无法启用符箓" if usable and not item["active"] and retreating else reason
        talismans.append(row)

    all_personal_shop = list_shop_items(official_only=False)
    personal_shop = [item for item in all_personal_shop if item["owner_tg"] == tg]
    community_shop = [item for item in all_personal_shop if item["owner_tg"] not in {None, tg}]
    settings = {
        **get_exchange_settings(),
        "artifact_equip_limit": equip_limit,
    }

    capabilities = {
        "can_train": profile_data["consented"] and not retreating and not is_same_china_day(profile.last_train_at, utcnow()),
        "train_reason": "" if not retreating and not is_same_china_day(profile.last_train_at, utcnow()) else ("闭关期间无法吐纳修炼" if retreating else "今日已经完成过吐纳修炼了"),
        "can_breakthrough": profile_data["consented"] and not retreating and int(profile_data["realm_layer"] or 0) >= 9 and bool(progress["breakthrough_ready"]),
        "breakthrough_reason": "" if not retreating and int(profile_data["realm_layer"] or 0) >= 9 and progress["breakthrough_ready"] else ("闭关期间无法突破" if retreating else "只有达到当前境界九层且满修为后才能突破"),
        "can_retreat": profile_data["consented"] and not retreating,
        "retreat_reason": "" if not retreating else "你正在闭关中",
        "is_in_retreat": retreating,
        "artifact_equip_limit": equip_limit,
        "equipped_artifact_count": len(equipped),
    }

    return {
        "profile": profile_data,
        "progress": progress,
        "capabilities": capabilities,
        "emby_balance": get_emby_balance(tg),
        "equipped_artifact": equipped[0] if equipped else None,
        "equipped_artifacts": equipped,
        "active_talisman": active_talisman,
        "current_technique": current_technique,
        "artifacts": artifacts,
        "pills": pills,
        "talismans": talismans,
        "techniques": techniques,
        "settings": settings,
        "official_shop": list_shop_items(official_only=True),
        "community_shop": community_shop,
        "personal_shop": personal_shop,
    }


def _find_pill_in_inventory(tg: int, pill_type: str) -> dict[str, Any] | None:
    for row in list_user_pills(tg):
        pill = row["pill"]
        if pill["pill_type"] == pill_type and row["quantity"] > 0:
            return row
    return None


def equip_artifact_for_user(tg: int, artifact_id: int) -> dict[str, Any]:
    ensure_not_in_retreat(tg)
    profile = serialize_profile(get_profile(tg, create=False))
    if profile is None:
        raise ValueError("你还没有踏入仙途。")

    owned = {row["artifact"]["id"] for row in list_user_artifacts(tg)}
    if artifact_id not in owned:
        raise ValueError("你的背包里没有这件法宝。")
    artifact = get_artifact(artifact_id)
    if artifact is None:
        raise ValueError("未找到目标法宝。")
    if not realm_requirement_met(profile, artifact.min_realm_stage, artifact.min_realm_layer):
        raise ValueError(f"需要达到 {format_realm_requirement(artifact.min_realm_stage, artifact.min_realm_layer)} 才能装备这件法宝。")

    equip_limit = max(int(get_xiuxian_settings().get("artifact_equip_limit", DEFAULT_SETTINGS["artifact_equip_limit"]) or 0), 1)
    result = set_equipped_artifact(tg, artifact_id, equip_limit)
    if result is None:
        raise ValueError("法宝装备状态更新失败。")
    return {
        "action": result["action"],
        "artifact_name": artifact.name,
        "profile": serialize_full_profile(tg),
    }


def activate_talisman_for_user(tg: int, talisman_id: int) -> dict[str, Any]:
    ensure_not_in_retreat(tg)
    profile_obj = get_profile(tg, create=False)
    if profile_obj is None or not profile_obj.consented:
        raise ValueError("你还没有踏入仙途。")
    if profile_obj.active_talisman_id:
        raise ValueError("你已经准备了一张符箓，需先消耗后才能再启用。")

    owned = {row["talisman"]["id"] for row in list_user_talismans(tg)}
    if talisman_id not in owned:
        raise ValueError("你的背包里没有这张符箓。")

    talisman = get_talisman(talisman_id)
    if talisman is None or not talisman.enabled:
        raise ValueError("未找到可用的符箓。")
    if not realm_requirement_met(serialize_profile(profile_obj), talisman.min_realm_stage, talisman.min_realm_layer):
        raise ValueError(f"需要达到 {format_realm_requirement(talisman.min_realm_stage, talisman.min_realm_layer)} 才能启用这张符箓。")
    if not consume_user_talisman(tg, talisman_id, 1):
        raise ValueError("你的背包里没有足够的符箓。")

    set_active_talisman(tg, talisman_id)
    return {
        "talisman": serialize_talisman(talisman),
        "profile": serialize_full_profile(tg),
    }


def activate_technique_for_user(tg: int, technique_id: int) -> dict[str, Any]:
    ensure_seed_data()
    profile_obj = get_profile(tg, create=False)
    if profile_obj is None or not profile_obj.consented:
        raise ValueError("你还没有踏入仙途。")
    technique = get_technique(technique_id)
    if technique is None or not technique.enabled:
        raise ValueError("未找到可用的功法。")
    profile_data = serialize_profile(profile_obj)
    if not realm_requirement_met(profile_data, technique.min_realm_stage, technique.min_realm_layer):
        raise ValueError(f"需要达到 {format_realm_requirement(technique.min_realm_stage, technique.min_realm_layer)} 才能参悟这门功法。")
    set_current_technique(tg, technique_id)
    return {
        "technique": serialize_technique(technique),
        "profile": serialize_full_profile(tg),
    }


def start_retreat_for_user(tg: int, hours: int) -> dict[str, Any]:
    profile = get_profile(tg, create=False)
    if profile is None or not profile.consented:
        raise ValueError("你还没有踏入仙途。")
    if _is_retreating(profile):
        raise ValueError("你已经在闭关中。")

    retreat_hours = max(min(int(hours or 0), 4), 1)
    plan = _compute_retreat_plan(profile)
    total_minutes = retreat_hours * 60
    total_cost = plan["cost_per_minute"] * total_minutes
    if int(profile.spiritual_stone or 0) < total_cost:
        raise ValueError(f"灵石不足，闭关 {retreat_hours} 小时预计需要 {total_cost} 灵石。")

    now = utcnow()
    updated = upsert_profile(
        tg,
        retreat_started_at=now,
        retreat_end_at=now + timedelta(hours=retreat_hours),
        retreat_gain_per_minute=plan["gain_per_minute"],
        retreat_cost_per_minute=plan["cost_per_minute"],
        retreat_minutes_total=total_minutes,
        retreat_minutes_resolved=0,
    )
    return {
        "hours": retreat_hours,
        "estimated_gain": plan["gain_per_minute"] * total_minutes,
        "estimated_cost": total_cost,
        "profile": serialize_full_profile(updated.tg),
    }


def finish_retreat_for_user(tg: int) -> dict[str, Any]:
    result = _settle_retreat_progress(tg)
    profile = get_profile(tg, create=False)
    if profile is None or not profile.consented:
        raise ValueError("你还没有踏入仙途。")
    if result is None and not _is_retreating(profile):
        raise ValueError("你当前并未处于闭关状态。")

    upsert_profile(
        tg,
        retreat_started_at=None,
        retreat_end_at=None,
        retreat_gain_per_minute=0,
        retreat_cost_per_minute=0,
        retreat_minutes_total=0,
        retreat_minutes_resolved=0,
    )
    return {
        "settled": result or {"gain": 0, "cost": 0, "upgraded_layers": [], "finished": True},
        "profile": serialize_full_profile(tg),
    }


def create_personal_shop_listing(
    *,
    tg: int,
    shop_name: str,
    item_kind: str,
    item_ref_id: int,
    quantity: int,
    price_stone: int,
    broadcast: bool,
) -> dict[str, Any]:
    profile = get_profile(tg, create=False)
    if profile is None or not profile.consented:
        raise ValueError("你还没有踏入仙途。")
    if _is_retreating(profile):
        raise ValueError("闭关期间无法上架个人商店。")

    item_name = ""
    if item_kind == "artifact":
        artifact = get_artifact(item_ref_id)
        if artifact is None:
            raise ValueError("未找到目标法宝。")
        if not use_user_artifact_listing_stock(tg, item_ref_id, quantity):
            raise ValueError("背包里的法宝数量不足。")
        item_name = artifact.name
    elif item_kind == "pill":
        pill = get_pill(item_ref_id)
        if pill is None:
            raise ValueError("未找到目标丹药。")
        if not use_user_pill_listing_stock(tg, item_ref_id, quantity):
            raise ValueError("背包里的丹药数量不足。")
        item_name = pill.name
    elif item_kind == "talisman":
        talisman = get_talisman(item_ref_id)
        if talisman is None:
            raise ValueError("未找到目标符箓。")
        if not use_user_talisman_listing_stock(tg, item_ref_id, quantity):
            raise ValueError("背包里的符箓数量不足。")
        item_name = talisman.name
    else:
        raise ValueError("不支持的上架物品类型。")

    settings = get_xiuxian_settings()
    broadcast_cost = int(settings.get("shop_broadcast_cost", DEFAULT_SETTINGS["shop_broadcast_cost"]) or 0)
    if broadcast and int(profile.spiritual_stone or 0) < broadcast_cost:
        raise ValueError("灵石不足，无法支付全群播报费用。")

    resolved_shop_name = str(shop_name or profile.shop_name or PERSONAL_SHOP_NAME).strip() or PERSONAL_SHOP_NAME

    listing = create_shop_item(
        owner_tg=tg,
        shop_name=resolved_shop_name,
        item_kind=item_kind,
        item_ref_id=item_ref_id,
        item_name=item_name,
        quantity=quantity,
        price_stone=price_stone,
        is_official=False,
    )

    updated = upsert_profile(
        tg,
        shop_name=resolved_shop_name,
        shop_broadcast=bool(broadcast),
        spiritual_stone=int(profile.spiritual_stone or 0) - (broadcast_cost if broadcast else 0),
    )

    return {
        "listing": listing,
        "broadcast_cost": broadcast_cost if broadcast else 0,
        "profile": serialize_profile(updated),
    }


def create_official_shop_listing(
    *,
    item_kind: str,
    item_ref_id: int,
    quantity: int,
    price_stone: int,
    shop_name: str | None = None,
) -> dict[str, Any]:
    settings = get_xiuxian_settings()
    official_name = shop_name or settings.get("official_shop_name", DEFAULT_SETTINGS["official_shop_name"])
    if item_kind == "artifact":
        artifact = get_artifact(item_ref_id)
        if artifact is None:
            raise ValueError("未找到目标法宝。")
        item_name = artifact.name
    elif item_kind == "pill":
        pill = get_pill(item_ref_id)
        if pill is None:
            raise ValueError("未找到目标丹药。")
        item_name = pill.name
    elif item_kind == "talisman":
        talisman = get_talisman(item_ref_id)
        if talisman is None:
            raise ValueError("未找到目标符箓。")
        item_name = talisman.name
    else:
        raise ValueError("不支持的官方商店物品类型。")

    return create_shop_item(
        owner_tg=None,
        shop_name=official_name,
        item_kind=item_kind,
        item_ref_id=item_ref_id,
        item_name=item_name,
        quantity=quantity,
        price_stone=price_stone,
        is_official=True,
    )


def patch_shop_listing(item_id: int, **fields) -> dict[str, Any] | None:
    return update_shop_item(item_id, **fields)


def update_xiuxian_settings(payload: dict[str, Any]) -> dict[str, Any]:
    patch = dict(payload)
    if "root_quality_value_rules" in patch:
        patch["root_quality_value_rules"] = _normalize_root_quality_value_rules(patch["root_quality_value_rules"])
    if "item_quality_value_rules" in patch:
        patch["item_quality_value_rules"] = _normalize_item_quality_value_rules(patch["item_quality_value_rules"])
    if "exploration_drop_weight_rules" in patch:
        defaults = DEFAULT_SETTINGS["exploration_drop_weight_rules"]
        raw = patch["exploration_drop_weight_rules"] if isinstance(patch["exploration_drop_weight_rules"], dict) else {}
        patch["exploration_drop_weight_rules"] = {
            "material_divine_sense_divisor": _coerce_int(raw.get("material_divine_sense_divisor"), defaults["material_divine_sense_divisor"], 1),
            "high_quality_threshold": min(
                _coerce_int(raw.get("high_quality_threshold"), defaults["high_quality_threshold"], 1),
                max(ROOT_QUALITY_LEVELS.values()),
            ),
            "high_quality_fortune_divisor": _coerce_int(raw.get("high_quality_fortune_divisor"), defaults["high_quality_fortune_divisor"], 1),
            "high_quality_root_level_start": _coerce_int(raw.get("high_quality_root_level_start"), defaults["high_quality_root_level_start"], 0),
        }
    if "high_quality_broadcast_level" in patch and patch["high_quality_broadcast_level"] is not None:
        patch["high_quality_broadcast_level"] = min(
            _coerce_int(patch["high_quality_broadcast_level"], DEFAULT_SETTINGS["high_quality_broadcast_level"], 1),
            max(ROOT_QUALITY_LEVELS.values()),
        )
    if "immortal_touch_infusion_layers" in patch and patch["immortal_touch_infusion_layers"] is not None:
        patch["immortal_touch_infusion_layers"] = min(
            _coerce_int(
                patch["immortal_touch_infusion_layers"],
                DEFAULT_SETTINGS["immortal_touch_infusion_layers"],
                1,
            ),
            9,
        )
    return set_xiuxian_settings(patch)


def grant_item_to_user(tg: int, item_kind: str, item_ref_id: int, quantity: int) -> dict[str, Any]:
    if item_kind == "artifact":
        return grant_artifact_to_user(tg, item_ref_id, quantity)
    if item_kind == "material":
        return grant_material_to_user(tg, item_ref_id, quantity)
    if item_kind == "pill":
        return grant_pill_to_user(tg, item_ref_id, quantity)
    if item_kind == "talisman":
        return grant_talisman_to_user(tg, item_ref_id, quantity)
    raise ValueError("不支持的发放物品类型。")


def purchase_shop_item(tg: int, item_id: int, quantity: int = 1) -> dict[str, Any]:
    ensure_not_in_retreat(tg)
    return sql_purchase_shop_item(tg, item_id, quantity)


def compute_artifact_score(
    profile: dict[str, Any],
    equipped_artifacts: list[dict[str, Any]] | None,
    opponent_profile: dict[str, Any] | None = None,
) -> int:
    if not equipped_artifacts:
        return 0
    effects = merge_artifact_effects(profile, equipped_artifacts, opponent_profile)
    return (
        int(round(effects.get("attack_bonus", 0)))
        + int(round(effects.get("defense_bonus", 0)))
        + int(round(effects.get("bone_bonus", 0)))
        + int(round(effects.get("comprehension_bonus", 0)))
        + int(round(effects.get("divine_sense_bonus", 0)))
        + int(round(effects.get("fortune_bonus", 0)))
        + int(round(effects.get("body_movement_bonus", 0)))
        + int(round(effects.get("qi_blood_bonus", 0) / 10))
        + int(round(effects.get("true_yuan_bonus", 0) / 10))
        + int(round(effects.get("duel_rate_bonus", 0))) * 10
        + int(round(effects.get("cultivation_bonus", 0))) * 2
    )


def compute_talisman_score(
    profile: dict[str, Any],
    active_talisman: dict[str, Any] | None,
    opponent_profile: dict[str, Any] | None = None,
) -> int:
    if active_talisman is None:
        return 0
    effects = resolve_talisman_effects(profile, active_talisman, opponent_profile)
    return (
        int(round(effects.get("attack_bonus", 0)))
        + int(round(effects.get("defense_bonus", 0)))
        + int(round(effects.get("bone_bonus", 0)))
        + int(round(effects.get("comprehension_bonus", 0)))
        + int(round(effects.get("divine_sense_bonus", 0)))
        + int(round(effects.get("fortune_bonus", 0)))
        + int(round(effects.get("body_movement_bonus", 0)))
        + int(round(effects.get("qi_blood_bonus", 0) / 10))
        + int(round(effects.get("true_yuan_bonus", 0) / 10))
        + int(round(effects.get("duel_rate_bonus", 0))) * 10
    )


def build_leaderboard(kind: str, page: int = 1, page_size: int = 20) -> dict[str, Any]:
    profiles = [serialize_profile(row) for row in list_profiles()]
    tgs = [int(item["tg"]) for item in profiles]
    emby_name_map = get_emby_name_map(tgs)

    rows = []
    for item in profiles:
        equipped_artifacts = collect_equipped_artifacts(int(item["tg"]))
        base = {
            "tg": item["tg"],
            "name": emby_name_map.get(item["tg"], f"TG {item['tg']}"),
            "realm_stage": item["realm_stage"],
            "realm_layer": item["realm_layer"],
            "spiritual_stone": item["spiritual_stone"],
            "artifact_name": ", ".join(artifact["name"] for artifact in equipped_artifacts[:3]) if equipped_artifacts else None,
            "artifact_score": compute_artifact_score(item, equipped_artifacts),
        }
        if kind == "stone":
            base["score"] = int(item["spiritual_stone"] or 0)
        elif kind == "realm":
            base["score"] = realm_index(item["realm_stage"]) * 1000 + int(item["realm_layer"] or 0) * 100 + int(item["cultivation"] or 0)
        else:
            base["score"] = base["artifact_score"]
        rows.append(base)

    rows.sort(key=lambda row: (row["score"], row["tg"]), reverse=True)
    rows = rows[:100]
    total = len(rows)
    total_pages = max((total + page_size - 1) // page_size, 1)
    current_page = min(max(int(page), 1), total_pages)
    start = (current_page - 1) * page_size
    items = rows[start:start + page_size]

    for index, item in enumerate(items, start=start + 1):
        item["rank"] = index

    return {
        "kind": kind,
        "page": current_page,
        "page_size": page_size,
        "total": total,
        "total_pages": total_pages,
        "items": items,
    }


def format_leaderboard_text(result: dict[str, Any]) -> str:
    title_map = {
        "stone": "灵石排行榜",
        "realm": "境界排行榜",
        "artifact": "法宝排行榜",
    }
    lines = [f"**{title_map.get(result['kind'], '排行榜')}**", f"第 {result['page']} 页 / 共 {result['total_pages']} 页", ""]
    if not result["items"]:
        lines.append("当前没有可显示的数据。")
        return "\n".join(lines)

    for item in result["items"]:
        if result["kind"] == "stone":
            desc = f"{item['spiritual_stone']} 灵石"
        elif result["kind"] == "realm":
            desc = f"{item['realm_stage']}{item['realm_layer']}层"
        else:
            desc = item["artifact_name"] or "暂无装备法宝"
        lines.append(f"{item['rank']}. {item['name']} | {desc}")
    return "\n".join(lines)


def create_foundation_pill_for_user_if_missing(tg: int) -> None:
    pill_row = _find_pill_in_inventory(tg, "foundation")
    if pill_row is not None:
        return

    for pill in list_pills(enabled_only=True):
        if pill["pill_type"] == "foundation":
            grant_pill_to_user(tg, pill["id"], 1)
            return


def admin_seed_demo_assets(tg: int) -> dict[str, Any]:
    ensure_seed_data()
    first_artifact = next((item for item in list_artifacts(enabled_only=True)), None)
    foundation_pill = next((item for item in list_pills(enabled_only=True) if item["pill_type"] == "foundation"), None)
    clear_pill = next((item for item in list_pills(enabled_only=True) if item["pill_type"] == "clear_poison"), None)
    first_talisman = next((item for item in list_talismans(enabled_only=True)), None)

    if first_artifact:
        grant_artifact_to_user(tg, first_artifact["id"], 1)
    if foundation_pill:
        grant_pill_to_user(tg, foundation_pill["id"], 1)
    if clear_pill:
        grant_pill_to_user(tg, clear_pill["id"], 1)
    if first_talisman:
        grant_talisman_to_user(tg, first_talisman["id"], 1)

    return serialize_full_profile(tg)


def maybe_gain_cultivation_from_chat(tg: int) -> dict[str, Any] | None:
    profile = get_profile(tg, create=False)
    if profile is None or not profile.consented or _is_retreating(profile):
        return None

    settings = get_xiuxian_settings()
    chance = max(min(int(settings.get("chat_cultivation_chance", DEFAULT_SETTINGS["chat_cultivation_chance"]) or 0), 100), 0)
    if chance <= 0 or random.randint(1, 100) > chance:
        return None

    min_gain = max(int(settings.get("chat_cultivation_min_gain", DEFAULT_SETTINGS["chat_cultivation_min_gain"]) or 1), 1)
    max_gain = max(int(settings.get("chat_cultivation_max_gain", DEFAULT_SETTINGS["chat_cultivation_max_gain"]) or min_gain), min_gain)
    gain = random.randint(min_gain, max_gain)
    layer, cultivation, upgraded_layers, remaining = apply_cultivation_gain(
        profile.realm_stage or "炼气",
        int(profile.realm_layer or 1),
        int(profile.cultivation or 0),
        gain,
    )
    updated = upsert_profile(
        tg,
        cultivation=cultivation,
        realm_layer=layer,
    )
    return {
        "gain": gain,
        "upgraded_layers": upgraded_layers,
        "remaining": remaining,
        "profile": serialize_profile(updated),
    }


def broadcast_shop_copy(seller_name: str, shop_name: str, item_name: str, price_stone: int) -> str:
    return (
        f"【坊市播报】{seller_name} 刚刚在 **{shop_name}** 上架了 **{item_name}**\n"
        f"售价：{price_stone} 灵石\n"
        f"感兴趣的道友可以前往修仙面板查看。哼，仙途上的细账本女仆都替你理好了，继续往前走。"
    )


def convert_emby_coin_to_stone(tg: int, amount: int) -> dict[str, Any]:
    return convert_coin_to_stone(tg, amount)


def convert_stone_to_emby_coin(tg: int, amount: int) -> dict[str, Any]:
    return convert_stone_to_coin(tg, amount)


def list_public_shop_items() -> dict[str, Any]:
    settings = get_xiuxian_settings()
    return {
        "official_shop_name": settings.get("official_shop_name", DEFAULT_SETTINGS["official_shop_name"]),
        "official_items": list_shop_items(official_only=True),
    }


def search_xiuxian_players(
    query: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> dict[str, Any]:
    return search_profiles(query=query, page=page, page_size=page_size)


def admin_patch_player(tg: int, **fields) -> dict[str, Any] | None:
    return admin_patch_profile(tg, **fields)


def _battle_bundle(bundle_or_profile: dict[str, Any], opponent_profile: dict[str, Any] | None = None, apply_random: bool = False) -> dict[str, Any]:
    if "profile" in bundle_or_profile:
        bundle = bundle_or_profile
        profile = dict(bundle["profile"])
        artifacts = bundle.get("equipped_artifacts") or []
        talisman = bundle.get("active_talisman")
        technique = bundle.get("current_technique")
    else:
        profile = dict(bundle_or_profile)
        artifacts = collect_equipped_artifacts(int(profile["tg"]))
        active_talisman_id = profile.get("active_talisman_id")
        talisman = serialize_talisman(get_talisman(int(active_talisman_id))) if active_talisman_id else None
        current_technique_id = profile.get("current_technique_id")
        technique = serialize_technique(get_technique(int(current_technique_id))) if current_technique_id else None

    quality_name = _normalized_root_quality(profile)
    quality = _root_quality_payload(quality_name)
    sect_effects = get_sect_effects(profile)
    artifact_effects = merge_artifact_effects(profile, artifacts, opponent_profile)
    talisman_effects = resolve_talisman_effects(profile, talisman, opponent_profile) if talisman else None
    technique_effects = resolve_technique_effects(profile, technique, opponent_profile) if technique else None
    stats = _effective_stats(profile, artifact_effects, talisman_effects, sect_effects, technique_effects)

    stage_index = realm_index(profile.get("realm_stage"))
    layer = int(profile.get("realm_layer") or 0)
    realm_base = 180 + stage_index * 220 + max(layer, 1) * 34
    attribute_factor = 1 + stats["bone"] / 240 + stats["comprehension"] / 260 + stats["divine_sense"] / 280 + stats["fortune"] / 320
    offense_factor = 1 + stats["attack_power"] / 200
    defense_factor = 1 + stats["defense_power"] / 220
    vitality_factor = 1 + stats["qi_blood"] / 2200
    mana_factor = 1 + stats["true_yuan"] / 2400
    movement_factor = 1 + stats["body_movement"] / 240
    artifact_factor = 1 + (
        artifact_effects.get("attack_bonus", 0)
        + artifact_effects.get("defense_bonus", 0)
        + artifact_effects.get("bone_bonus", 0)
        + artifact_effects.get("comprehension_bonus", 0)
        + artifact_effects.get("divine_sense_bonus", 0)
        + artifact_effects.get("fortune_bonus", 0)
        + artifact_effects.get("qi_blood_bonus", 0) / 8
        + artifact_effects.get("true_yuan_bonus", 0) / 8
        + artifact_effects.get("body_movement_bonus", 0)
    ) / 260
    talisman_factor = 1.0
    if talisman_effects:
        talisman_factor += (
            talisman_effects.get("attack_bonus", 0)
            + talisman_effects.get("defense_bonus", 0)
            + talisman_effects.get("bone_bonus", 0)
            + talisman_effects.get("comprehension_bonus", 0)
            + talisman_effects.get("divine_sense_bonus", 0)
            + talisman_effects.get("fortune_bonus", 0)
            + talisman_effects.get("qi_blood_bonus", 0) / 8
            + talisman_effects.get("true_yuan_bonus", 0) / 8
            + talisman_effects.get("body_movement_bonus", 0)
        ) / 320

    root_factor = float(quality["combat_factor"])
    if opponent_profile:
        root_factor += _root_element_duel_modifier(profile, opponent_profile)
    if profile.get("root_type") == "变异灵根":
        root_factor += 0.03
    duel_rate_factor = 1 + (stats["duel_rate_bonus"] / 100)
    random_factor = random.uniform(0.95, 1.10) if apply_random else 1.0
    power = (
        realm_base
        * attribute_factor
        * offense_factor
        * defense_factor
        * vitality_factor
        * mana_factor
        * movement_factor
        * max(root_factor, 0.75)
        * max(artifact_factor, 0.8)
        * max(talisman_factor, 0.85)
        * max(duel_rate_factor, 0.7)
        * random_factor
    )
    return {
        "profile": profile,
        "quality": quality_name,
        "quality_payload": quality,
        "stats": stats,
        "artifact_effects": artifact_effects,
        "talisman_effects": talisman_effects or {},
        "sect_effects": sect_effects,
        "technique_effects": technique_effects or {},
        "power": float(power),
    }


def serialize_full_profile(tg: int) -> dict[str, Any]:
    bundle = _legacy_serialize_full_profile(tg)
    profile = bundle.get("profile") or {}
    has_root = bool(str(profile.get("root_type") or "").strip() or str(profile.get("root_quality") or "").strip())
    if has_root:
        quality_name = _normalized_root_quality(profile)
        quality = _root_quality_payload(quality_name)
        profile["root_quality"] = quality_name
        profile["root_quality_level"] = profile.get("root_quality_level") or quality["level"]
        profile["root_quality_color"] = profile.get("root_quality_color") or quality["color"]
    else:
        profile["root_quality"] = None
        profile["root_quality_level"] = None
        profile["root_quality_color"] = None
    profile["root_text"] = format_root(profile)
    battle = _battle_bundle(bundle)
    bundle["effective_stats"] = {
        key: int(round(value)) if isinstance(value, (int, float)) else value
        for key, value in battle["stats"].items()
    }
    bundle["combat_power"] = int(round(battle["power"]))
    return bundle


def generate_root_payload() -> dict[str, Any]:
    quality_name = _roll_root_quality()
    quality = _root_quality_payload(quality_name)
    if quality_name == "天灵根":
        primary = random.choice(FIVE_ELEMENTS)
        return {
            "root_type": "天灵根",
            "root_primary": primary,
            "root_secondary": None,
            "root_relation": "天道垂青",
            "root_bonus": 12,
            "root_quality": quality_name,
            "root_quality_level": quality["level"],
            "root_quality_color": quality["color"],
        }
    if quality_name == "变异灵根":
        primary = random.choice(ROOT_VARIANT_ELEMENTS)
        return {
            "root_type": "变异灵根",
            "root_primary": primary,
            "root_secondary": None,
            "root_relation": "异灵独秀",
            "root_bonus": 10,
            "root_quality": quality_name,
            "root_quality_level": quality["level"],
            "root_quality_color": quality["color"],
        }
    if random.randint(1, 100) <= 10:
        primary, secondary = random.sample(FIVE_ELEMENTS, 2)
        relation, bonus = determine_relation(primary, secondary)
        return {
            "root_type": "双灵根",
            "root_primary": primary,
            "root_secondary": secondary,
            "root_relation": relation,
            "root_bonus": bonus,
            "root_quality": quality_name,
            "root_quality_level": quality["level"],
            "root_quality_color": quality["color"],
        }
    primary = random.choice(FIVE_ELEMENTS)
    return {
        "root_type": "单灵根",
        "root_primary": primary,
        "root_secondary": None,
        "root_relation": "平稳中正",
        "root_bonus": 0,
        "root_quality": quality_name,
        "root_quality_level": quality["level"],
        "root_quality_color": quality["color"],
    }


def format_root(payload: dict[str, Any]) -> str:
    root_type = str(payload.get("root_type") or "").strip()
    if not root_type:
        return "尚未踏入仙途"

    quality = _normalized_root_quality(payload)
    primary = str(payload.get("root_primary") or "")
    secondary = str(payload.get("root_secondary") or "")
    relation = str(payload.get("root_relation") or "")
    if root_type in {"天灵根", "变异灵根"}:
        return f"{quality} · {primary}"
    if root_type == "双灵根":
        return f"{quality} · {primary}/{secondary} · {relation}"
    return f"{quality} · {primary}"


def init_path_for_user(tg: int) -> dict[str, Any]:
    ensure_seed_data()
    profile = get_profile(tg, create=True)
    if profile and profile.consented:
        return serialize_full_profile(tg)

    root_payload = generate_root_payload()
    stats = _build_opening_stats(root_payload)
    updated = upsert_profile(
        tg,
        consented=True,
        root_type=root_payload["root_type"],
        root_primary=root_payload["root_primary"],
        root_secondary=root_payload["root_secondary"],
        root_relation=root_payload["root_relation"],
        root_bonus=root_payload["root_bonus"],
        root_quality=root_payload["root_quality"],
        root_quality_level=root_payload["root_quality_level"],
        root_quality_color=root_payload["root_quality_color"],
        realm_stage="炼气",
        realm_layer=1,
        cultivation=0,
        spiritual_stone=50,
        dan_poison=0,
        shop_name="",
        shop_broadcast=False,
        **stats,
    )
    return serialize_full_profile(updated.tg)


def practice_for_user(tg: int) -> dict[str, Any]:
    profile = get_profile(tg, create=False)
    if profile is None or not profile.consented:
        raise ValueError("你还没有踏入仙途。")
    if _is_retreating(profile):
        raise ValueError("闭关期间无法吐纳修炼。")
    if is_same_china_day(profile.last_train_at, utcnow()):
        raise ValueError("今日已经完成过吐纳修炼了。")

    profile_data = serialize_profile(profile)
    artifact_effects = merge_artifact_effects(profile_data, collect_equipped_artifacts(tg))
    active_talisman = serialize_talisman(get_talisman(profile.active_talisman_id)) if profile.active_talisman_id else None
    talisman_effects = resolve_talisman_effects(profile_data, active_talisman) if active_talisman else None
    current_technique = _current_technique_payload(profile_data)
    technique_effects = resolve_technique_effects(profile_data, current_technique) if current_technique else None
    stats = _effective_stats(profile_data, artifact_effects, talisman_effects, get_sect_effects(profile_data), technique_effects)
    quality = _root_quality_payload(_normalized_root_quality(profile_data))
    poison_penalty = max(float(profile.dan_poison or 0) - stats["bone"] * 0.45, 0.0) / 110
    base_gain = random.randint(18, 36)
    gain = int(round((base_gain + stats["bone"] * 0.55 + stats["comprehension"] * 0.75 + stats["cultivation_bonus"]) * quality["cultivation_rate"] * max(0.55, 1 - poison_penalty)))
    gain = max(gain, 5)
    stone_gain = random.randint(2, 8) + int(stats["fortune"] // 18)
    stage = normalize_realm_stage(profile.realm_stage or "炼气")
    layer, cultivation, upgraded_layers, remaining = apply_cultivation_gain(stage, int(profile.realm_layer or 1), int(profile.cultivation or 0), gain)
    updated = upsert_profile(
        tg,
        cultivation=cultivation,
        spiritual_stone=int(profile.spiritual_stone or 0) + stone_gain,
        realm_layer=layer,
        last_train_at=utcnow(),
    )
    return {
        "gain": gain,
        "stone_gain": stone_gain,
        "upgraded_layers": upgraded_layers,
        "remaining": remaining,
        "profile": serialize_full_profile(updated.tg),
    }


def breakthrough_for_user(tg: int, use_pill: bool = False) -> dict[str, Any]:
    profile = get_profile(tg, create=False)
    if profile is None or not profile.consented:
        raise ValueError("你还没有踏入仙途。")
    if _is_retreating(profile):
        raise ValueError("闭关期间无法突破。")
    if int(profile.realm_layer or 0) < 9:
        raise ValueError("只有达到当前大境界九层后才能尝试突破。")

    stage = normalize_realm_stage(profile.realm_stage or "炼气")
    required_cultivation = cultivation_threshold(stage, 9)
    if int(profile.cultivation or 0) < required_cultivation:
        raise ValueError(f"当前修为尚未圆满，还差 {required_cultivation - int(profile.cultivation or 0)} 点修为。")
    next_stage = next_realm_stage(stage)
    if next_stage is None:
        raise ValueError("你已经走到当前修炼体系的尽头。")

    profile_data = serialize_profile(profile)
    artifact_effects = merge_artifact_effects(profile_data, collect_equipped_artifacts(tg))
    active_talisman = serialize_talisman(get_talisman(profile.active_talisman_id)) if profile.active_talisman_id else None
    talisman_effects = resolve_talisman_effects(profile_data, active_talisman) if active_talisman else None
    current_technique = _current_technique_payload(profile_data)
    technique_effects = resolve_technique_effects(profile_data, current_technique) if current_technique else None
    stats = _effective_stats(profile_data, artifact_effects, talisman_effects, get_sect_effects(profile_data), technique_effects)
    quality = _root_quality_payload(_normalized_root_quality(profile_data))
    success_rate = BREAKTHROUGH_BASE_RATE.get(stage, 12)
    success_rate += int(round((stats["bone"] - 12) * 0.45))
    success_rate += int(round((stats["comprehension"] - 12) * 0.6))
    success_rate += int(quality["breakthrough_bonus"])
    success_rate += int(round((technique_effects or {}).get("breakthrough_bonus", 0)))
    success_rate -= int(max(float(profile.dan_poison or 0) - stats["bone"] * 0.3, 0) // 8)
    if _normalized_root_quality(profile_data) == "天灵根":
        success_rate += 4

    pill_bonus = 0
    used_pill_name = None
    if stage == "炼气" and use_pill:
        pill_row = _find_pill_in_inventory(tg, "foundation")
        if pill_row is None:
            raise ValueError("你没有可用的筑基丹。")
        used_pill_name = pill_row["pill"]["name"]
        pill_effects = resolve_pill_effects(profile_data, pill_row["pill"], {"pill_uses": int(profile.breakthrough_pill_uses or 0), "base_success_rate": success_rate})
        base_bonus = max(50 - int(profile.breakthrough_pill_uses or 0) * 5, 30)
        pill_bonus = max(int(round(pill_effects.get("success_rate_bonus", 0))), base_bonus)
        success_rate += pill_bonus

    success_rate = max(min(success_rate, 95), 1)
    roll = random.randint(1, 100)
    success = roll <= success_rate
    if use_pill and used_pill_name:
        pill_row = _find_pill_in_inventory(tg, "foundation")
        if pill_row is None or not consume_user_pill(tg, pill_row["pill"]["id"], 1):
            raise ValueError("筑基丹消耗失败，请稍后再试。")

    if success:
        updated = upsert_profile(
            tg,
            realm_stage=next_stage,
            realm_layer=1,
            cultivation=0,
            breakthrough_pill_uses=int(profile.breakthrough_pill_uses or 0) + (1 if use_pill else 0),
            qi_blood=int(profile.qi_blood or 0) + 25 + int(stats["bone"] // 2),
            true_yuan=int(profile.true_yuan or 0) + 20 + int(stats["comprehension"] // 2),
            attack_power=int(profile.attack_power or 0) + 3,
            defense_power=int(profile.defense_power or 0) + 3,
        )
    else:
        updated = upsert_profile(
            tg,
            cultivation=max(int(profile.cultivation or 0) - required_cultivation // 2, 0),
            breakthrough_pill_uses=int(profile.breakthrough_pill_uses or 0) + (1 if use_pill else 0),
        )
    return {
        "success": success,
        "roll": roll,
        "success_rate": success_rate,
        "pill_bonus": pill_bonus,
        "used_pill": used_pill_name,
        "profile": serialize_full_profile(updated.tg),
    }


def consume_pill_for_user(tg: int, pill_id: int) -> dict[str, Any]:
    profile = get_profile(tg, create=False)
    if profile is None or not profile.consented:
        raise ValueError("你还没有踏入仙途。")
    if _is_retreating(profile):
        raise ValueError("闭关期间无法服用丹药。")
    pill = get_pill(pill_id)
    if pill is None or not pill.enabled:
        raise ValueError("未找到可用的丹药。")
    profile_data = serialize_profile(profile)
    if not realm_requirement_met(profile_data, pill.min_realm_stage, pill.min_realm_layer):
        raise ValueError(f"需要达到 {format_realm_requirement(pill.min_realm_stage, pill.min_realm_layer)} 才能服用这枚丹药。")
    if pill.pill_type == "foundation":
        raise ValueError("筑基丹只能在突破时使用。")
    if not consume_user_pill(tg, pill_id, 1):
        raise ValueError("你的背包里没有这枚丹药。")

    pill_data = serialize_pill(pill)
    effects = resolve_pill_effects(profile_data, pill_data)
    bone_resistance = min((float(profile.bone or 0) / 200), 0.45)
    dan_poison = min(int(profile.dan_poison or 0) + int(round(float(effects.get("poison_delta", 0) or 0) * (1 - bone_resistance))), 100)
    cultivation = int(profile.cultivation or 0)
    spiritual_stone = int(profile.spiritual_stone or 0)
    bone = int(profile.bone or 0) + int(round(effects.get("bone_bonus", 0)))
    comprehension = int(profile.comprehension or 0) + int(round(effects.get("comprehension_bonus", 0)))
    divine_sense = int(profile.divine_sense or 0) + int(round(effects.get("divine_sense_bonus", 0)))
    fortune = int(profile.fortune or 0) + int(round(effects.get("fortune_bonus", 0)))
    qi_blood = int(profile.qi_blood or 0) + int(round(effects.get("qi_blood_bonus", 0)))
    true_yuan = int(profile.true_yuan or 0) + int(round(effects.get("true_yuan_bonus", 0)))
    body_movement = int(profile.body_movement or 0) + int(round(effects.get("body_movement_bonus", 0)))
    attack_power = int(profile.attack_power or 0) + int(round(effects.get("attack_bonus", 0)))
    defense_power = int(profile.defense_power or 0) + int(round(effects.get("defense_bonus", 0)))

    if pill.pill_type == "clear_poison":
        dan_poison = max(dan_poison - int(round(effects.get("clear_poison", effects.get("effect_value", 50)))), 0)
    elif pill.pill_type == "cultivation":
        cultivation += int(round(effects.get("cultivation_gain", effects.get("effect_value", 0))))
    elif pill.pill_type == "stone":
        spiritual_stone += int(round(effects.get("stone_gain", effects.get("effect_value", 0))))

    layer, cultivation, _, _ = apply_cultivation_gain(normalize_realm_stage(profile.realm_stage or "炼气"), int(profile.realm_layer or 1), cultivation, 0)
    updated = upsert_profile(
        tg,
        dan_poison=dan_poison,
        cultivation=cultivation,
        spiritual_stone=spiritual_stone,
        bone=bone,
        comprehension=comprehension,
        divine_sense=divine_sense,
        fortune=fortune,
        qi_blood=qi_blood,
        true_yuan=true_yuan,
        body_movement=body_movement,
        attack_power=attack_power,
        defense_power=defense_power,
        realm_layer=layer,
    )
    return {"pill": {**pill_data, "resolved_effects": effects}, "profile": serialize_full_profile(updated.tg)}


def compute_duel_odds(challenger_tg: int, defender_tg: int) -> dict[str, Any]:
    challenger = serialize_full_profile(challenger_tg)
    defender = serialize_full_profile(defender_tg)
    challenger_profile = challenger["profile"]
    defender_profile = defender["profile"]
    if not challenger_profile["consented"] or not defender_profile["consented"]:
        raise ValueError("斗法双方都必须已经踏入仙途。")

    challenger_state = _battle_bundle(challenger, defender_profile)
    defender_state = _battle_bundle(defender, challenger_profile)
    total_power = max(challenger_state["power"] + defender_state["power"], 1)
    rate = challenger_state["power"] / total_power
    stage_diff = realm_index(challenger_profile["realm_stage"]) - realm_index(defender_profile["realm_stage"])
    if abs(stage_diff) >= 2:
        rate = max(min(rate, 0.999), 0.001)
    else:
        rate = max(min(rate, 0.97), 0.03)
    defender_rate = max(min(1 - rate, 0.999), 0.001)
    return {
        "challenger": challenger,
        "defender": defender,
        "challenger_rate": round(rate, 4),
        "defender_rate": round(defender_rate, 4),
        "challenger_power": round(challenger_state["power"], 2),
        "defender_power": round(defender_state["power"], 2),
        "weights": {
            "stage_diff": stage_diff,
            "root_modifier": round(_root_element_duel_modifier(challenger_profile, defender_profile), 4),
            "challenger_quality": challenger_state["quality"],
            "defender_quality": defender_state["quality"],
            "challenger_attack": round(challenger_state["stats"]["attack_power"]),
            "challenger_defense": round(challenger_state["stats"]["defense_power"]),
            "challenger_qi_blood": round(challenger_state["stats"]["qi_blood"]),
            "challenger_true_yuan": round(challenger_state["stats"]["true_yuan"]),
            "challenger_body_movement": round(challenger_state["stats"]["body_movement"]),
            "defender_attack": round(defender_state["stats"]["attack_power"]),
            "defender_defense": round(defender_state["stats"]["defense_power"]),
            "defender_qi_blood": round(defender_state["stats"]["qi_blood"]),
            "defender_true_yuan": round(defender_state["stats"]["true_yuan"]),
            "defender_body_movement": round(defender_state["stats"]["body_movement"]),
        },
    }


def resolve_duel(challenger_tg: int, defender_tg: int, stake: int = 0) -> dict[str, Any]:
    duel = compute_duel_odds(challenger_tg, defender_tg)
    challenger_profile = duel["challenger"]["profile"]
    defender_profile = duel["defender"]["profile"]
    stake_amount = max(int(stake), 0)
    if stake_amount > 0:
        if int(challenger_profile["spiritual_stone"] or 0) < stake_amount or int(defender_profile["spiritual_stone"] or 0) < stake_amount:
            raise ValueError("双方至少有一方灵石不足，无法进行赌斗。")

    challenger_state = _battle_bundle(duel["challenger"], defender_profile, apply_random=True)
    defender_state = _battle_bundle(duel["defender"], challenger_profile, apply_random=True)
    total_power = max(challenger_state["power"] + defender_state["power"], 1)
    dynamic_rate = challenger_state["power"] / total_power
    stage_diff = realm_index(challenger_profile["realm_stage"]) - realm_index(defender_profile["realm_stage"])
    if abs(stage_diff) >= 2:
        dynamic_rate = max(min(dynamic_rate, 0.999), 0.001)
    else:
        dynamic_rate = max(min(dynamic_rate, 0.97), 0.03)
    roll = random.random()
    challenger_win = roll <= dynamic_rate
    winner_tg = challenger_tg if challenger_win else defender_tg
    loser_tg = defender_tg if challenger_win else challenger_tg
    winner_profile = get_profile(winner_tg, create=False)
    loser_profile = get_profile(loser_tg, create=False)
    if winner_profile is None or loser_profile is None:
        raise ValueError("斗法双方的修仙资料缺失。")

    if stake_amount:
        upsert_profile(winner_tg, spiritual_stone=int(winner_profile.spiritual_stone or 0) + stake_amount)
        upsert_profile(loser_tg, spiritual_stone=max(int(loser_profile.spiritual_stone or 0) - stake_amount, 0))

    create_duel_record(
        challenger_tg=challenger_tg,
        defender_tg=defender_tg,
        winner_tg=winner_tg,
        loser_tg=loser_tg,
        challenger_rate=int(round(dynamic_rate * 1000)),
        defender_rate=int(round((1 - dynamic_rate) * 1000)),
        summary=f"战力对比 {challenger_state['power']:.1f} vs {defender_state['power']:.1f}",
    )
    return {
        "challenger": serialize_full_profile(challenger_tg),
        "defender": serialize_full_profile(defender_tg),
        "winner_tg": winner_tg,
        "loser_tg": loser_tg,
        "challenger_rate": dynamic_rate,
        "defender_rate": 1 - dynamic_rate,
        "roll": roll,
        "winner_power": round(max(challenger_state["power"], defender_state["power"]), 2),
        "loser_power": round(min(challenger_state["power"], defender_state["power"]), 2),
        "stake": stake_amount,
        "pot": stake_amount * 2,
        "summary": f"战力对比 {challenger_state['power']:.1f} vs {defender_state['power']:.1f}",
    }


def generate_shop_name(first_name: str) -> str:
    return PERSONAL_SHOP_NAME


def generate_duel_preview_text(duel: dict[str, Any], stake: int = 0) -> str:
    challenger = duel["challenger"]["profile"]
    defender = duel["defender"]["profile"]
    challenger_name = challenger.get("display_label") or f"TG {challenger['tg']}"
    defender_name = defender.get("display_label") or f"TG {defender['tg']}"
    extra = f"\n赌注：每人 {stake} 灵石" if stake else ""
    return (
        f"⚔️ **斗法邀请**\n"
        f"挑战者：{challenger_name} {challenger['realm_stage']}{challenger['realm_layer']}层\n"
        f"应战者：{defender_name} {defender['realm_stage']}{defender['realm_layer']}层\n"
        f"当前预测胜率：挑战者 {duel['challenger_rate'] * 100:.1f}% / 应战者 {duel['defender_rate'] * 100:.1f}%"
        f"{extra}"
    )

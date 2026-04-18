from __future__ import annotations

import random
import re
from datetime import timedelta
from typing import Any

from bot.sql_helper import Session
from bot.sql_helper.sql_xiuxian import (
    DEFAULT_SETTINGS,
    QUALITY_LABEL_LEVELS,
    XiuxianArtifact,
    XiuxianArtifactInventory,
    XiuxianEquippedArtifact,
    XiuxianExploration,
    XiuxianProfile,
    XiuxianScene,
    XiuxianSceneDrop,
    XiuxianUserTechnique,
    apply_spiritual_stone_delta,
    create_journal,
    create_scene,
    create_scene_drop,
    get_artifact,
    get_material,
    get_pill,
    get_profile,
    get_recipe,
    get_scene,
    get_shared_spiritual_stone_total,
    get_technique,
    get_talisman,
    get_xiuxian_settings,
    grant_artifact_to_user,
    grant_material_to_user,
    grant_pill_to_user,
    grant_recipe_to_user,
    grant_talisman_to_user,
    grant_technique_to_user,
    list_scene_drops,
    list_recipe_ingredients,
    list_recipes,
    list_user_techniques,
    normalize_technique_capacity,
    realm_index,
    serialize_artifact,
    serialize_exploration,
    serialize_material,
    serialize_pill,
    serialize_profile,
    serialize_recipe,
    serialize_scene,
    serialize_technique,
    serialize_talisman,
    utcnow,
)
from bot.plugins.xiuxian_game.achievement_service import record_exploration_metrics
from bot.plugins.xiuxian_game.probability import roll_probability_percent


RARITY_LEVEL_MAP = {
    **QUALITY_LABEL_LEVELS,
    "黄品": 2,
    "玄品": 3,
    "地品": 4,
    "天品": 5,
}


def _legacy_service():
    from bot.plugins.xiuxian_game import service as legacy_service

    return legacy_service


def _clean_scene_fragment(raw: Any) -> str:
    text = re.sub(r"\s+", " ", str(raw or "")).strip()
    if not text:
        return ""
    return text.strip("，。！？；、,.!?; ")


def _join_scene_fragments(*parts: Any) -> str:
    rows: list[str] = []
    seen: set[str] = set()
    for part in parts:
        text = _clean_scene_fragment(part)
        if not text or text in seen:
            continue
        rows.append(text)
        seen.add(text)
    if not rows:
        return ""
    combined = "，".join(rows)
    combined = re.sub(r"[，、]{2,}", "，", combined)
    combined = re.sub(r"[。！？]{2,}", "。", combined)
    combined = re.sub(r"[；;]{2,}", "；", combined)
    return combined.strip("，。！？；、 ")


def _risk_level_label(risk_percent: int) -> tuple[str, str]:
    if risk_percent <= 5:
        return "stable", "稳妥"
    if risk_percent <= 18:
        return "light", "可控"
    if risk_percent <= 40:
        return "medium", "有压"
    if risk_percent <= 70:
        return "high", "高危"
    return "extreme", "九死一生"


def _grant_item_by_kind(tg: int, kind: str, ref_id: int, quantity: int) -> dict[str, Any]:
    if kind == "artifact":
        return grant_artifact_to_user(tg, ref_id, quantity)
    if kind == "pill":
        return grant_pill_to_user(tg, ref_id, quantity)
    if kind == "talisman":
        return grant_talisman_to_user(tg, ref_id, quantity)
    if kind == "material":
        return grant_material_to_user(tg, ref_id, quantity)
    if kind == "recipe":
        return grant_recipe_to_user(tg, ref_id, source="exploration", obtained_note="秘境所得")
    if kind == "technique":
        return grant_technique_to_user(
            tg,
            ref_id,
            source="exploration",
            obtained_note="秘境所得",
            auto_equip_if_empty=True,
        )
    raise ValueError("不支持的物品类型")


def _get_item_payload(kind: str, ref_id: int) -> dict[str, Any] | None:
    if kind == "artifact":
        return serialize_artifact(get_artifact(ref_id))
    if kind == "pill":
        return serialize_pill(get_pill(ref_id))
    if kind == "talisman":
        return serialize_talisman(get_talisman(ref_id))
    if kind == "material":
        return serialize_material(get_material(ref_id))
    if kind == "technique":
        return serialize_technique(get_technique(ref_id))
    if kind == "recipe":
        recipe = serialize_recipe(get_recipe(ref_id))
        if recipe:
            recipe["result_item"] = _get_item_payload(
                str(recipe.get("result_kind") or ""),
                int(recipe.get("result_ref_id") or 0),
            )
        return recipe
    return None


def _quality_from_item(kind: str, item: dict[str, Any] | None) -> int:
    if not item:
        return 1
    if kind == "material":
        return max(int(item.get("quality_level", 1) or 1), 1)
    if kind == "recipe":
        return _quality_from_item(
            str(item.get("result_kind") or ""),
            _get_item_payload(
                str(item.get("result_kind") or ""),
                int(item.get("result_ref_id") or 0),
            ),
        )
    if kind in {"artifact", "talisman", "pill", "technique"}:
        if item.get("rarity_level") is not None:
            return max(int(item.get("rarity_level") or 1), 1)
        return max(RARITY_LEVEL_MAP.get(item.get("rarity") or "凡品", 1), 1)
    return 1


def _exploration_drop_weight_rules() -> dict[str, int]:
    defaults = DEFAULT_SETTINGS["exploration_drop_weight_rules"]
    raw = get_xiuxian_settings().get("exploration_drop_weight_rules", defaults)
    raw = raw if isinstance(raw, dict) else {}

    def pick(key: str, minimum: int) -> int:
        try:
            value = int(raw.get(key, defaults[key]))
        except (TypeError, ValueError):
            value = int(defaults[key])
        return max(value, minimum)

    return {
        "material_divine_sense_divisor": pick("material_divine_sense_divisor", 1),
        "high_quality_threshold": min(pick("high_quality_threshold", 1), max(RARITY_LEVEL_MAP.values())),
        "high_quality_fortune_divisor": pick("high_quality_fortune_divisor", 1),
        "high_quality_root_level_start": pick("high_quality_root_level_start", 0),
    }


def _craft_target_quality_by_material() -> dict[int, int]:
    recipe_quality_map: dict[int, int] = {}
    for recipe in list_recipes(enabled_only=True):
        result_kind = str(recipe.get("result_kind") or "")
        result_ref_id = int(recipe.get("result_ref_id") or 0)
        result_quality = _quality_from_item(result_kind, _get_item_payload(result_kind, result_ref_id))
        if result_quality <= 0:
            continue
        for ingredient in list_recipe_ingredients(int(recipe.get("id") or 0)):
            material_id = int(ingredient.get("material_id") or 0)
            if material_id <= 0:
                continue
            recipe_quality_map[material_id] = max(recipe_quality_map.get(material_id, 0), result_quality)
    return recipe_quality_map


def _drop_effective_quality(
    drop: dict[str, Any],
    item_payload: dict[str, Any] | None,
    recipe_quality_map: dict[int, int],
) -> int:
    kind = str(drop.get("reward_kind") or "")
    ref_id = int(drop.get("reward_ref_id") or 0)
    quality = _quality_from_item(kind, item_payload)
    if kind == "material" and ref_id > 0:
        quality = max(quality, int(recipe_quality_map.get(ref_id) or 0))
    return max(quality, 1)


def _scene_quality_level(
    drops: list[dict[str, Any]],
    recipe_quality_map: dict[int, int],
) -> int:
    highest = 1
    for drop in drops:
        if not int(drop.get("reward_ref_id") or 0):
            continue
        item_payload = _get_item_payload(str(drop.get("reward_kind") or ""), int(drop.get("reward_ref_id") or 0))
        highest = max(highest, _drop_effective_quality(drop, item_payload, recipe_quality_map))
    return highest


def _base_drop_success_rate(quality_level: int) -> int:
    return {
        1: 58,
        2: 46,
        3: 34,
        4: 24,
        5: 16,
        6: 10,
        7: 6,
    }.get(max(int(quality_level or 1), 1), 6)


def _drop_success_rate(
    quality_level: int,
    *,
    duration: int,
    max_minutes: int,
    fortune: int,
    divine_sense: int,
    scene_quality: int,
    combat_power: int,
    min_combat_power: int,
    requirements_met: bool,
) -> int:
    duration_ratio = max(min(float(duration) / float(max(max_minutes, 1)), 1.0), 0.05)
    rate = _base_drop_success_rate(quality_level)
    rate += int(round(duration_ratio * 28))
    rate += max(fortune - 10, 0) // 4
    rate += max(divine_sense - 10, 0) // 5
    rate -= max(scene_quality - quality_level, 0) * 3
    power_gap = max(int(min_combat_power or 0) - max(int(combat_power or 0), 0), 0)
    if power_gap > 0:
        gap_ratio = power_gap / max(int(min_combat_power or 0), 1)
        rate -= 12 + min(int(round(gap_ratio * 28)), 20)
    elif requirements_met:
        power_surplus = max(int(combat_power or 0) - max(int(min_combat_power or 0), 0), 0)
        surplus_ratio = power_surplus / max(int(min_combat_power or 0), 1) if int(min_combat_power or 0) > 0 else 1.0
        rate += 14 + min(int(round(surplus_ratio * 22)), 22)
        rate = max(rate, 72 + min(int(round(surplus_ratio * 10)), 12))
    return max(min(rate, 95), 3)


def sync_scene_with_drops_by_name(
    *,
    name: str,
    description: str = "",
    image_url: str = "",
    max_minutes: int = 60,
    min_realm_stage: str | None = None,
    min_realm_layer: int = 1,
    min_combat_power: int = 0,
    event_pool: list[dict[str, Any]] | list[str] | None = None,
    drops: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    legacy_service = _legacy_service()
    payload = {
        "name": str(name or "").strip(),
        "description": str(description or "").strip(),
        "image_url": str(image_url or "").strip(),
        "max_minutes": max(min(int(max_minutes or 60), 60), 1),
        "min_realm_stage": (
            legacy_service.normalize_realm_stage(min_realm_stage)
            if min_realm_stage
            else None
        ),
        "min_realm_layer": max(int(min_realm_layer or 1), 1),
        "min_combat_power": max(int(min_combat_power or 0), 0),
        "event_pool": event_pool or [],
        "enabled": True,
    }
    with Session() as session:
        scene = session.query(XiuxianScene).filter(XiuxianScene.name == payload["name"]).first()
        if scene is None:
            scene = XiuxianScene(**payload)
            session.add(scene)
            session.commit()
            session.refresh(scene)
        else:
            scene.description = payload["description"]
            scene.image_url = payload["image_url"] or None
            scene.max_minutes = payload["max_minutes"]
            scene.min_realm_stage = payload["min_realm_stage"]
            scene.min_realm_layer = payload["min_realm_layer"]
            scene.min_combat_power = payload["min_combat_power"]
            scene.event_pool = payload["event_pool"]
            scene.enabled = True
            scene.updated_at = utcnow()
            session.commit()
            session.refresh(scene)
        session.query(XiuxianSceneDrop).filter(XiuxianSceneDrop.scene_id == scene.id).delete()
        for drop in drops or []:
            session.add(
                XiuxianSceneDrop(
                    scene_id=scene.id,
                    reward_kind=str(drop.get("reward_kind") or "material"),
                    reward_ref_id=drop.get("reward_ref_id"),
                    quantity_min=max(int(drop.get("quantity_min", 1) or 1), 1),
                    quantity_max=max(int(drop.get("quantity_max", drop.get("quantity_min", 1)) or 1), 1),
                    weight=max(int(drop.get("weight", 1) or 1), 1),
                    stone_reward=max(int(drop.get("stone_reward", 0) or 0), 0),
                    event_text=str(drop.get("event_text") or "").strip() or None,
                )
            )
        scene_id = int(scene.id)
        session.commit()
    scene_payload = serialize_scene(get_scene(scene_id))
    scene_payload["drops"] = list_scene_drops(scene_id)
    return scene_payload


def create_scene_with_drops(
    *,
    name: str,
    description: str = "",
    image_url: str = "",
    max_minutes: int = 60,
    min_realm_stage: str | None = None,
    min_realm_layer: int = 1,
    min_combat_power: int = 0,
    event_pool: list[dict[str, Any]] | list[str] | None = None,
    drops: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    legacy_service = _legacy_service()
    scene = create_scene(
        name=name,
        description=description,
        image_url=image_url,
        max_minutes=max(min(int(max_minutes or 60), 60), 1),
        min_realm_stage=(
            legacy_service.normalize_realm_stage(min_realm_stage)
            if min_realm_stage
            else None
        ),
        min_realm_layer=max(int(min_realm_layer or 1), 1),
        min_combat_power=max(int(min_combat_power or 0), 0),
        event_pool=event_pool or [],
        enabled=True,
    )
    for drop in drops or []:
        create_scene_drop(
            scene_id=scene["id"],
            reward_kind=str(drop.get("reward_kind") or "material"),
            reward_ref_id=drop.get("reward_ref_id"),
            quantity_min=max(int(drop.get("quantity_min", 1) or 1), 1),
            quantity_max=max(int(drop.get("quantity_max", drop.get("quantity_min", 1)) or 1), 1),
            weight=max(int(drop.get("weight", 1) or 1), 1),
            stone_reward=max(int(drop.get("stone_reward", 0) or 0), 0),
            event_text=str(drop.get("event_text") or "").strip() or None,
        )
    scene["drops"] = list_scene_drops(scene["id"])
    return scene


def patch_scene_with_drops(
    scene_id: int,
    *,
    name: str,
    description: str = "",
    image_url: str = "",
    max_minutes: int = 60,
    min_realm_stage: str | None = None,
    min_realm_layer: int = 1,
    min_combat_power: int = 0,
    event_pool: list[dict[str, Any]] | list[str] | None = None,
    drops: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    legacy_service = _legacy_service()
    with Session() as session:
        scene = session.query(XiuxianScene).filter(XiuxianScene.id == scene_id).first()
        if scene is None:
            raise ValueError("场景不存在")
        scene.name = str(name or "").strip()
        scene.description = str(description or "").strip()
        scene.image_url = str(image_url or "").strip() or None
        scene.max_minutes = max(min(int(max_minutes or 60), 60), 1)
        scene.min_realm_stage = (
            legacy_service.normalize_realm_stage(min_realm_stage)
            if min_realm_stage
            else None
        )
        scene.min_realm_layer = max(int(min_realm_layer or 1), 1)
        scene.min_combat_power = max(int(min_combat_power or 0), 0)
        scene.event_pool = event_pool or []
        scene.enabled = True
        scene.updated_at = utcnow()
        session.query(XiuxianSceneDrop).filter(XiuxianSceneDrop.scene_id == scene.id).delete()
        for drop in drops or []:
            session.add(
                XiuxianSceneDrop(
                    scene_id=scene.id,
                    reward_kind=str(drop.get("reward_kind") or "material"),
                    reward_ref_id=drop.get("reward_ref_id"),
                    quantity_min=max(int(drop.get("quantity_min", 1) or 1), 1),
                    quantity_max=max(int(drop.get("quantity_max", drop.get("quantity_min", 1)) or 1), 1),
                    weight=max(int(drop.get("weight", 1) or 1), 1),
                    stone_reward=max(int(drop.get("stone_reward", 0) or 0), 0),
                    event_text=str(drop.get("event_text") or "").strip() or None,
                )
            )
        session.commit()
    scene_payload = serialize_scene(get_scene(scene_id))
    scene_payload["drops"] = list_scene_drops(scene_id)
    return scene_payload


def _weighted_random_choice(rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not rows:
        return None
    total_weight = sum(max(int(item.get("weight") or 0), 1) for item in rows)
    cursor = random.randint(1, max(total_weight, 1))
    current = 0
    for item in rows:
        current += max(int(item.get("weight") or 0), 1)
        if cursor <= current:
            return item
    return rows[-1]


def _recipe_like_bonus_item(kind: str | None, ref_id: int | None) -> bool:
    if kind in {"recipe", "technique"}:
        return True
    item = _get_item_payload(str(kind or ""), int(ref_id or 0)) if kind and ref_id else None
    name = str((item or {}).get("name") or "")
    return "谱" in name or "残页" in name or "图录" in name


def _build_exploration_outcome(
    scene: dict[str, Any],
    chosen_drop: dict[str, Any],
    fortune: int,
    divine_sense: int,
    karma: int,
    duration: int,
    scene_quality: int = 1,
) -> dict[str, Any]:
    max_minutes = max(int(scene.get("max_minutes") or 60), 1)
    duration_ratio = max(min(float(duration) / float(max_minutes), 1.0), 0.05)
    effort_factor = 0.45 + duration_ratio * 1.55
    event = _weighted_random_choice(scene.get("event_pool") or []) or {}
    stone_bonus = 0
    stone_loss = 0
    bonus_reward = None
    if event:
        stone_bonus_min = max(int(event.get("stone_bonus_min") or 0), 0)
        stone_bonus_max = max(int(event.get("stone_bonus_max") or stone_bonus_min), stone_bonus_min)
        if stone_bonus_max > 0:
            stone_bonus = int(round(random.randint(stone_bonus_min, stone_bonus_max) * effort_factor))
        stone_loss_min = max(int(event.get("stone_loss_min") or 0), 0)
        stone_loss_max = max(int(event.get("stone_loss_max") or stone_loss_min), stone_loss_min)
        if stone_loss_max > 0:
            mitigation = max(fortune // 4 + divine_sense // 6, 0)
            danger_factor = 1 + max(scene_quality - 1, 0) * 0.18
            stone_loss = max(int(round(random.randint(stone_loss_min, stone_loss_max) * effort_factor * danger_factor)) - mitigation, 0)
        bonus_reward_kind = event.get("bonus_reward_kind")
        bonus_reward_ref_id = int(event.get("bonus_reward_ref_id") or 0)
        bonus_chance = max(min(int(event.get("bonus_chance") or 0) + max(karma - 10, 0) // 6, 100), 0)
        if bonus_reward_kind and bonus_reward_ref_id > 0 and roll_probability_percent(bonus_chance)["success"]:
            bonus_quantity_min = max(int(event.get("bonus_quantity_min") or 1), 1)
            bonus_quantity_max = max(int(event.get("bonus_quantity_max") or bonus_quantity_min), bonus_quantity_min)
            raw_quantity = random.randint(bonus_quantity_min, bonus_quantity_max)
            bonus_reward = {
                "kind": bonus_reward_kind,
                "ref_id": bonus_reward_ref_id,
                "quantity": max(int(round(raw_quantity * (0.6 + duration_ratio * 1.2))), 1),
                "is_recipe_like": _recipe_like_bonus_item(bonus_reward_kind, bonus_reward_ref_id),
            }
    return {
        "event": event,
        "stone_bonus": stone_bonus,
        "stone_loss": stone_loss,
        "bonus_reward": bonus_reward,
        "event_text": _join_scene_fragments(
            event.get("name"),
            chosen_drop.get("event_text"),
            event.get("description"),
        ),
        "duration_minutes": int(duration),
        "duration_ratio": round(duration_ratio, 4),
        "scene_quality_level": max(int(scene_quality or 1), 1),
    }


def _get_active_exploration(tg: int) -> dict[str, Any] | None:
    with Session() as session:
        row = (
            session.query(XiuxianExploration)
            .filter(XiuxianExploration.tg == tg, XiuxianExploration.claimed.is_(False))
            .order_by(XiuxianExploration.id.desc())
            .first()
        )
        return serialize_exploration(row)


def _scene_requirement_state(
    profile: dict[str, Any],
    scene: dict[str, Any],
    combat_power: int,
) -> dict[str, Any]:
    current_stage = realm_index(profile.get("realm_stage"))
    current_stage_name = profile.get("realm_stage") or "炼气"
    current_layer = int(profile.get("realm_layer") or 1)
    required_stage_name = scene.get("min_realm_stage")
    required_stage = realm_index(required_stage_name) if required_stage_name else None
    required_layer = max(int(scene.get("min_realm_layer") or 1), 1)
    min_power = max(int(scene.get("min_combat_power") or 0), 0)

    reasons: list[str] = []
    realm_gap_score = 0
    realm_surplus_score = 0
    if required_stage is not None:
        stage_gap = required_stage - current_stage
        if stage_gap > 0:
            realm_gap_score = stage_gap * 9 + max(required_layer - 1, 0)
            reasons.append(
                f"当前境界 {current_stage_name}{current_layer}层，低于秘境要求 {required_stage_name}{required_layer}层"
            )
        elif current_stage == required_stage and current_layer < required_layer:
            realm_gap_score = required_layer - current_layer
            reasons.append(
                f"当前境界 {current_stage_name}{current_layer}层，低于秘境要求 {required_stage_name}{required_layer}层"
            )
        else:
            realm_surplus_score = max((current_stage - required_stage) * 9 + (current_layer - required_layer), 0)

    power_gap = max(min_power - max(int(combat_power or 0), 0), 0)
    power_gap_ratio = (power_gap / max(min_power, 1)) if min_power > 0 else 0.0
    power_surplus = max(max(int(combat_power or 0), 0) - min_power, 0)
    power_surplus_ratio = (power_surplus / max(min_power, 1)) if min_power > 0 else 0.0
    if power_gap > 0:
        reasons.append(f"当前战力 {combat_power}，低于秘境要求 {min_power}")

    risk_score = 0.0
    if realm_gap_score > 0:
        risk_score += 36 + min(realm_gap_score * 6.5, 34)
    elif required_stage is not None:
        risk_score += max(12 - min(realm_surplus_score * 2.6, 12), 0)
    if power_gap > 0:
        risk_score += 24 + min(power_gap_ratio * 46, 34)
    elif min_power > 0:
        risk_score += max(10 - min(power_surplus_ratio * 18, 10), 0)
    if not reasons:
        risk_score -= 18
    survival_offset = (
        max(int(profile.get("willpower") or 0) - 10, 0) * 0.9
        + max(int(profile.get("karma") or 0) - 10, 0) * 0.65
        + max(int(profile.get("fortune") or 0) - 10, 0) * 0.35
    )
    risk_score -= survival_offset
    if len(reasons) >= 2:
        risk_score += 8
    risk_percent = max(min(int(round(risk_score)), 95), 0)
    risk_level, risk_label = _risk_level_label(risk_percent)
    item_loss_risk = 0 if risk_percent < 20 else max(min(int(round(risk_percent * 0.55 + max(realm_gap_score - 1, 0) * 4)), 85), 8)
    cultivation_loss_risk = 0 if risk_percent < 10 else min(int(round(risk_percent * 0.42)), 70)
    death_chance = 0 if risk_percent <= 0 else min(max(int(round(risk_percent * 0.82 + (18 if reasons else 0))), 3), 95)
    requirement_rows = []
    if required_stage_name:
        requirement_rows.append(f"境界至少 {required_stage_name}{required_layer}层")
    if min_power > 0:
        requirement_rows.append(f"战力至少 {min_power}")
    requirement_summary = "；".join(requirement_rows) if requirement_rows else "无硬性门槛"
    safe_note = "当前境界与战力已能压住此地反噬，适合稳定刷取材料与功法。" if risk_percent <= 5 else ""
    item_loss_warning = ""
    if item_loss_risk > 0:
        item_loss_warning = f"若强闯失手，存在掉落未绑定法宝与折损修为的风险。"
    return {
        "min_realm_stage": required_stage_name,
        "min_realm_layer": required_layer,
        "min_combat_power": min_power,
        "combat_power": max(int(combat_power or 0), 0),
        "current_realm_display": f"{current_stage_name}{current_layer}层",
        "requirement_summary": requirement_summary,
        "risk_reasons": reasons,
        "risk_percent": risk_percent,
        "risk_level": risk_level,
        "risk_label": risk_label,
        "item_loss_risk": item_loss_risk,
        "cultivation_loss_risk": cultivation_loss_risk,
        "item_loss_warning": item_loss_warning,
        "safe_note": safe_note,
        "death_chance": death_chance,
        "realm_gap_score": realm_gap_score,
        "realm_surplus_score": realm_surplus_score,
        "power_gap": power_gap,
        "power_gap_ratio": round(power_gap_ratio, 4),
        "power_surplus": power_surplus,
        "power_surplus_ratio": round(power_surplus_ratio, 4),
        "requirements_met": not reasons,
    }


def _apply_cultivation_loss(stage: str, layer: int, cultivation: int, loss: int) -> tuple[int, int, int]:
    legacy_service = _legacy_service()
    current_layer = max(int(layer or 1), 1)
    current_cultivation = max(int(cultivation or 0), 0)
    remaining_loss = max(int(loss or 0), 0)
    threshold = legacy_service.cultivation_threshold(stage, current_layer)
    current_cultivation = min(current_cultivation, threshold)

    def total_progress(target_layer: int, target_cultivation: int) -> int:
        total = max(int(target_cultivation or 0), 0)
        for current in range(1, max(int(target_layer or 1), 1)):
            total += legacy_service.cultivation_threshold(stage, current)
        return total

    before_total = total_progress(current_layer, current_cultivation)

    while remaining_loss > 0:
        if current_cultivation >= remaining_loss:
            current_cultivation -= remaining_loss
            remaining_loss = 0
            break
        remaining_loss -= current_cultivation
        if current_layer <= 1:
            current_cultivation = 0
            remaining_loss = 0
            break
        current_layer -= 1
        current_cultivation = legacy_service.cultivation_threshold(stage, current_layer)

    actual_loss = max(before_total - total_progress(current_layer, current_cultivation), 0)
    return current_layer, current_cultivation, actual_loss


def _drop_random_unbound_artifacts(tg: int, count: int) -> list[dict[str, Any]]:
    amount = max(int(count or 0), 0)
    if amount <= 0:
        return []

    dropped: list[dict[str, Any]] = []
    with Session() as session:
        profile = session.query(XiuxianProfile).filter(XiuxianProfile.tg == tg).with_for_update().first()
        if profile is None:
            return []

        for _ in range(amount):
            owner_rows = (
                session.query(XiuxianArtifactInventory)
                .filter(XiuxianArtifactInventory.tg == tg)
                .with_for_update()
                .all()
            )
            equipped_rows = (
                session.query(XiuxianEquippedArtifact)
                .filter(XiuxianEquippedArtifact.tg == tg)
                .order_by(XiuxianEquippedArtifact.slot.desc(), XiuxianEquippedArtifact.id.desc())
                .with_for_update()
                .all()
            )
            equipped_count_map: dict[int, int] = {}
            for equipped_row in equipped_rows:
                artifact_id = int(equipped_row.artifact_id or 0)
                equipped_count_map[artifact_id] = equipped_count_map.get(artifact_id, 0) + 1

            weighted_rows: list[tuple[int, int]] = []
            for row in owner_rows:
                total_quantity = int(row.quantity or 0)
                bound_quantity = max(min(int(row.bound_quantity or 0), total_quantity), 0)
                protected_quantity = min(total_quantity, bound_quantity + equipped_count_map.get(int(row.artifact_id), 0))
                droppable_quantity = max(total_quantity - protected_quantity, 0)
                if droppable_quantity > 0:
                    weighted_rows.append((int(row.artifact_id), droppable_quantity))
            if not weighted_rows:
                break

            weighted_ids = [artifact_id for artifact_id, quantity in weighted_rows for _ in range(quantity)]
            artifact_id = random.choice(weighted_ids)
            row = next((item for item in owner_rows if int(item.artifact_id) == artifact_id), None)
            if row is None:
                continue

            row.quantity = max(int(row.quantity or 0) - 1, 0)
            row.bound_quantity = max(min(int(row.bound_quantity or 0), int(row.quantity or 0)), 0)
            row.updated_at = utcnow()

            if int(row.quantity or 0) <= 0:
                session.delete(row)

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

            artifact = session.query(XiuxianArtifact).filter(XiuxianArtifact.id == artifact_id).first()
            dropped.append(
                {
                    "artifact": serialize_artifact(artifact),
                    "was_equipped": False,
                }
            )

        session.commit()
    return dropped


def start_exploration_for_user(tg: int, scene_id: int, minutes: int) -> dict[str, Any]:
    legacy_service = _legacy_service()
    bundle = legacy_service.serialize_full_profile(tg)
    profile = bundle.get("profile") or {}
    if not profile or not profile.get("consented"):
        raise ValueError("你还没有踏入仙途")
    if bundle.get("capabilities", {}).get("gender_required"):
        raise ValueError(str(bundle.get("capabilities", {}).get("gender_lock_reason") or "请先设置性别。"))
    active = _get_active_exploration(tg)
    if active and not active.get("claimed"):
        raise ValueError("你还有未结算的探索")
    scene = serialize_scene(get_scene(scene_id))
    if not scene or not scene.get("enabled"):
        raise ValueError("场景不存在")

    requirement_state = _scene_requirement_state(
        profile,
        scene,
        int(bundle.get("combat_power") or 0),
    )
    duration = max(min(int(minutes or 60), int(scene.get("max_minutes") or 60), 60), 1)
    drops = list_scene_drops(scene_id)
    if not drops:
        raise ValueError("该场景尚未配置掉落")
    divine_sense = int(profile.get("divine_sense") or 0)
    fortune = int(profile.get("fortune") or 0)
    karma = int(profile.get("karma") or 0)
    root_quality_level = int(profile.get("root_quality_level") or 1)
    weight_rules = _exploration_drop_weight_rules()
    recipe_quality_map = _craft_target_quality_by_material()
    scene_quality = _scene_quality_level(drops, recipe_quality_map)
    weighted = []
    for drop in drops:
        item_payload = (
            _get_item_payload(str(drop.get("reward_kind") or ""), int(drop.get("reward_ref_id") or 0))
            if drop.get("reward_ref_id")
            else None
        )
        reward_quality = _drop_effective_quality(drop, item_payload, recipe_quality_map)
        extra_weight = 0
        if str(drop.get("reward_kind") or "") == "material":
            extra_weight += max(divine_sense - 10, 0) // int(weight_rules["material_divine_sense_divisor"])
        if reward_quality >= int(weight_rules["high_quality_threshold"]):
            extra_weight += (
                max(fortune - 10, 0) // int(weight_rules["high_quality_fortune_divisor"])
                + max(root_quality_level - int(weight_rules["high_quality_root_level_start"]), 0)
            )
        if _recipe_like_bonus_item(str(drop.get("reward_kind") or ""), int(drop.get("reward_ref_id") or 0)):
            extra_weight += max(karma - 10, 0) // 6
        weighted.extend([drop] * max(int(drop.get("weight") or 1) + extra_weight, 1))
    chosen = random.choice(weighted)
    duration_ratio = max(min(float(duration) / float(max(int(scene.get("max_minutes") or 60), 1)), 1.0), 0.05)
    base_quantity = random.randint(
        int(chosen.get("quantity_min") or 1),
        int(chosen.get("quantity_max") or chosen.get("quantity_min") or 1),
    )
    quantity = max(int(round(base_quantity * (0.55 + duration_ratio * 1.25))), 1)
    base_stone_reward = max(int(chosen.get("stone_reward", 0) or 0), 0)
    scaled_stone_reward = int(round(base_stone_reward * (0.45 + duration_ratio * 1.55)))
    chosen_payload = (
        _get_item_payload(str(chosen.get("reward_kind") or ""), int(chosen.get("reward_ref_id") or 0))
        if chosen.get("reward_ref_id")
        else None
    )
    effective_quality = _drop_effective_quality(chosen, chosen_payload, recipe_quality_map)
    drop_success_rate = _drop_success_rate(
        effective_quality,
        duration=duration,
        max_minutes=max(int(scene.get("max_minutes") or 60), 1),
        fortune=fortune,
        divine_sense=divine_sense,
        scene_quality=scene_quality,
        combat_power=int(bundle.get("combat_power") or 0),
        min_combat_power=int(requirement_state.get("min_combat_power") or 0),
        requirements_met=bool(requirement_state.get("requirements_met")),
    )
    drop_succeeded = roll_probability_percent(drop_success_rate)["success"]
    if not drop_succeeded:
        quantity = 0
        scaled_stone_reward = int(round(scaled_stone_reward * 0.55))
    outcome = _build_exploration_outcome(scene, chosen, fortune, divine_sense, karma, duration, scene_quality=scene_quality)
    outcome["drop_quality_level"] = effective_quality
    outcome["drop_success_rate"] = drop_success_rate
    outcome["drop_succeeded"] = drop_succeeded
    event_text = outcome.get("event_text") or chosen.get("event_text") or ""
    if not drop_succeeded:
        miss_note = "你在秘境中有所收获，却没能真正带出那件材料。"
        event_text = _join_scene_fragments(event_text, miss_note)

    death_chance = int(requirement_state.get("death_chance") or 0)
    death_chance = min(death_chance + max(scene_quality - 3, 0) * 4, 95)
    fatal_outcome = None
    if death_chance > 0:
        death_roll = random.randint(1, 100)
        died = death_roll <= death_chance
        outcome["death_risk"] = {
            "chance": death_chance,
            "roll": death_roll,
            "died": died,
            "reasons": list(requirement_state.get("risk_reasons") or []),
        }
        if died:
            fatal_outcome = {
                "died": True,
                "reasons": list(requirement_state.get("risk_reasons") or []),
                "stone_loss_percent": random.randint(18, 42),
                "cultivation_loss_percent": random.randint(12, 28),
                "artifact_drop_count": 1 + (1 if death_chance >= 85 else 0),
            }
            outcome["fatal_outcome"] = fatal_outcome
        else:
            outcome["risk_note"] = _join_scene_fragments(
                requirement_state.get("item_loss_warning"),
                "你此次硬着头皮闯入高危秘境，侥幸活着撑了下来。",
            )
    outcome["requirement_state"] = requirement_state

    with Session() as session:
        exploration = XiuxianExploration(
            tg=tg,
            scene_id=scene_id,
            started_at=utcnow(),
            end_at=utcnow() + timedelta(minutes=duration),
            claimed=False,
            reward_kind=chosen.get("reward_kind") if drop_succeeded else None,
            reward_ref_id=chosen.get("reward_ref_id") if drop_succeeded else None,
            reward_quantity=quantity,
            stone_reward=scaled_stone_reward,
            event_text=event_text or None,
            outcome_payload=outcome,
        )
        session.add(exploration)
        session.commit()
        session.refresh(exploration)
        scene["requirement_state"] = requirement_state
        return {"scene": scene, "exploration": serialize_exploration(exploration)}


def claim_exploration_for_user(tg: int, exploration_id: int) -> dict[str, Any]:
    exploration_payload: dict[str, Any] | None = None
    reward_kind = None
    reward_ref_id = 0
    reward_quantity = 0
    stone_reward = 0
    outcome: dict[str, Any] = {}
    with Session() as session:
        exploration = (
            session.query(XiuxianExploration)
            .filter(XiuxianExploration.id == exploration_id, XiuxianExploration.tg == tg)
            .with_for_update()
            .first()
        )
        if exploration is None:
            raise ValueError("探索记录不存在")
        if exploration.claimed:
            raise ValueError("该探索已领取过")
        if exploration.end_at > utcnow():
            raise ValueError("探索尚未结束")

        outcome = dict(exploration.outcome_payload or {})
        fatal_outcome = outcome.get("fatal_outcome") if isinstance(outcome.get("fatal_outcome"), dict) else None
        bonus_payload = outcome.get("bonus_reward") if isinstance(outcome.get("bonus_reward"), dict) else None
        if not fatal_outcome:
            technique_rewards = []
            if exploration.reward_kind == "technique" and exploration.reward_ref_id:
                technique_rewards.append(int(exploration.reward_ref_id))
            if (
                bonus_payload
                and str(bonus_payload.get("kind") or "") == "technique"
                and int(bonus_payload.get("ref_id") or 0) > 0
            ):
                technique_rewards.append(int(bonus_payload.get("ref_id")))
            if technique_rewards:
                profile_obj = session.query(XiuxianProfile).filter(XiuxianProfile.tg == tg).first()
                capacity = normalize_technique_capacity(getattr(profile_obj, "technique_capacity", None))
                owned_ids = {
                    int(row[0] or 0)
                    for row in session.query(XiuxianUserTechnique.technique_id)
                    .filter(XiuxianUserTechnique.tg == tg)
                    .all()
                    if int(row[0] or 0) > 0
                }
                incoming_new = {
                    technique_id
                    for technique_id in technique_rewards
                    if technique_id not in owned_ids
                }
                if len(owned_ids) + len(incoming_new) > capacity:
                    raise ValueError(
                        f"当前可参悟功法数量已满，上限为 {capacity}，请先让管理员调整后再领取该机缘。"
                    )

        reward_kind = exploration.reward_kind
        reward_ref_id = int(exploration.reward_ref_id or 0)
        reward_quantity = int(exploration.reward_quantity or 0)
        stone_reward = int(exploration.stone_reward or 0)
        exploration.claimed = True
        exploration.updated_at = utcnow()
        session.commit()
        session.refresh(exploration)
        exploration_payload = serialize_exploration(exploration)

    legacy_service = _legacy_service()
    profile_row = legacy_service._repair_profile_realm_state(tg) or get_profile(tg, create=False)
    profile = serialize_profile(profile_row) if profile_row is not None else None
    profile_bundle = legacy_service.serialize_full_profile(tg)
    if profile_bundle.get("capabilities", {}).get("gender_required"):
        raise ValueError(str(profile_bundle.get("capabilities", {}).get("gender_lock_reason") or "请先设置性别。"))
    fatal_outcome = outcome.get("fatal_outcome") if isinstance(outcome.get("fatal_outcome"), dict) else None
    if fatal_outcome:
        if profile is None:
            raise ValueError("用户不存在")
        current_stone = max(int(get_shared_spiritual_stone_total(tg) or 0), 0)
        planned_stone_loss = max(
            int(round(current_stone * int(fatal_outcome.get("stone_loss_percent") or 0) / 100)),
            12 if current_stone > 0 else 0,
        )
        actual_stone_loss = min(current_stone, planned_stone_loss)

        stage = legacy_service.normalize_realm_stage(profile.get("realm_stage") or legacy_service.FIRST_REALM_STAGE)
        current_layer = int(profile.get("realm_layer") or 1)
        current_cultivation = int(profile.get("cultivation") or 0)
        threshold = legacy_service.cultivation_threshold(stage, current_layer)
        planned_cultivation_loss = max(
            int(round(max(current_cultivation, threshold // 3) * int(fatal_outcome.get("cultivation_loss_percent") or 0) / 100)),
            10,
        )
        next_layer, next_cultivation, actual_cultivation_loss = _apply_cultivation_loss(
            stage,
            current_layer,
            current_cultivation,
            planned_cultivation_loss,
        )
        artifact_losses = _drop_random_unbound_artifacts(
            tg,
            int(fatal_outcome.get("artifact_drop_count") or 0),
        )
        with Session() as session:
            updated = session.query(XiuxianProfile).filter(XiuxianProfile.tg == int(tg)).with_for_update().first()
            if updated is None or not updated.consented:
                raise ValueError("你还没有踏入仙途")
            if actual_stone_loss > 0:
                apply_spiritual_stone_delta(
                    session,
                    tg,
                    -actual_stone_loss,
                    action_text="探索失利损失灵石",
                    enforce_currency_lock=False,
                    allow_dead=False,
                    apply_tribute=False,
                )
            updated.realm_layer = next_layer
            updated.cultivation = next_cultivation
            updated.updated_at = utcnow()
            session.commit()
        updated_profile = (legacy_service.serialize_full_profile(tg) or {}).get("profile")
        death_reasons = list(fatal_outcome.get("reasons") or [])
        reason_text = "；".join(death_reasons) if death_reasons else "误入凶险秘境"
        create_journal(
            tg,
            "explore",
            "探索阵亡",
            f"{reason_text}，损失灵石 {actual_stone_loss}、修为 {actual_cultivation_loss}。",
        )
        return {
            "exploration": exploration_payload,
            "reward_item": None,
            "bonus_reward": None,
            "stone_gain": 0,
            "stone_loss": actual_stone_loss,
            "stone_delta": -actual_stone_loss,
            "cultivation_loss": actual_cultivation_loss,
            "artifact_losses": artifact_losses,
            "profile": updated_profile,
            "death": {
                "died": True,
                "reasons": death_reasons,
                "stone_loss": actual_stone_loss,
                "cultivation_loss": actual_cultivation_loss,
                "artifact_losses": artifact_losses,
            },
            "achievement_unlocks": [],
        }

    reward_item = None
    if reward_kind and reward_ref_id and reward_quantity > 0:
        reward_item = _grant_item_by_kind(tg, reward_kind, reward_ref_id, reward_quantity)

    bonus_payload = outcome.get("bonus_reward") if isinstance(outcome.get("bonus_reward"), dict) else None
    bonus_reward = None
    if (
        bonus_payload
        and bonus_payload.get("kind")
        and int(bonus_payload.get("ref_id") or 0) > 0
        and int(bonus_payload.get("quantity") or 0) > 0
    ):
        bonus_reward = _grant_item_by_kind(
            tg,
            str(bonus_payload.get("kind")),
            int(bonus_payload.get("ref_id")),
            int(bonus_payload.get("quantity")),
        )

    event_stone_bonus = max(int(outcome.get("stone_bonus") or 0), 0)
    event_stone_loss = max(int(outcome.get("stone_loss") or 0), 0)
    current_stone = max(int(get_shared_spiritual_stone_total(tg) or 0), 0)
    actual_stone_loss = min(current_stone, event_stone_loss)
    total_stone_delta = stone_reward + event_stone_bonus - actual_stone_loss
    activity_growth = {"triggered": False, "changes": [], "patch": {}, "chance": 0, "roll": None}
    updated_profile = None
    with Session() as session:
        updated = session.query(XiuxianProfile).filter(XiuxianProfile.tg == tg).with_for_update().first()
        if updated is None or not updated.consented:
            raise ValueError("你还没有踏入仙途")
        if total_stone_delta:
            apply_spiritual_stone_delta(
                session,
                tg,
                total_stone_delta,
                action_text="探索结算灵石",
                enforce_currency_lock=False,
                allow_dead=False,
                apply_tribute=total_stone_delta > 0,
            )
        activity_growth = legacy_service._apply_activity_stat_growth_to_profile_row(
            updated,
            "exploration",
            serialize_profile(updated),
        )
        updated.updated_at = utcnow()
        session.commit()
        session.refresh(updated)
        updated_profile = serialize_profile(updated)
    event_type = str((outcome.get("event") or {}).get("event_type") or "").strip()
    recipe_like_drop = bool(
        bonus_payload and bonus_payload.get("is_recipe_like")
    ) or _recipe_like_bonus_item(reward_kind, reward_ref_id)
    achievement_unlocks = record_exploration_metrics(
        tg,
        event_type=event_type,
        recipe_drop=recipe_like_drop,
    )
    growth_text = ""
    if activity_growth.get("triggered"):
        growth_text = " 属性成长：" + "、".join(
            f"{item['label']} +{item['value']}"
            for item in (activity_growth.get("changes") or [])
        ) + "。"
    create_journal(
        tg,
        "explore",
        "探索结算",
        (
            f"完成探索，灵石变化 {total_stone_delta:+d}。"
            f"{growth_text}"
            f"{' 另得机缘之物。' if bonus_reward else ''}"
        ),
    )
    return {
        "exploration": exploration_payload,
        "reward_item": reward_item,
        "bonus_reward": bonus_reward,
        "stone_gain": stone_reward + event_stone_bonus,
        "stone_loss": actual_stone_loss,
        "stone_delta": total_stone_delta,
        "attribute_growth": activity_growth.get("changes") or [],
        "profile": updated_profile,
        "achievement_unlocks": achievement_unlocks,
    }

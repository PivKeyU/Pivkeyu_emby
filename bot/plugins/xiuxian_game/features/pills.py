from __future__ import annotations

from typing import Any

from bot.sql_helper.sql_xiuxian import (
    consume_user_pill,
    get_pill,
    get_profile,
    normalize_realm_stage,
    serialize_pill,
    serialize_profile,
    upsert_profile,
)
from bot.plugins.xiuxian_game.features.retreat import is_retreating


def _legacy_service():
    from bot.plugins.xiuxian_game import service as legacy_service

    return legacy_service


def resolve_pill_effects(
    profile: dict[str, Any],
    pill: dict[str, Any] | None,
    extra: dict[str, Any] | None = None,
) -> dict[str, float]:
    legacy_service = _legacy_service()
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
            "willpower_bonus": 0.0,
            "charisma_bonus": 0.0,
            "karma_bonus": 0.0,
            "qi_blood_bonus": 0.0,
            "true_yuan_bonus": 0.0,
            "body_movement_bonus": 0.0,
            "root_quality_gain": 0.0,
            "root_quality_floor": 0.0,
        }
    pill_type = pill.get("pill_type")
    multiplier = legacy_service._item_quality_multiplier(pill, "pill")
    base_effect_value = max(float(pill.get("effect_value", 0) or 0) * multiplier, 0.0)
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
        "willpower_bonus": 0.0,
        "charisma_bonus": 0.0,
        "karma_bonus": 0.0,
        "qi_blood_bonus": float(pill.get("qi_blood_bonus", 0) or 0) * multiplier,
        "true_yuan_bonus": float(pill.get("true_yuan_bonus", 0) or 0) * multiplier,
        "body_movement_bonus": float(pill.get("body_movement_bonus", 0) or 0) * multiplier,
        "root_quality_gain": 0.0,
        "root_quality_floor": 0.0,
    }
    if pill_type == "foundation":
        payload["success_rate_bonus"] = base_effect_value
    elif pill_type == "bone":
        payload["bone_bonus"] += base_effect_value
    elif pill_type == "comprehension":
        payload["comprehension_bonus"] += base_effect_value
    elif pill_type == "divine_sense":
        payload["divine_sense_bonus"] += base_effect_value
    elif pill_type == "fortune":
        payload["fortune_bonus"] += base_effect_value
    elif pill_type == "willpower":
        payload["willpower_bonus"] += base_effect_value
    elif pill_type == "charisma":
        payload["charisma_bonus"] += base_effect_value
    elif pill_type == "karma":
        payload["karma_bonus"] += base_effect_value
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
    elif pill_type == "root_refine":
        payload["root_quality_gain"] = base_effect_value
    elif pill_type == "root_remold":
        payload["root_quality_floor"] = base_effect_value
    return payload


def pill_usage_reason(profile_data: dict[str, Any], pill: dict[str, Any]) -> str:
    legacy_service = _legacy_service()
    if not legacy_service.realm_requirement_met(
        profile_data,
        pill.get("min_realm_stage"),
        pill.get("min_realm_layer"),
    ):
        return (
            f"需要达到 {legacy_service.format_realm_requirement(pill.get('min_realm_stage'), pill.get('min_realm_layer'))}"
            " 才能服用这枚丹药。"
        )
    pill_type = str(pill.get("pill_type") or "").strip()
    if pill_type == "foundation":
        return "筑基丹只能在突破时配合使用。"
    if pill_type == "root_refine":
        effects = resolve_pill_effects(profile_data, pill)
        steps = max(int(round(float(effects.get("root_quality_gain", 0) or 0))), 0)
        current_quality = legacy_service._normalized_root_quality(profile_data)
        if current_quality in legacy_service.ROOT_SPECIAL_QUALITIES:
            return "当前已是特殊灵根，无法再用此丹淬炼。"
        if steps <= 0:
            return "这枚淬灵丹没有可生效的品阶。"
        if legacy_service._refined_root_payload(profile_data, steps) is None:
            return "当前灵根品质已达可淬炼上限。"
    if pill_type in legacy_service.ROOT_TRANSFORM_PILL_TYPES:
        if legacy_service._transformed_root_payload(profile_data, pill_type, pill.get("effect_value")) is None:
            return "这枚丹药当前无法改变你的灵根。"
    return ""


def pill_effect_summary(before_profile: dict[str, Any], after_profile: dict[str, Any]) -> str:
    legacy_service = _legacy_service()
    parts: list[str] = []
    before_root = legacy_service.format_root(before_profile)
    after_root = legacy_service.format_root(after_profile)
    before_stage = normalize_realm_stage(before_profile.get("realm_stage") or "炼气")
    after_stage = normalize_realm_stage(after_profile.get("realm_stage") or "炼气")
    before_layer = max(int(before_profile.get("realm_layer") or 1), 1)
    after_layer = max(int(after_profile.get("realm_layer") or 1), 1)

    def cultivation_progress_total(profile: dict[str, Any]) -> int:
        stage = normalize_realm_stage(profile.get("realm_stage") or "炼气")
        layer = max(int(profile.get("realm_layer") or 1), 1)
        cultivation = max(int(profile.get("cultivation") or 0), 0)
        total = cultivation
        for current_layer in range(1, layer):
            total += legacy_service.cultivation_threshold(stage, current_layer)
        return total

    if before_root != after_root:
        parts.append(f"灵根：{before_root} -> {after_root}")
    if before_stage != after_stage or before_layer != after_layer:
        parts.append(f"境界：{before_stage}{before_layer}层 -> {after_stage}{after_layer}层")
    cultivation_delta = (
        cultivation_progress_total(after_profile) - cultivation_progress_total(before_profile)
        if before_stage == after_stage
        else int(after_profile.get("cultivation") or 0) - int(before_profile.get("cultivation") or 0)
    )
    if cultivation_delta:
        parts.append(f"修为 {'+' if cultivation_delta > 0 else ''}{cultivation_delta}")
    for key in (
        "spiritual_stone",
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
        "dan_poison",
    ):
        delta = int(after_profile.get(key) or 0) - int(before_profile.get(key) or 0)
        if not delta:
            continue
        label = {
            "cultivation": "修为",
            "spiritual_stone": "灵石",
            "attack_power": "攻击",
            "defense_power": "防御",
            "dan_poison": "丹毒",
        }.get(key, legacy_service.ATTRIBUTE_LABELS.get(f"{key}_bonus", key))
        parts.append(f"{label} {'+' if delta > 0 else ''}{delta}")
    return "；".join(parts) if parts else "药力已经化开。"


def consume_pill_for_user(tg: int, pill_id: int) -> dict[str, Any]:
    legacy_service = _legacy_service()
    profile = get_profile(tg, create=False)
    if profile is None or not profile.consented:
        raise ValueError("你还没有踏入仙途。")
    if is_retreating(profile):
        raise ValueError("闭关期间无法服用丹药。")
    pill = get_pill(pill_id)
    if pill is None or not pill.enabled:
        raise ValueError("未找到可用的丹药。")
    profile_data = serialize_profile(profile)
    pill_data = serialize_pill(pill)
    usage_reason = pill_usage_reason(profile_data, pill_data)
    if usage_reason:
        raise ValueError(usage_reason)
    if not consume_user_pill(tg, pill_id, 1):
        raise ValueError("你的背包里没有这枚丹药。")

    effects = resolve_pill_effects(profile_data, pill_data)
    bone_resistance = min((float(profile.bone or 0) / 200), 0.45)
    dan_poison = min(
        int(profile.dan_poison or 0) + int(round(float(effects.get("poison_delta", 0) or 0) * (1 - bone_resistance))),
        100,
    )
    cultivation = int(profile.cultivation or 0)
    spiritual_stone = int(profile.spiritual_stone or 0)
    bone = int(profile.bone or 0) + int(round(effects.get("bone_bonus", 0)))
    comprehension = int(profile.comprehension or 0) + int(round(effects.get("comprehension_bonus", 0)))
    divine_sense = int(profile.divine_sense or 0) + int(round(effects.get("divine_sense_bonus", 0)))
    fortune = int(profile.fortune or 0) + int(round(effects.get("fortune_bonus", 0)))
    willpower = int(profile.willpower or 0) + int(round(effects.get("willpower_bonus", 0)))
    charisma = int(profile.charisma or 0) + int(round(effects.get("charisma_bonus", 0)))
    karma = int(profile.karma or 0) + int(round(effects.get("karma_bonus", 0)))
    qi_blood = int(profile.qi_blood or 0) + int(round(effects.get("qi_blood_bonus", 0)))
    true_yuan = int(profile.true_yuan or 0) + int(round(effects.get("true_yuan_bonus", 0)))
    body_movement = int(profile.body_movement or 0) + int(round(effects.get("body_movement_bonus", 0)))
    attack_power = int(profile.attack_power or 0) + int(round(effects.get("attack_bonus", 0)))
    defense_power = int(profile.defense_power or 0) + int(round(effects.get("defense_bonus", 0)))
    root_patch: dict[str, Any] | None = None

    if pill.pill_type == "clear_poison":
        dan_poison = max(dan_poison - int(round(effects.get("clear_poison", effects.get("effect_value", 50)))), 0)
    elif pill.pill_type == "cultivation":
        cultivation += max(int(round(effects.get("cultivation_gain", effects.get("effect_value", 0)))), 0)
    elif pill.pill_type == "stone":
        spiritual_stone += max(int(round(effects.get("stone_gain", effects.get("effect_value", 0)))), 0)
    elif pill.pill_type == "root_refine":
        steps = max(int(round(float(effects.get("root_quality_gain", 0) or 0))), 0)
        root_patch = legacy_service._refined_root_payload(profile_data, steps)
    elif pill.pill_type == "root_remold":
        floor_level = max(int(round(float(effects.get("root_quality_floor", 0) or 0))), 0)
        root_patch = legacy_service._generate_root_payload_with_floor(floor_level)
    elif pill.pill_type in legacy_service.ROOT_TRANSFORM_PILL_TYPES:
        root_patch = legacy_service._transformed_root_payload(
            profile_data,
            pill.pill_type,
            effects.get("effect_value", pill_data.get("effect_value", 0)),
        )

    layer, cultivation, _, _ = legacy_service.apply_cultivation_gain(
        normalize_realm_stage(profile.realm_stage or "炼气"),
        int(profile.realm_layer or 1),
        max(cultivation, 0),
        0,
    )
    updated = upsert_profile(
        tg,
        dan_poison=dan_poison,
        cultivation=cultivation,
        spiritual_stone=max(spiritual_stone, 0),
        bone=bone,
        comprehension=comprehension,
        divine_sense=divine_sense,
        fortune=fortune,
        willpower=willpower,
        charisma=charisma,
        karma=karma,
        qi_blood=qi_blood,
        true_yuan=true_yuan,
        body_movement=body_movement,
        attack_power=attack_power,
        defense_power=defense_power,
        realm_layer=layer,
        **(root_patch or {}),
    )
    bundle = legacy_service.serialize_full_profile(updated.tg)
    return {
        "pill": {**pill_data, "resolved_effects": effects},
        "profile": bundle,
        "summary": pill_effect_summary(profile_data, bundle["profile"]),
    }


def consume_pill_for_user_batch(tg: int, pill_id: int, quantity: int = 1) -> dict[str, Any]:
    legacy_service = _legacy_service()
    requested_quantity = max(int(quantity or 1), 1)

    if requested_quantity == 1:
        result = consume_pill_for_user(tg, pill_id)
        return {
            **result,
            "requested_quantity": 1,
            "used_count": 1,
            "completed": True,
            "stopped_reason": "",
        }

    pill = get_pill(pill_id)
    if pill is None or not pill.enabled:
        raise ValueError("未找到可用的丹药。")

    profile = legacy_service._require_alive_profile_obj(tg, "批量服用丹药")
    if is_retreating(profile):
        raise ValueError("闭关期间无法服用丹药。")

    before_profile = serialize_profile(profile)
    last_result: dict[str, Any] | None = None
    used_count = 0
    stopped_reason = ""

    for _ in range(requested_quantity):
        try:
            last_result = consume_pill_for_user(tg, pill_id)
        except ValueError as exc:
            if used_count <= 0:
                raise
            stopped_reason = str(exc).strip() or "后续已无法继续服用。"
            break
        used_count += 1

    if last_result is None:
        raise ValueError("服用丹药失败，请稍后再试。")

    bundle = last_result.get("profile") or legacy_service.serialize_full_profile(tg)
    after_profile = (bundle or {}).get("profile") or before_profile

    return {
        **last_result,
        "summary": pill_effect_summary(before_profile, after_profile),
        "requested_quantity": requested_quantity,
        "used_count": used_count,
        "completed": used_count >= requested_quantity and not stopped_reason,
        "stopped_reason": stopped_reason,
    }

from __future__ import annotations

import random
from typing import Any

from bot.sql_helper import Session
from bot.sql_helper.sql_xiuxian import (
    ITEM_KIND_LABELS,
    QUALITY_LEVEL_COLORS,
    QUALITY_LEVEL_LABELS,
    XiuxianProfile,
    apply_spiritual_stone_delta,
    assert_profile_alive,
    create_journal,
    get_shared_spiritual_stone_total,
    get_profile,
    grant_artifact_to_user,
    grant_material_to_user,
    grant_pill_to_user,
    grant_talisman_to_user,
    list_artifacts,
    list_materials,
    list_pills,
    list_talismans,
    realm_index,
)


FISHING_SPOTS: dict[str, dict[str, Any]] = {
    "brook": {
        "key": "brook",
        "name": "青溪灵涧",
        "description": "溪流平缓，最适合试竿，常有基础灵材、低阶丹药顺水而来。",
        "cast_cost_stone": 18,
        "min_realm_stage": None,
        "min_realm_layer": 1,
        "quality_min": 1,
        "quality_max": 3,
        "tier_weights": {1: 620, 2: 220, 3: 60},
        "kind_weights": {"material": 1.0, "pill": 0.32, "talisman": 0.12},
        "fortune_scale": 0.35,
    },
    "moon_lake": {
        "key": "moon_lake",
        "name": "寒月灵湖",
        "description": "月华长期沉在湖底，容易勾出带寒性的灵草、丹药与符箓。",
        "cast_cost_stone": 36,
        "min_realm_stage": "筑基",
        "min_realm_layer": 2,
        "quality_min": 1,
        "quality_max": 4,
        "tier_weights": {1: 420, 2: 250, 3: 110, 4: 28},
        "kind_weights": {"material": 0.88, "pill": 0.45, "talisman": 0.24},
        "fortune_scale": 0.48,
    },
    "lava_pool": {
        "key": "lava_pool",
        "name": "火鳞熔潭",
        "description": "潭口热浪翻卷，偶尔会把高热药材、战斗丹与法宝胚胎卷上岸。",
        "cast_cost_stone": 72,
        "min_realm_stage": "筑基",
        "min_realm_layer": 3,
        "quality_min": 2,
        "quality_max": 5,
        "tier_weights": {2: 360, 3: 190, 4: 72, 5: 18},
        "kind_weights": {"material": 0.72, "pill": 0.56, "talisman": 0.18, "artifact": 0.14},
        "fortune_scale": 0.62,
    },
    "star_sea": {
        "key": "star_sea",
        "name": "星渊古海",
        "description": "海眼与星潮相连，重宝虽少却并非绝迹，最吃机缘。",
        "cast_cost_stone": 144,
        "min_realm_stage": "金丹",
        "min_realm_layer": 2,
        "quality_min": 3,
        "quality_max": 7,
        "tier_weights": {3: 290, 4: 170, 5: 70, 6: 16, 7: 3},
        "kind_weights": {"material": 0.65, "pill": 0.42, "talisman": 0.28, "artifact": 0.18},
        "fortune_scale": 0.82,
    },
}

PREVIEW_REWARD_LIMIT = 8


def _legacy_service():
    from bot.plugins.xiuxian_game import service as legacy_service

    return legacy_service


def _shared_reward_pool(settings: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    service = _legacy_service()
    current_settings = settings or service.get_xiuxian_settings()
    return service._configured_gambling_pool(current_settings)


def _weighted_choice(rows: list[dict[str, Any]], weight_key: str = "weight") -> dict[str, Any] | None:
    if not rows:
        return None
    weighted_rows = [(item, max(float(item.get(weight_key) or 0.0), 0.0)) for item in rows]
    total = sum(weight for _, weight in weighted_rows)
    if total <= 0:
        return None
    cursor = random.random() * total
    passed = 0.0
    for item, weight in weighted_rows:
        if weight <= 0:
            continue
        passed += weight
        if cursor <= passed:
            return item
    return weighted_rows[-1][0]


def _grant_item_by_kind(tg: int, kind: str, ref_id: int, quantity: int) -> None:
    if kind == "artifact":
        grant_artifact_to_user(tg, ref_id, quantity)
        return
    if kind == "pill":
        grant_pill_to_user(tg, ref_id, quantity)
        return
    if kind == "talisman":
        grant_talisman_to_user(tg, ref_id, quantity)
        return
    if kind == "material":
        grant_material_to_user(tg, ref_id, quantity)
        return
    raise ValueError("不支持的钓获物类型")


def _quality_meta(level: int) -> dict[str, Any]:
    normalized = max(min(int(level or 1), 7), 1)
    return {
        "level": normalized,
        "label": QUALITY_LEVEL_LABELS.get(normalized, "凡品"),
        "color": QUALITY_LEVEL_COLORS.get(normalized, "#9ca3af"),
    }


def _meets_realm_requirement(profile: XiuxianProfile | dict[str, Any] | None, stage: str | None, layer: int = 1) -> bool:
    if not stage:
        return True
    if profile is None:
        return False
    current_stage = getattr(profile, "realm_stage", None) if not isinstance(profile, dict) else profile.get("realm_stage")
    current_layer = getattr(profile, "realm_layer", None) if not isinstance(profile, dict) else profile.get("realm_layer")
    current_index = realm_index(current_stage)
    target_index = realm_index(stage)
    if current_index != target_index:
        return current_index > target_index
    return max(int(current_layer or 1), 1) >= max(int(layer or 1), 1)


def _spot_requirement_text(spot: dict[str, Any]) -> str:
    stage = str(spot.get("min_realm_stage") or "").strip()
    layer = max(int(spot.get("min_realm_layer") or 1), 1)
    return f"{stage}{layer}层" if stage else "入道后即可"


def _catch_quantity_range(kind: str, quality_level: int) -> tuple[int, int]:
    quality = max(int(quality_level or 1), 1)
    if kind == "material":
        if quality <= 1:
            return 2, 4
        if quality == 2:
            return 1, 3
        if quality <= 4:
            return 1, 2
        return 1, 1
    if kind == "pill" and quality <= 2:
        return 1, 2
    return 1, 1


def _item_quality_level(kind: str, item: dict[str, Any] | None) -> int:
    if not item:
        return 1
    if kind == "material":
        return max(int(item.get("quality_level") or 1), 1)
    return max(int(item.get("rarity_level") or item.get("quality_level") or 1), 1)


def _build_item_lookups() -> dict[str, dict[int, dict[str, Any]]]:
    materials = {int(item["id"]): item for item in list_materials(enabled_only=True) if int(item.get("id") or 0) > 0}
    pills = {int(item["id"]): item for item in list_pills(enabled_only=True) if int(item.get("id") or 0) > 0}
    talismans = {int(item["id"]): item for item in list_talismans(enabled_only=True) if int(item.get("id") or 0) > 0}
    artifacts = {int(item["id"]): item for item in list_artifacts(enabled_only=True) if int(item.get("id") or 0) > 0}
    return {
        "material": materials,
        "pill": pills,
        "talisman": talismans,
        "artifact": artifacts,
    }


def _build_fishing_candidates(
    item_lookups: dict[str, dict[int, dict[str, Any]]],
    *,
    owned_recipe_ids: set[int] | None = None,
    settings: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    _ = owned_recipe_ids
    for entry in _shared_reward_pool(settings):
        if not bool(entry.get("fishing_enabled", entry.get("enabled", True))):
            continue
        kind = str(entry.get("item_kind") or "").strip()
        ref_id = int(entry.get("item_ref_id") or 0)
        if kind not in {"material", "pill", "talisman", "artifact"} or ref_id <= 0:
            continue
        item = (item_lookups.get(kind) or {}).get(ref_id)
        if not item:
            continue
        if kind == "pill" and str(item.get("pill_type") or "").strip() == "foundation":
            continue
        quality_level = _item_quality_level(kind, item)
        quality = _quality_meta(quality_level)
        rows.append(
            {
                "kind": kind,
                "kind_label": ITEM_KIND_LABELS.get(kind, kind),
                "ref_id": ref_id,
                "name": str(item.get("name") or "").strip(),
                "item": item,
                "quality_level": quality_level,
                "quality_label": quality["label"],
                "quality_color": quality["color"],
                "quantity_min": max(int(entry.get("quantity_min") or 1), 1),
                "quantity_max": max(int(entry.get("quantity_max") or entry.get("quantity_min") or 1), max(int(entry.get("quantity_min") or 1), 1)),
                "fishing_weight": max(float(entry.get("fishing_weight", entry.get("base_weight") or 0.0) or 0.0), 0.0),
            }
        )
    return [row for row in rows if row.get("ref_id") and row.get("name") and float(row.get("fishing_weight") or 0.0) > 0]


def _spot_candidates(spot: dict[str, Any], candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    allowed_kinds = set((spot.get("kind_weights") or {}).keys())
    quality_min = max(int(spot.get("quality_min") or 1), 1)
    quality_max = max(int(spot.get("quality_max") or quality_min), quality_min)
    return [
        row
        for row in candidates
        if row.get("kind") in allowed_kinds
        and quality_min <= int(row.get("quality_level") or 0) <= quality_max
    ]


def _tier_weights_for_spot(spot: dict[str, Any], fortune: int, tiers: set[int], settings: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    if not tiers:
        return []
    service = _legacy_service()
    current_settings = settings or service.get_xiuxian_settings()
    quality_rules = service._normalize_fishing_quality_weight_rules(current_settings.get("fishing_quality_weight_rules"))
    available_tiers = sorted(tiers)
    median_tier = available_tiers[len(available_tiers) // 2]
    luck_delta = max(min((int(fortune or 0) - 12) / 20.0, 1.8), -0.35)
    fortune_scale = max(float(spot.get("fortune_scale") or 0), 0.0)
    rows: list[dict[str, Any]] = []
    for tier in available_tiers:
        base_weight = int((spot.get("tier_weights") or {}).get(tier) or 0)
        if base_weight <= 0:
            continue
        shift = int(tier) - int(median_tier)
        multiplier = 1.0 + shift * luck_delta * fortune_scale
        multiplier = max(min(multiplier, 3.4), 0.25)
        quality_multiplier = max(
            float((quality_rules.get(_quality_meta(tier)["label"]) or {}).get("weight_multiplier", 1.0) or 0.0),
            0.0,
        )
        total_weight = base_weight * multiplier * quality_multiplier
        if total_weight <= 0:
            continue
        rows.append({"quality_level": tier, "weight": total_weight})
    return rows


def _kind_weights_for_tier(spot: dict[str, Any], tier_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    available_kinds = {str(row.get("kind") or "") for row in tier_rows if str(row.get("kind") or "")}
    weights = []
    for kind, base_weight in (spot.get("kind_weights") or {}).items():
        if kind not in available_kinds:
            continue
        weights.append(
            {
                "kind": kind,
                "weight": max(int(round(float(base_weight or 0) * 100)), 1),
            }
        )
    return weights


def _preview_rewards(candidates: list[dict[str, Any]], limit: int = PREVIEW_REWARD_LIMIT) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen_names: set[str] = set()
    preferred: list[dict[str, Any]] = []
    for kind in ("artifact", "talisman", "pill", "material"):
        kind_rows = [row for row in candidates if row.get("kind") == kind]
        kind_rows.sort(key=lambda item: (-int(item.get("quality_level") or 0), str(item.get("name") or "")))
        if kind_rows:
            preferred.append(kind_rows[0])
    sorted_rows = sorted(
        candidates,
        key=lambda item: (-int(item.get("quality_level") or 0), str(item.get("kind") or ""), str(item.get("name") or "")),
    )
    for source in preferred + sorted_rows:
        name = str(source.get("name") or "").strip()
        if not name or name in seen_names:
            continue
        rows.append(
            {
                "name": name,
                "kind": source.get("kind"),
                "kind_label": source.get("kind_label"),
                "quality_level": int(source.get("quality_level") or 1),
                "quality_label": source.get("quality_label"),
                "quality_color": source.get("quality_color"),
            }
        )
        seen_names.add(name)
        if len(rows) >= limit:
            break
    return rows


def _build_spot_bundle(spot: dict[str, Any], profile: XiuxianProfile, candidates: list[dict[str, Any]]) -> dict[str, Any]:
    available = _meets_realm_requirement(profile, spot.get("min_realm_stage"), int(spot.get("min_realm_layer") or 1))
    stone_cost = max(int(spot.get("cast_cost_stone") or 0), 0)
    profile_stone = max(int(get_shared_spiritual_stone_total(int(profile.tg or 0)) or 0), 0)
    if available and profile_stone < stone_cost:
        available = False
        available_reason = f"抛竿至少需要 {stone_cost} 灵石"
    elif available:
        available_reason = ""
    else:
        available_reason = f"需达到 {_spot_requirement_text(spot)}"

    tier_weights = _tier_weights_for_spot(spot, int(profile.fortune or 0), {int(row.get("quality_level") or 0) for row in candidates})
    total_weight = sum(max(float(row.get("weight") or 0.0), 0.0) for row in tier_weights)
    odds_preview = [
        {
            **_quality_meta(int(row.get("quality_level") or 1)),
            "chance_percent": round(max(float(row.get("weight") or 0.0), 0.0) * 100 / max(total_weight, 1.0), 1),
        }
        for row in tier_weights
    ]
    quality_min = max(int(spot.get("quality_min") or 1), 1)
    quality_max = max(int(spot.get("quality_max") or quality_min), quality_min)
    return {
        "key": spot["key"],
        "name": spot["name"],
        "description": spot["description"],
        "cast_cost_stone": stone_cost,
        "min_realm_stage": spot.get("min_realm_stage"),
        "min_realm_layer": int(spot.get("min_realm_layer") or 1),
        "requirement_text": _spot_requirement_text(spot),
        "quality_band_label": f"{QUALITY_LEVEL_LABELS.get(quality_min, '凡品')} - {QUALITY_LEVEL_LABELS.get(quality_max, '凡品')}",
        "kind_labels": [ITEM_KIND_LABELS.get(kind, kind) for kind in (spot.get("kind_weights") or {}).keys()],
        "available": bool(available and candidates),
        "available_reason": available_reason if candidates else "当前没有可从该钓场钓出的物品",
        "candidate_count": len(candidates),
        "reward_preview": _preview_rewards(candidates),
        "odds_preview": odds_preview,
    }


def build_fishing_bundle(tg: int) -> dict[str, Any]:
    _legacy_service().ensure_seed_data()
    settings = _legacy_service().get_xiuxian_settings()
    profile = get_profile(tg, create=False)
    if profile is None or not profile.consented:
        return {
            "spots": [],
            "current_fortune": 0,
            "available_spot_count": 0,
            "note": "踏入仙途后才能开始垂钓。",
        }
    item_lookups = _build_item_lookups()
    base_candidates = _build_fishing_candidates(item_lookups, settings=settings)
    spots = [_build_spot_bundle(spot, profile, _spot_candidates(spot, base_candidates)) for spot in FISHING_SPOTS.values()]
    return {
        "spots": spots,
        "current_fortune": max(int(profile.fortune or 0), 0),
        "available_spot_count": sum(1 for spot in spots if spot.get("available")),
        "note": "垂钓与仙界奇石共用同一套奖励池，但会额外压低高品阶权重；破境丹与丹方仅能在对应秘境中获取。",
    }


def cast_fishing_line_for_user(tg: int, spot_key: str) -> dict[str, Any]:
    _legacy_service().ensure_seed_data()
    settings = _legacy_service().get_xiuxian_settings()
    spot = FISHING_SPOTS.get(str(spot_key or "").strip())
    if not spot:
        raise ValueError("钓场不存在")

    full_bundle = _legacy_service().serialize_full_profile(tg)
    effective_stats = full_bundle.get("effective_stats") or {}
    effective_fortune = max(int(effective_stats.get("fortune") or full_bundle.get("profile", {}).get("fortune") or 0), 0)

    with Session() as session:
        profile = session.query(XiuxianProfile).filter(XiuxianProfile.tg == int(tg)).with_for_update().first()
        if profile is None or not profile.consented:
            raise ValueError("你还没有踏入仙途")
        assert_profile_alive(profile, "前往钓鱼")
        if not _meets_realm_requirement(profile, spot.get("min_realm_stage"), int(spot.get("min_realm_layer") or 1)):
            raise ValueError(f"前往 {spot['name']} 需达到 {_spot_requirement_text(spot)}")

        base_candidates = _build_fishing_candidates(_build_item_lookups(), settings=settings)
        candidates = _spot_candidates(spot, base_candidates)
        if not candidates:
            raise ValueError("该钓场当前没有可钓取的奖励")

        tier_pick = _weighted_choice(
            _tier_weights_for_spot(spot, effective_fortune, {int(row.get("quality_level") or 0) for row in candidates}, settings),
            weight_key="weight",
        )
        if not tier_pick:
            raise ValueError("当前无法计算钓鱼概率")
        chosen_tier = int(tier_pick.get("quality_level") or 1)
        tier_candidates = [row for row in candidates if int(row.get("quality_level") or 0) == chosen_tier]
        kind_pick = _weighted_choice(_kind_weights_for_tier(spot, tier_candidates), weight_key="weight")
        if not kind_pick:
            raise ValueError("当前钓场没有可用的奖励种类")
        chosen_kind = str(kind_pick.get("kind") or "")
        kind_candidates = [row for row in tier_candidates if str(row.get("kind") or "") == chosen_kind]
        chosen = _weighted_choice(kind_candidates, weight_key="fishing_weight")
        if not chosen:
            raise ValueError("当前钓场没有可用的奖励物品")

        cast_cost_stone = max(int(spot.get("cast_cost_stone") or 0), 0)
        if cast_cost_stone > 0:
            apply_spiritual_stone_delta(
                session,
                tg,
                -cast_cost_stone,
                action_text=f"前往 {spot['name']} 抛竿",
                apply_tribute=False,
            )
        session.commit()

    quantity = random.randint(int(chosen.get("quantity_min") or 1), int(chosen.get("quantity_max") or 1))
    try:
        _grant_item_by_kind(tg, chosen_kind, int(chosen.get("ref_id") or 0), quantity)
    except Exception as exc:
        if cast_cost_stone > 0:
            with Session() as session:
                apply_spiritual_stone_delta(
                    session,
                    tg,
                    cast_cost_stone,
                    action_text=f"{spot['name']} 垂钓异常返还灵石",
                    apply_tribute=False,
                )
                session.commit()
        raise ValueError("垂钓奖励发放失败，已返还本次灵石，请稍后重试。") from exc

    reward_name = str(chosen.get("name") or "未知物品").strip() or "未知物品"
    kind_label = str(chosen.get("kind_label") or ITEM_KIND_LABELS.get(chosen_kind, chosen_kind))
    quality_level = max(int(chosen.get("quality_level") or 1), 1)
    quality = _quality_meta(quality_level)
    luck_note = ""
    if effective_fortune >= 18 and quality_level >= max(int(spot.get("quality_min") or 1) + 1, 3):
        luck_note = "机缘牵引之下，钓线拽起了更高品阶的宝物。"
    elif quality_level >= 6:
        luck_note = "浪潮深处只浮起一瞬异光，你险些错过这件重宝。"
    message = f"你在 {spot['name']} 抛竿，钓起了 {quality['label']}{kind_label}【{reward_name}】"
    if quantity > 1:
        message += f" ×{quantity}"
    message += "。"
    if luck_note:
        message += luck_note

    create_journal(
        tg,
        "fishing",
        "灵河垂钓",
        f"在 {spot['name']} 钓起【{reward_name}】×{quantity}，品阶 {quality['label']}。",
    )
    return {
        "spot_key": spot["key"],
        "spot_name": spot["name"],
        "cast_cost_stone": max(int(spot.get("cast_cost_stone") or 0), 0),
        "fortune_used": effective_fortune,
        "reward_kind": chosen_kind,
        "reward_kind_label": kind_label,
        "reward_item": chosen.get("item"),
        "quantity": quantity,
        "quality_level": quality_level,
        "quality_label": quality["label"],
        "quality_color": quality["color"],
        "message": message,
    }

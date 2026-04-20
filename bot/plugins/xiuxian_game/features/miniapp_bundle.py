from __future__ import annotations

from typing import Any

from bot.func_helper.emby_currency import get_emby_balance, get_exchange_settings
from bot.plugins.xiuxian_game.features.exploration import _scene_requirement_state
from bot.plugins.xiuxian_game.features.gambling import build_gambling_bundle
from bot.plugins.xiuxian_game.features.shop import attach_official_recycle_quotes
from bot.plugins.xiuxian_game.service import (
    DEFAULT_SETTINGS,
    _apply_profile_growth_floor,
    _battle_bundle,
    _breakthrough_requirement,
    _current_technique_payload,
    _gender_lock_reason,
    _is_retreating,
    _normalized_root_quality,
    _profile_name_with_title,
    _rebirth_cooldown_state,
    _repair_profile_realm_state,
    _root_quality_payload,
    _settle_retreat_progress,
    SOCIAL_MODE_LABELS,
    build_progress,
    format_root,
    get_current_title,
    get_profile,
    get_active_duel_lock,
    get_xiuxian_settings,
    is_same_china_day,
    list_equipped_artifacts,
    list_user_techniques,
    profile_social_mode,
    seclusion_cultivation_efficiency_percent,
    serialize_talisman,
    serialize_full_profile,
    serialize_profile,
    get_talisman,
)
from bot.plugins.xiuxian_game.world_service import (
    _user_task_daily_limit,
    _user_task_publish_count_today,
    get_current_sect_bundle,
    list_sects_for_user,
)


def build_full_profile_bundle(
    tg: int,
    *,
    can_upload_images: bool = False,
    upload_image_reason: str = "",
    allow_non_admin_image_upload: bool = False,
    is_admin: bool = False,
    admin_panel_url: str | None = None,
) -> dict[str, Any]:
    bundle = serialize_full_profile(tg)
    from bot.plugins.xiuxian_game.features.world_bundle import build_world_bundle

    world_bundle = build_world_bundle(tg)
    bundle.update({key: value for key, value in world_bundle.items() if key != "settings"})
    attach_official_recycle_quotes(bundle)
    _apply_scene_requirement_state(bundle)
    _apply_capabilities(
        bundle,
        can_upload_images=can_upload_images,
        upload_image_reason=upload_image_reason,
        allow_non_admin_image_upload=allow_non_admin_image_upload,
        is_admin=is_admin,
        admin_panel_url=admin_panel_url,
    )
    bundle["gambling"] = build_gambling_bundle(tg, bundle=bundle)
    return bundle


def build_bootstrap_core_bundle(
    tg: int,
    *,
    can_upload_images: bool = False,
    upload_image_reason: str = "",
    allow_non_admin_image_upload: bool = False,
    is_admin: bool = False,
    admin_panel_url: str | None = None,
) -> dict[str, Any]:
    bundle = _build_core_profile_bundle(tg)
    bundle.update(_build_core_world_bundle(tg))
    attach_official_recycle_quotes(bundle)
    _apply_capabilities(
        bundle,
        can_upload_images=can_upload_images,
        upload_image_reason=upload_image_reason,
        allow_non_admin_image_upload=allow_non_admin_image_upload,
        is_admin=is_admin,
        admin_panel_url=admin_panel_url,
    )
    return bundle


def build_deferred_profile_sections(
    tg: int,
    *,
    can_upload_images: bool = False,
    upload_image_reason: str = "",
    allow_non_admin_image_upload: bool = False,
    is_admin: bool = False,
    admin_panel_url: str | None = None,
) -> dict[str, Any]:
    return build_full_profile_bundle(
        tg,
        can_upload_images=can_upload_images,
        upload_image_reason=upload_image_reason,
        allow_non_admin_image_upload=allow_non_admin_image_upload,
        is_admin=is_admin,
        admin_panel_url=admin_panel_url,
    )


def _build_core_profile_bundle(tg: int) -> dict[str, Any]:
    _prepare_profile_state(tg)
    profile_obj = _repair_profile_realm_state(tg)
    if profile_obj is None:
        profile_obj = get_profile(tg, create=True)
    profile = dict(serialize_profile(profile_obj) or {})
    if not profile:
        raise ValueError("未找到修仙档案。")
    raw_spiritual_stone = int(profile.get("spiritual_stone") or 0)
    shared_spiritual_stone = (
        raw_spiritual_stone if not profile.get("consented") else int(profile.get("spiritual_stone") or 0)
    )
    profile["personal_spiritual_stone"] = raw_spiritual_stone
    profile["spiritual_stone"] = shared_spiritual_stone
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
    progress = build_progress(
        profile["realm_stage"],
        int(profile.get("realm_layer") or 1),
        int(profile.get("cultivation") or 0),
    )
    retreating = bool(profile_obj and _is_retreating(profile_obj))
    xiuxian_settings = get_xiuxian_settings()
    equip_limit = max(int(xiuxian_settings.get("artifact_equip_limit", DEFAULT_SETTINGS["artifact_equip_limit"]) or 0), 1)
    equipped_artifacts = []
    for row in list_equipped_artifacts(tg):
        artifact = dict(row.get("artifact") or {})
        if not artifact:
            continue
        artifact["equipped"] = True
        artifact["slot"] = row.get("slot")
        equipped_artifacts.append(artifact)
    active_talisman = serialize_talisman(get_talisman(profile_obj.active_talisman_id)) if profile_obj and profile_obj.active_talisman_id else None
    current_technique = _current_technique_payload(profile)
    current_title = get_current_title(tg)
    battle = _battle_bundle(
        {
            "profile": profile,
            "equipped_artifacts": equipped_artifacts,
            "active_talisman": active_talisman,
            "current_technique": current_technique,
            "current_title": current_title,
        }
    )
    effective_stats = {
        key: int(round(value)) if isinstance(value, (int, float)) else value
        for key, value in battle["stats"].items()
    }
    combat_power = int(round(battle["power"]))
    if current_title:
        profile["current_title_name"] = current_title.get("name")
        profile["display_name_with_title"] = _profile_name_with_title(profile, current_title)
    else:
        profile["current_title_name"] = None
    profile["is_dead"] = bool(profile.get("death_at"))
    profile["social_mode"] = profile_social_mode(profile)
    profile["social_mode_label"] = SOCIAL_MODE_LABELS.get(profile["social_mode"], "入世")
    profile["is_secluded"] = profile["social_mode"] == "secluded"
    rebirth_cooldown = _rebirth_cooldown_state(profile, xiuxian_settings)
    profile["rebirth_cooldown_enabled"] = rebirth_cooldown["enabled"]
    profile["rebirth_cooldown_hours"] = rebirth_cooldown["cooldown_hours"]
    profile["rebirth_cooldown_remaining_seconds"] = rebirth_cooldown["remaining_seconds"]
    profile["rebirth_available_at"] = rebirth_cooldown["available_at"]
    profile["rebirth_locked"] = rebirth_cooldown["blocked"]
    profile["rebirth_cooldown_reason"] = rebirth_cooldown["reason"]
    gender_lock_reason = _gender_lock_reason(profile_obj or profile)
    gender_locked = bool(gender_lock_reason)
    active_duel_lock = get_active_duel_lock(tg)
    breakthrough_requirement = _breakthrough_requirement(profile.get("realm_stage"))
    settings = {
        **get_exchange_settings(),
        "coin_stone_exchange_enabled": bool(
            xiuxian_settings.get("coin_stone_exchange_enabled", DEFAULT_SETTINGS.get("coin_stone_exchange_enabled", True))
        ),
        "artifact_equip_limit": equip_limit,
        "equipment_unbind_cost": int(xiuxian_settings.get("equipment_unbind_cost", DEFAULT_SETTINGS["equipment_unbind_cost"]) or 0),
        "official_shop_name": str(
            xiuxian_settings.get("official_shop_name", DEFAULT_SETTINGS["official_shop_name"])
            or DEFAULT_SETTINGS["official_shop_name"]
        ),
        "allow_user_task_publish": bool(
            xiuxian_settings.get("allow_user_task_publish", DEFAULT_SETTINGS["allow_user_task_publish"])
        ),
        "task_publish_cost": max(int(xiuxian_settings.get("task_publish_cost", DEFAULT_SETTINGS["task_publish_cost"]) or 0), 0),
        "user_task_daily_limit": _user_task_daily_limit(),
        "user_task_published_today": _user_task_publish_count_today(tg),
        "furnace_harvest_cultivation_percent": max(
            int(
                xiuxian_settings.get(
                    "furnace_harvest_cultivation_percent",
                    DEFAULT_SETTINGS["furnace_harvest_cultivation_percent"],
                )
                or 0
            ),
            0,
        ),
        "seclusion_cultivation_efficiency_percent": seclusion_cultivation_efficiency_percent(xiuxian_settings),
    }
    capabilities = {
        "can_train": profile["consented"] and not profile["is_dead"] and not gender_locked and not retreating and not is_same_china_day(profile_obj.last_train_at if profile_obj else None, utcnow_placeholder()),
        "train_reason": (
            gender_lock_reason
            if gender_locked
            else (
                "角色已死亡，只能重新踏出仙途"
                if profile["is_dead"]
                else ("" if not retreating and not is_same_china_day(profile_obj.last_train_at if profile_obj else None, utcnow_placeholder()) else ("闭关期间无法吐纳修炼" if retreating else "今日已经完成过吐纳修炼了"))
            )
        ),
        "can_breakthrough": profile["consented"] and not profile["is_dead"] and not gender_locked and not retreating and int(profile.get("realm_layer") or 0) >= 9 and bool(progress["breakthrough_ready"]),
        "breakthrough_reason": (
            gender_lock_reason
            if gender_locked
            else (
                "角色已死亡，只能重新踏出仙途"
                if profile["is_dead"]
                else ("" if not retreating and int(profile.get("realm_layer") or 0) >= 9 and progress["breakthrough_ready"] else ("闭关期间无法突破" if retreating else "只有达到当前境界九层且满修为后才能突破"))
            )
        ),
        "required_breakthrough_pill_name": (breakthrough_requirement or {}).get("pill_name"),
        "required_breakthrough_scene_name": (breakthrough_requirement or {}).get("scene_name"),
        "can_retreat": profile["consented"] and not profile["is_dead"] and not gender_locked and not retreating,
        "retreat_reason": gender_lock_reason if gender_locked else ("角色已死亡，只能重新踏出仙途" if profile["is_dead"] else ("" if not retreating else "你正在闭关中")),
        "is_in_retreat": retreating,
        "is_dead": profile["is_dead"],
        "death_reason": rebirth_cooldown["reason"] if rebirth_cooldown["blocked"] else ("角色已死亡，只能重新踏出仙途" if profile["is_dead"] else ""),
        "can_enter_path": not profile["consented"] and not rebirth_cooldown["blocked"],
        "enter_reason": rebirth_cooldown["reason"],
        "rebirth_locked": rebirth_cooldown["blocked"],
        "social_mode": profile["social_mode"],
        "social_mode_label": profile["social_mode_label"],
        "is_secluded": profile["is_secluded"],
        "can_toggle_social_mode": profile["consented"] and not profile["is_dead"] and not gender_locked,
        "social_mode_toggle_reason": gender_lock_reason if gender_locked else ("角色已死亡，只能重新踏出仙途" if profile["is_dead"] else ""),
        "social_interaction_lock_reason": (
            gender_lock_reason
            if gender_locked
            else (
                f"你当前处于避世状态，对外互动已关闭，修为收益按 {settings['seclusion_cultivation_efficiency_percent']}% 结算。"
                if profile["is_secluded"]
                else ""
            )
        ),
        "gender_required": gender_locked,
        "gender_lock_reason": gender_lock_reason,
        "shared_spiritual_stone_total": shared_spiritual_stone,
        "shared_inventory_enabled": False,
        "shared_inventory_note": "结为道侣后，灵石与背包会自动共享。" if not gender_locked else "",
        "artifact_equip_limit": equip_limit,
        "equipped_artifact_count": len(equipped_artifacts),
        "duel_locked": bool(active_duel_lock),
        "duel_lock": active_duel_lock,
        "duel_lock_reason": "" if not active_duel_lock else f"{active_duel_lock['duel_mode_label']}结算前，禁止灵石与交易操作",
    }

    bundle = {
        "profile": profile,
        "progress": progress,
        "capabilities": capabilities,
        "emby_balance": get_emby_balance(tg),
        "equipped_artifact": equipped_artifacts[0] if equipped_artifacts else None,
        "equipped_artifacts": equipped_artifacts,
        "active_talisman": active_talisman,
        "current_technique": current_technique,
        "current_title": current_title,
        "active_artifact_sets": [],
        "settings": settings,
        "effective_stats": effective_stats,
        "combat_power": combat_power,
        "attribute_effects": _build_attribute_effects(profile, effective_stats),
        "commissions": [],
        "mentorship": {},
        "marriage": {},
        "master_profile": None,
        "slave_profiles": [],
        "titles": [],
        "achievements": [],
        "achievement_metric_progress": {},
        "achievement_unlocked_count": 0,
        "achievement_total_count": 0,
        "technique_owned_count": len(list_user_techniques(tg, enabled_only=False)),
        "technique_total_count": 0,
    }
    return bundle


def _prepare_profile_state(tg: int) -> None:
    profile = _repair_profile_realm_state(tg)
    if profile is None:
        profile = get_profile(tg, create=True)
    if profile and profile.consented:
        _settle_retreat_progress(tg)
        _apply_profile_growth_floor(tg)


def _build_core_world_bundle(tg: int) -> dict[str, Any]:
    settings = get_xiuxian_settings()
    return {
        "sects": list_sects_for_user(tg),
        "current_sect": get_current_sect_bundle(tg),
        "settings": {
            "allow_user_task_publish": bool(settings.get("allow_user_task_publish", DEFAULT_SETTINGS["allow_user_task_publish"])),
            "task_publish_cost": max(int(settings.get("task_publish_cost", DEFAULT_SETTINGS["task_publish_cost"]) or 0), 0),
            "user_task_daily_limit": _user_task_daily_limit(),
            "user_task_published_today": _user_task_publish_count_today(tg),
        },
    }


def _build_attribute_effects(profile: dict[str, Any], effective_stats: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    labels = (
        ("bone", "根骨"),
        ("comprehension", "悟性"),
        ("divine_sense", "神识"),
        ("fortune", "机缘"),
        ("willpower", "心志"),
        ("charisma", "魅力"),
        ("karma", "因果"),
        ("qi_blood", "气血"),
        ("true_yuan", "真元"),
        ("body_movement", "身法"),
        ("attack_power", "攻击"),
        ("defense_power", "防御"),
    )
    for key, label in labels:
        rows.append(
            {
                "key": key,
                "label": label,
                "value": int(profile.get(key) or 0),
                "effective_value": int(effective_stats.get(key) or 0),
                "effect": "",
            }
        )
    return rows


def utcnow_placeholder():
    from bot.plugins.xiuxian_game.service import utcnow

    return utcnow()


def _apply_scene_requirement_state(bundle: dict[str, Any]) -> None:
    profile = bundle.get("profile") or {}
    combat_power = int(bundle.get("combat_power") or 0)
    for scene in bundle.get("scenes") or []:
        if not isinstance(scene, dict):
            continue
        scene["requirement_state"] = _scene_requirement_state(profile, scene, combat_power)


def _apply_capabilities(
    bundle: dict[str, Any],
    *,
    can_upload_images: bool,
    upload_image_reason: str,
    allow_non_admin_image_upload: bool,
    is_admin: bool,
    admin_panel_url: str | None,
) -> None:
    bundle.setdefault("capabilities", {})
    bundle["capabilities"]["can_upload_images"] = can_upload_images
    bundle["capabilities"]["upload_image_reason"] = upload_image_reason
    bundle["capabilities"]["is_admin"] = is_admin
    bundle["capabilities"]["admin_panel_url"] = admin_panel_url if is_admin else None
    bundle.setdefault("settings", {})
    bundle["settings"]["allow_non_admin_image_upload"] = bool(allow_non_admin_image_upload)

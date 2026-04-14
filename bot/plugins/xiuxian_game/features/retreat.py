from __future__ import annotations

from datetime import timedelta
from math import ceil
from typing import Any

from bot.sql_helper.sql_xiuxian import (
    DEFAULT_SETTINGS,
    get_current_title,
    get_profile,
    get_xiuxian_settings,
    serialize_profile,
    upsert_profile,
    utcnow,
)


def _legacy_service():
    from bot.plugins.xiuxian_game import service as legacy_service

    return legacy_service


def is_retreating(profile) -> bool:
    return bool(
        profile
        and profile.retreat_started_at
        and profile.retreat_end_at
        and int(profile.retreat_minutes_total or 0) > int(profile.retreat_minutes_resolved or 0)
    )


def _compute_retreat_plan(profile) -> dict[str, int]:
    from bot.plugins.xiuxian_game.world_service import get_sect_effects

    legacy_service = _legacy_service()
    profile_data = serialize_profile(profile)
    artifact_effects = legacy_service.merge_artifact_effects(
        profile_data,
        legacy_service.collect_equipped_artifacts(profile.tg),
    )
    sect_effects = get_sect_effects(profile_data)
    technique_effects = legacy_service.resolve_technique_effects(
        profile_data,
        legacy_service._current_technique_payload(profile_data),
    )
    title_effects = legacy_service.resolve_title_effects(
        profile_data,
        get_current_title(profile.tg),
    )
    artifact_bonus = (
        int(artifact_effects.get("cultivation_bonus", 0))
        + int(sect_effects.get("cultivation_bonus", 0))
        + int(technique_effects.get("cultivation_bonus", 0))
        + int(title_effects.get("cultivation_bonus", 0))
        + int(profile_data.get("insight_bonus", 0) or 0)
    )
    poison_penalty = min(int(profile.dan_poison or 0) // 4, 25)
    gain_per_hour = max(
        90
        + legacy_service.realm_index(profile.realm_stage) * 18
        + int(profile.realm_layer or 1) * 10
        + artifact_bonus * 2
        - poison_penalty,
        40,
    )
    cost_per_hour = max(ceil(gain_per_hour / 12), 6)
    return {
        "gain_per_minute": max(gain_per_hour // 60, 1),
        "cost_per_minute": max(cost_per_hour // 60, 1),
    }


def settle_retreat_progress(tg: int) -> dict[str, Any] | None:
    legacy_service = _legacy_service()
    profile = get_profile(tg, create=False)
    if profile is None or not is_retreating(profile):
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

    gain_per_minute = max(int(profile.retreat_gain_per_minute or 0), 0)
    cost_per_minute = max(int(profile.retreat_cost_per_minute or 0), 0)
    affordable_minutes = delta_minutes
    insufficient_stone = False
    if cost_per_minute > 0:
        affordable_minutes = min(
            delta_minutes,
            max(int(profile.spiritual_stone or 0), 0) // cost_per_minute,
        )
        insufficient_stone = affordable_minutes < delta_minutes

    if affordable_minutes <= 0:
        if insufficient_stone or now >= end_at:
            updated = upsert_profile(
                tg,
                retreat_started_at=None,
                retreat_end_at=None,
                retreat_gain_per_minute=0,
                retreat_cost_per_minute=0,
                retreat_minutes_total=0,
                retreat_minutes_resolved=0,
            )
            return {
                "gain": 0,
                "cost": 0,
                "upgraded_layers": [],
                "remaining": 0,
                "finished": True,
                "insufficient_stone": True,
                "profile": serialize_profile(updated),
            }
        return None

    gain = affordable_minutes * gain_per_minute
    cost = affordable_minutes * cost_per_minute
    layer, cultivation, upgraded_layers, remaining = legacy_service.apply_cultivation_gain(
        profile.realm_stage or "炼气",
        int(profile.realm_layer or 1),
        int(profile.cultivation or 0),
        gain,
    )

    settled_minutes = min(resolved_minutes + affordable_minutes, total_minutes)
    finished = insufficient_stone or settled_minutes >= total_minutes or now >= end_at
    updated = upsert_profile(
        tg,
        cultivation=cultivation,
        realm_layer=layer,
        spiritual_stone=max(int(profile.spiritual_stone or 0) - cost, 0),
        retreat_minutes_resolved=0 if finished else settled_minutes,
        retreat_started_at=None if finished else profile.retreat_started_at,
        retreat_end_at=None if finished else profile.retreat_end_at,
        retreat_gain_per_minute=0 if finished else int(profile.retreat_gain_per_minute or 0),
        retreat_cost_per_minute=0 if finished else int(profile.retreat_cost_per_minute or 0),
        retreat_minutes_total=0 if finished else total_minutes,
    )
    return {
        "gain": gain,
        "cost": cost,
        "upgraded_layers": upgraded_layers,
        "remaining": remaining,
        "finished": finished,
        "insufficient_stone": insufficient_stone,
        "profile": serialize_profile(updated),
    }


def ensure_not_in_retreat(tg: int) -> None:
    profile = get_profile(tg, create=False)
    if profile is not None and is_retreating(profile):
        raise ValueError("你正在闭关中，当前不能执行这个操作。")


def start_retreat_for_user(tg: int, hours: int) -> dict[str, Any]:
    legacy_service = _legacy_service()
    profile = get_profile(tg, create=False)
    if profile is None or not profile.consented:
        raise ValueError("你还没有踏入仙途。")
    if is_retreating(profile):
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
        "profile": legacy_service.serialize_full_profile(updated.tg),
    }


def finish_retreat_for_user(tg: int) -> dict[str, Any]:
    legacy_service = _legacy_service()
    result = settle_retreat_progress(tg)
    profile = get_profile(tg, create=False)
    if profile is None or not profile.consented:
        raise ValueError("你还没有踏入仙途。")
    if result is None and not is_retreating(profile):
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
        "profile": legacy_service.serialize_full_profile(tg),
    }


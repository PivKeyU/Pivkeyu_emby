from __future__ import annotations

from datetime import timedelta
from math import ceil
from typing import Any

from bot.sql_helper import Session
from bot.sql_helper.sql_xiuxian import (
    XiuxianProfile,
    apply_spiritual_stone_delta,
    assert_currency_operation_allowed,
    get_current_title,
    get_profile,
    get_shared_spiritual_stone_total,
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
    stage = legacy_service.normalize_realm_stage(profile.realm_stage or legacy_service.FIRST_REALM_STAGE)
    stage_rule = legacy_service._realm_stage_rule(stage)
    poison_penalty = min(int(profile.dan_poison or 0) // 4, 25)
    gain_per_hour = max(
        int(stage_rule["retreat_hourly_base"])
        + int(profile.realm_layer or 1) * 18
        + legacy_service.realm_index(stage) * 48
        + artifact_bonus * 3
        - poison_penalty * 4,
        60,
    )
    cost_per_hour = max(ceil(gain_per_hour / 10), 12)
    return {
        "gain_per_minute": max(gain_per_hour // 60, 1),
        "cost_per_minute": max(cost_per_hour // 60, 1),
    }


def settle_retreat_progress(tg: int) -> dict[str, Any] | None:
    legacy_service = _legacy_service()
    profile = legacy_service._repair_profile_realm_state(tg) or get_profile(tg, create=False)
    if profile is None or not is_retreating(profile):
        return None

    now = utcnow()
    with Session() as session:
        updated = session.query(XiuxianProfile).filter(XiuxianProfile.tg == int(tg)).with_for_update().first()
        if updated is None or not is_retreating(updated):
            return None

        end_at = updated.retreat_end_at or now
        started_at = updated.retreat_started_at or now
        total_minutes = max(int(updated.retreat_minutes_total or 0), 0)
        resolved_minutes = max(int(updated.retreat_minutes_resolved or 0), 0)
        elapsed_minutes = int(max(min(now, end_at) - started_at, timedelta()).total_seconds() // 60)
        target_minutes = min(max(elapsed_minutes, 0), total_minutes)
        delta_minutes = max(target_minutes - resolved_minutes, 0)

        if delta_minutes <= 0:
            if now >= end_at and resolved_minutes >= total_minutes:
                updated.retreat_started_at = None
                updated.retreat_end_at = None
                updated.retreat_gain_per_minute = 0
                updated.retreat_cost_per_minute = 0
                updated.retreat_minutes_total = 0
                updated.retreat_minutes_resolved = 0
                updated.updated_at = now
                session.commit()
            return None

        gain_per_minute = max(int(updated.retreat_gain_per_minute or 0), 0)
        cost_per_minute = max(int(updated.retreat_cost_per_minute or 0), 0)
        affordable_minutes = delta_minutes
        insufficient_stone = False
        if cost_per_minute > 0:
            available_stone = max(int(get_shared_spiritual_stone_total(tg, session=session, for_update=True) or 0), 0)
            affordable_minutes = min(delta_minutes, available_stone // cost_per_minute)
            insufficient_stone = affordable_minutes < delta_minutes

        if affordable_minutes <= 0:
            if insufficient_stone or now >= end_at:
                updated.retreat_started_at = None
                updated.retreat_end_at = None
                updated.retreat_gain_per_minute = 0
                updated.retreat_cost_per_minute = 0
                updated.retreat_minutes_total = 0
                updated.retreat_minutes_resolved = 0
                updated.updated_at = now
                session.commit()
                profile_payload = serialize_profile(updated)
                return {
                    "gain": 0,
                    "gain_raw": 0,
                    "cultivation_efficiency_percent": 100,
                    "cost": 0,
                    "upgraded_layers": [],
                    "remaining": 0,
                    "finished": True,
                    "insufficient_stone": True,
                    "profile": profile_payload,
                }
            return None

        raw_gain = affordable_minutes * gain_per_minute
        gain, gain_meta = legacy_service.adjust_cultivation_gain_for_social_mode(updated, raw_gain)
        cost = affordable_minutes * cost_per_minute
        layer, cultivation, upgraded_layers, remaining = legacy_service.apply_cultivation_gain(
            legacy_service.normalize_realm_stage(updated.realm_stage or legacy_service.FIRST_REALM_STAGE),
            int(updated.realm_layer or 1),
            int(updated.cultivation or 0),
            gain,
        )

        settled_minutes = min(resolved_minutes + affordable_minutes, total_minutes)
        finished = insufficient_stone or settled_minutes >= total_minutes or now >= end_at
        if cost > 0:
            apply_spiritual_stone_delta(
                session,
                tg,
                -cost,
                action_text="闭关消耗灵石",
                enforce_currency_lock=True,
                allow_dead=False,
                apply_tribute=False,
            )
        updated.cultivation = cultivation
        updated.realm_layer = layer
        updated.retreat_minutes_resolved = 0 if finished else settled_minutes
        updated.retreat_started_at = None if finished else updated.retreat_started_at
        updated.retreat_end_at = None if finished else updated.retreat_end_at
        updated.retreat_gain_per_minute = 0 if finished else int(updated.retreat_gain_per_minute or 0)
        updated.retreat_cost_per_minute = 0 if finished else int(updated.retreat_cost_per_minute or 0)
        updated.retreat_minutes_total = 0 if finished else total_minutes
        updated.updated_at = now
        session.commit()
        profile_payload = serialize_profile(updated)

    return {
        "gain": gain,
        "gain_raw": raw_gain,
        "cultivation_efficiency_percent": int(gain_meta.get("efficiency_percent") or 100),
        "cost": cost,
        "upgraded_layers": upgraded_layers,
        "remaining": remaining,
        "finished": finished,
        "insufficient_stone": insufficient_stone,
        "profile": profile_payload,
    }


def ensure_not_in_retreat(tg: int) -> None:
    legacy_service = _legacy_service()
    profile = get_profile(tg, create=False)
    if profile is not None:
        legacy_service._assert_gender_ready(profile, "执行当前操作")
    if profile is not None and is_retreating(profile):
        raise ValueError("你正在闭关中，当前不能执行这个操作。")


def start_retreat_for_user(tg: int, hours: int) -> dict[str, Any]:
    legacy_service = _legacy_service()
    profile = legacy_service._require_alive_profile_obj(tg, "开始闭关")
    assert_currency_operation_allowed(tg, "开始闭关", profile=profile)
    if is_retreating(profile):
        raise ValueError("你已经在闭关中。")

    retreat_hours = max(min(int(hours or 0), 4), 1)
    plan = _compute_retreat_plan(profile)
    total_minutes = retreat_hours * 60
    estimated_gain_raw = plan["gain_per_minute"] * total_minutes
    estimated_gain, gain_meta = legacy_service.adjust_cultivation_gain_for_social_mode(profile, estimated_gain_raw)
    total_cost = plan["cost_per_minute"] * total_minutes
    if max(int(get_shared_spiritual_stone_total(tg) or 0), 0) < total_cost:
        raise ValueError(f"灵石不足，闭关 {retreat_hours} 小时预计需要 {total_cost} 灵石。")

    now = utcnow()
    upsert_profile(
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
        "estimated_gain": estimated_gain,
        "estimated_gain_raw": estimated_gain_raw,
        "cultivation_efficiency_percent": int(gain_meta.get("efficiency_percent") or 100),
        "estimated_cost": total_cost,
        "profile": legacy_service.serialize_full_profile(tg),
    }


def finish_retreat_for_user(tg: int) -> dict[str, Any]:
    legacy_service = _legacy_service()
    profile = legacy_service._require_alive_profile_obj(tg, "结束闭关")
    assert_currency_operation_allowed(tg, "结束闭关", profile=profile)
    result = settle_retreat_progress(tg)
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
        "settled": result
        or {
            "gain": 0,
            "gain_raw": 0,
            "cultivation_efficiency_percent": 100,
            "cost": 0,
            "upgraded_layers": [],
            "finished": True,
        },
        "profile": legacy_service.serialize_full_profile(tg),
    }

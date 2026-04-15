"""修仙世界玩法服务。

这里保留历史兼容出口。
后续新增或维护优先落到 `features/` 下的对应世界玩法文件，再由这里兼容导出。
"""

from __future__ import annotations

import random
import re
from datetime import datetime, timedelta
from typing import Any

from bot.sql_helper import Session
from bot.sql_helper.sql_xiuxian import (
    DEFAULT_SETTINGS,
    DUEL_MODE_LABELS,
    QUALITY_LABEL_LEVELS,
    SECT_ROLE_LABELS,
    SECT_ROLE_PRESETS,
    apply_spiritual_stone_delta,
    assert_currency_operation_allowed,
    assert_profile_alive,
    XiuxianArtifactInventory,
    XiuxianEquippedArtifact,
    XiuxianPillInventory,
    XiuxianProfile,
    XiuxianRecipe,
    XiuxianRecipeIngredient,
    XiuxianSect,
    XiuxianSectRole,
    XiuxianTask,
    XiuxianTaskClaim,
    XiuxianUserTechnique,
    XiuxianMaterialInventory,
    XiuxianTalismanInventory,
    XiuxianExploration,
    XiuxianScene,
    XiuxianSceneDrop,
    XiuxianRedEnvelope,
    XiuxianRedEnvelopeClaim,
    XiuxianDuelBetPool,
    XiuxianDuelBet,
    create_recipe,
    create_scene,
    create_scene_drop,
    create_sect,
    create_task,
    create_journal,
    get_artifact,
    get_emby_name_map,
    get_material,
    get_pill,
    get_profile,
    get_recipe,
    get_red_envelope,
    get_scene,
    get_sect,
    get_technique,
    get_talisman,
    get_xiuxian_settings,
    get_active_duel_lock,
    grant_artifact_to_user,
    grant_material_to_user,
    grant_pill_to_user,
    grant_recipe_to_user,
    grant_talisman_to_user,
    grant_technique_to_user,
    list_recipe_ingredients,
    list_recipes,
    list_recent_journals,
    list_red_envelope_claims,
    list_scene_drops,
    list_scenes,
    list_equipped_artifacts,
    list_slave_profiles,
    list_sect_roles,
    list_sects,
    list_tasks,
    list_techniques,
    list_user_materials,
    list_user_recipes,
    list_user_techniques,
    plunder_random_artifact_to_user,
    realm_index,
    patch_sect,
    replace_recipe_ingredients,
    replace_sect_roles,
    serialize_exploration,
    serialize_datetime,
    serialize_material,
    serialize_profile,
    serialize_recipe,
    serialize_red_envelope,
    serialize_scene,
    serialize_sect,
    serialize_technique,
    serialize_talisman,
    serialize_task,
    upsert_profile,
    utcnow,
)
from bot.plugins.xiuxian_game.probability import roll_probability_percent
from bot.plugins.xiuxian_game.achievement_service import (
    record_craft_metrics,
    record_exploration_metrics,
    record_gift_metrics,
    record_red_envelope_metrics,
    record_robbery_metrics,
)


RARITY_LEVEL_MAP = {
    **QUALITY_LABEL_LEVELS,
    "黄品": 2,
    "玄品": 3,
    "地品": 4,
    "天品": 5,
}


def china_now():
    return utcnow() + timedelta(hours=8)


def china_day_key() -> str:
    return china_now().strftime("%Y-%m-%d")


def _require_alive_profile_data(tg: int, action_text: str) -> tuple[XiuxianProfile, dict[str, Any]]:
    profile_obj = get_profile(tg, create=False)
    if profile_obj is None or not profile_obj.consented:
        raise ValueError("你还没有踏入仙途")
    assert_profile_alive(profile_obj, action_text)
    return profile_obj, serialize_profile(profile_obj)


def _full_profile_bundle(tg: int) -> dict[str, Any]:
    from bot.plugins.xiuxian_game.service import serialize_full_profile

    return serialize_full_profile(tg)


def floor_div(left: int, right: int) -> int:
    if right <= 0:
        return 0
    return int(left // right)


def _zero_effects() -> dict[str, int]:
    return {
        "attack_bonus": 0,
        "defense_bonus": 0,
        "bone_bonus": 0,
        "comprehension_bonus": 0,
        "divine_sense_bonus": 0,
        "fortune_bonus": 0,
        "qi_blood_bonus": 0,
        "true_yuan_bonus": 0,
        "body_movement_bonus": 0,
        "duel_rate_bonus": 0,
        "cultivation_bonus": 0,
        "breakthrough_bonus": 0,
    }


def get_sect_role_payload(sect_id: int | None, role_key: str | None) -> dict[str, Any] | None:
    if not sect_id or not role_key:
        return None
    for role in list_sect_roles(int(sect_id)):
        if role["role_key"] == role_key:
            return role
    return None


def get_sect_effects(profile_data: dict[str, Any] | None) -> dict[str, int]:
    if not profile_data:
        return _zero_effects()
    sect = serialize_sect(get_sect(int(profile_data.get("sect_id") or 0))) if profile_data.get("sect_id") else None
    role = get_sect_role_payload(profile_data.get("sect_id"), profile_data.get("sect_role_key"))
    effects = _zero_effects()
    if sect:
        effects["attack_bonus"] += int(sect.get("attack_bonus", 0) or 0)
        effects["defense_bonus"] += int(sect.get("defense_bonus", 0) or 0)
        effects["duel_rate_bonus"] += int(sect.get("duel_rate_bonus", 0) or 0)
        effects["cultivation_bonus"] += int(sect.get("cultivation_bonus", 0) or 0)
        effects["fortune_bonus"] += int(sect.get("fortune_bonus", 0) or 0)
        effects["body_movement_bonus"] += int(sect.get("body_movement_bonus", 0) or 0)
    if role:
        effects["attack_bonus"] += int(role.get("attack_bonus", 0) or 0)
        effects["defense_bonus"] += int(role.get("defense_bonus", 0) or 0)
        effects["duel_rate_bonus"] += int(role.get("duel_rate_bonus", 0) or 0)
        effects["cultivation_bonus"] += int(role.get("cultivation_bonus", 0) or 0)
    return effects


def _default_role_payloads() -> list[dict[str, Any]]:
    rows = []
    for role_key, role_name, sort_order in SECT_ROLE_PRESETS:
        rows.append(
            {
                "role_key": role_key,
                "role_name": role_name,
                "attack_bonus": 0,
                "defense_bonus": 0,
                "duel_rate_bonus": 0,
                "cultivation_bonus": 0,
                "monthly_salary": 0,
                "can_publish_tasks": role_key in {"leader", "elder", "inner_deacon", "outer_deacon"},
                "sort_order": sort_order,
            }
        )
    return rows


def create_sect_with_roles(
    *,
    name: str,
    description: str = "",
    image_url: str = "",
    camp: str = "orthodox",
    min_realm_stage: str | None = None,
    min_realm_layer: int = 1,
    min_stone: int = 0,
    min_bone: int = 0,
    min_comprehension: int = 0,
    min_divine_sense: int = 0,
    min_fortune: int = 0,
    min_willpower: int = 0,
    min_charisma: int = 0,
    min_karma: int = 0,
    min_body_movement: int = 0,
    min_combat_power: int = 0,
    attack_bonus: int = 0,
    defense_bonus: int = 0,
    duel_rate_bonus: int = 0,
    cultivation_bonus: int = 0,
    fortune_bonus: int = 0,
    body_movement_bonus: int = 0,
    entry_hint: str = "",
    roles: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    sect = create_sect(
        name=name,
        description=description,
        image_url=image_url,
        camp=camp,
        min_realm_stage=min_realm_stage,
        min_realm_layer=max(int(min_realm_layer or 1), 1),
        min_stone=max(int(min_stone or 0), 0),
        min_bone=max(int(min_bone or 0), 0),
        min_comprehension=max(int(min_comprehension or 0), 0),
        min_divine_sense=max(int(min_divine_sense or 0), 0),
        min_fortune=max(int(min_fortune or 0), 0),
        min_willpower=max(int(min_willpower or 0), 0),
        min_charisma=max(int(min_charisma or 0), 0),
        min_karma=max(int(min_karma or 0), 0),
        min_body_movement=max(int(min_body_movement or 0), 0),
        min_combat_power=max(int(min_combat_power or 0), 0),
        attack_bonus=int(attack_bonus or 0),
        defense_bonus=int(defense_bonus or 0),
        duel_rate_bonus=int(duel_rate_bonus or 0),
        cultivation_bonus=int(cultivation_bonus or 0),
        fortune_bonus=int(fortune_bonus or 0),
        body_movement_bonus=int(body_movement_bonus or 0),
        entry_hint=entry_hint,
        enabled=True,
    )
    role_payloads = roles or _default_role_payloads()
    sanitized = []
    for index, role in enumerate(role_payloads, start=1):
        role_key = str(role.get("role_key") or "").strip() or f"role_{index}"
        sanitized.append(
            {
                "role_key": role_key,
                "role_name": str(role.get("role_name") or SECT_ROLE_LABELS.get(role_key, role_key)).strip(),
                "attack_bonus": int(role.get("attack_bonus", 0) or 0),
                "defense_bonus": int(role.get("defense_bonus", 0) or 0),
                "duel_rate_bonus": int(role.get("duel_rate_bonus", 0) or 0),
                "cultivation_bonus": int(role.get("cultivation_bonus", 0) or 0),
                "monthly_salary": int(role.get("monthly_salary", 0) or 0),
                "can_publish_tasks": bool(role.get("can_publish_tasks", False)),
                "sort_order": int(role.get("sort_order", index) or index),
            }
        )
    sect["roles"] = replace_sect_roles(sect["id"], sanitized)
    return sect


def sync_sect_with_roles_by_name(
    *,
    name: str,
    description: str = "",
    image_url: str = "",
    camp: str = "orthodox",
    min_realm_stage: str | None = None,
    min_realm_layer: int = 1,
    min_stone: int = 0,
    min_bone: int = 0,
    min_comprehension: int = 0,
    min_divine_sense: int = 0,
    min_fortune: int = 0,
    min_willpower: int = 0,
    min_charisma: int = 0,
    min_karma: int = 0,
    min_body_movement: int = 0,
    min_combat_power: int = 0,
    attack_bonus: int = 0,
    defense_bonus: int = 0,
    duel_rate_bonus: int = 0,
    cultivation_bonus: int = 0,
    fortune_bonus: int = 0,
    body_movement_bonus: int = 0,
    entry_hint: str = "",
    roles: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    existing = next((row for row in list_sects(enabled_only=False) if row.get("name") == name), None)
    if existing is None:
        return create_sect_with_roles(
            name=name,
            description=description,
            image_url=image_url,
            camp=camp,
            min_realm_stage=min_realm_stage,
            min_realm_layer=min_realm_layer,
            min_stone=min_stone,
            min_bone=min_bone,
            min_comprehension=min_comprehension,
            min_divine_sense=min_divine_sense,
            min_fortune=min_fortune,
            min_willpower=min_willpower,
            min_charisma=min_charisma,
            min_karma=min_karma,
            min_body_movement=min_body_movement,
            min_combat_power=min_combat_power,
            attack_bonus=attack_bonus,
            defense_bonus=defense_bonus,
            duel_rate_bonus=duel_rate_bonus,
            cultivation_bonus=cultivation_bonus,
            fortune_bonus=fortune_bonus,
            body_movement_bonus=body_movement_bonus,
            entry_hint=entry_hint,
            roles=roles,
        )
    updated = patch_sect(
        int(existing["id"]),
        name=name,
        description=description,
        image_url=image_url,
        camp=camp,
        min_realm_stage=min_realm_stage,
        min_realm_layer=min_realm_layer,
        min_stone=min_stone,
        min_bone=min_bone,
        min_comprehension=min_comprehension,
        min_divine_sense=min_divine_sense,
        min_fortune=min_fortune,
        min_willpower=min_willpower,
        min_charisma=min_charisma,
        min_karma=min_karma,
        min_body_movement=min_body_movement,
        min_combat_power=min_combat_power,
        attack_bonus=attack_bonus,
        defense_bonus=defense_bonus,
        duel_rate_bonus=duel_rate_bonus,
        cultivation_bonus=cultivation_bonus,
        fortune_bonus=fortune_bonus,
        body_movement_bonus=body_movement_bonus,
        entry_hint=entry_hint,
        enabled=True,
    ) or existing
    updated["roles"] = replace_sect_roles(int(existing["id"]), roles or _default_role_payloads())
    return updated


def _count_sect_members(sect_id: int) -> int:
    with Session() as session:
        return (
            session.query(XiuxianProfile)
            .filter(XiuxianProfile.sect_id == sect_id, XiuxianProfile.consented.is_(True))
            .count()
        )


def _parse_optional_datetime(raw: str | None) -> datetime | None:
    if not raw:
        return None
    try:
        return datetime.fromisoformat(str(raw))
    except ValueError:
        return None


def _format_remaining_delta(delta: timedelta) -> str:
    total_seconds = max(int(delta.total_seconds()), 0)
    days, rem = divmod(total_seconds, 86400)
    hours, rem = divmod(rem, 3600)
    minutes, _ = divmod(rem, 60)
    parts = []
    if days:
        parts.append(f"{days} 天")
    if hours:
        parts.append(f"{hours} 小时")
    if minutes or not parts:
        parts.append(f"{minutes} 分钟")
    return "".join(parts[:2])


def _sect_salary_min_stay_days() -> int:
    settings = get_xiuxian_settings()
    return max(int(settings.get("sect_salary_min_stay_days", DEFAULT_SETTINGS.get("sect_salary_min_stay_days", 30)) or 0), 1)


def _sect_betrayal_cooldown_days() -> int:
    settings = get_xiuxian_settings()
    return max(int(settings.get("sect_betrayal_cooldown_days", DEFAULT_SETTINGS.get("sect_betrayal_cooldown_days", 7)) or 0), 1)


def _sect_betrayal_stone_penalty(balance: int) -> int:
    settings = get_xiuxian_settings()
    current = max(int(balance or 0), 0)
    percent = max(int(settings.get("sect_betrayal_stone_percent", DEFAULT_SETTINGS.get("sect_betrayal_stone_percent", 10)) or 0), 0)
    minimum = max(int(settings.get("sect_betrayal_stone_min", DEFAULT_SETTINGS.get("sect_betrayal_stone_min", 20)) or 0), 0)
    maximum = max(int(settings.get("sect_betrayal_stone_max", DEFAULT_SETTINGS.get("sect_betrayal_stone_max", 300)) or 0), minimum)
    percent_penalty = (current * percent) // 100 if percent > 0 else 0
    return min(max(percent_penalty, minimum), maximum, current)


def _task_publish_day_window() -> tuple[datetime, datetime]:
    current = china_now()
    day_start = current.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(hours=8)
    return day_start, day_start + timedelta(days=1)


def _user_task_daily_limit() -> int:
    settings = get_xiuxian_settings()
    return max(int(settings.get("user_task_daily_limit", DEFAULT_SETTINGS.get("user_task_daily_limit", 3)) or 0), 0)


def _user_task_publish_count_today(tg: int, *, session: Session | None = None) -> int:
    day_start, day_end = _task_publish_day_window()
    owns_session = session is None
    active_session = session or Session()
    try:
        return int(
            active_session.query(XiuxianTask)
            .filter(
                XiuxianTask.owner_tg == int(tg),
                XiuxianTask.created_at >= day_start,
                XiuxianTask.created_at < day_end,
            )
            .count()
            or 0
        )
    finally:
        if owns_session:
            active_session.close()


def _scene_exploration_counts(tg: int) -> dict[int, int]:
    counts: dict[int, int] = {}
    with Session() as session:
        rows = session.query(XiuxianExploration.scene_id).filter(XiuxianExploration.tg == int(tg)).all()
    for row in rows:
        scene_id = int(getattr(row, "scene_id", row[0] if row else 0) or 0)
        if scene_id <= 0:
            continue
        counts[scene_id] = counts.get(scene_id, 0) + 1
    return counts


def _eligible_for_sect(profile_data: dict[str, Any], sect: dict[str, Any], combat_power: int = 0) -> tuple[bool, str]:
    betrayal_until = _parse_optional_datetime(profile_data.get("sect_betrayal_until"))
    if betrayal_until and betrayal_until > utcnow():
        return False, f"叛宗余罚未消，需再等 {_format_remaining_delta(betrayal_until - utcnow())} 方可重投山门"
    if sect.get("min_realm_stage") and realm_index(profile_data.get("realm_stage")) < realm_index(sect.get("min_realm_stage")):
        return False, "境界不满足宗门要求"
    if profile_data.get("realm_stage") == sect.get("min_realm_stage") and int(profile_data.get("realm_layer") or 0) < int(sect.get("min_realm_layer") or 1):
        return False, "层数不满足宗门要求"
    if int(profile_data.get("spiritual_stone") or 0) < int(sect.get("min_stone") or 0):
        return False, "灵石不满足宗门要求"
    if int(profile_data.get("bone") or 0) < int(sect.get("min_bone") or 0):
        return False, "根骨不满足宗门要求"
    if int(profile_data.get("comprehension") or 0) < int(sect.get("min_comprehension") or 0):
        return False, "悟性不满足宗门要求"
    if int(profile_data.get("divine_sense") or 0) < int(sect.get("min_divine_sense") or 0):
        return False, "神识不满足宗门要求"
    if int(profile_data.get("fortune") or 0) < int(sect.get("min_fortune") or 0):
        return False, "机缘不满足宗门要求"
    if int(profile_data.get("willpower") or 0) < int(sect.get("min_willpower") or 0):
        return False, "心志不满足宗门要求"
    if int(profile_data.get("charisma") or 0) < int(sect.get("min_charisma") or 0):
        return False, "魅力不满足宗门要求"
    if int(profile_data.get("karma") or 0) < int(sect.get("min_karma") or 0):
        return False, "因果不满足宗门要求"
    if int(profile_data.get("body_movement") or 0) < int(sect.get("min_body_movement") or 0):
        return False, "身法不满足宗门要求"
    if int(combat_power or 0) < int(sect.get("min_combat_power") or 0):
        return False, "战力不满足宗门要求"
    return True, ""


def list_sects_for_user(tg: int) -> list[dict[str, Any]]:
    profile_obj = get_profile(tg, create=True)
    profile = serialize_profile(profile_obj)
    combat_power = 0
    if profile and profile.get("consented") and not profile.get("death_at"):
        from bot.plugins.xiuxian_game.service import serialize_full_profile

        combat_power = int((serialize_full_profile(tg) or {}).get("combat_power") or 0)
    rows = []
    for sect in list_sects(enabled_only=True):
        sect["roles"] = list_sect_roles(sect["id"])
        sect["member_count"] = _count_sect_members(sect["id"])
        allowed, reason = _eligible_for_sect(profile, sect, combat_power=combat_power)
        sect["joinable"] = profile.get("sect_id") in {None, sect["id"]} and allowed
        sect["join_reason"] = "" if sect["joinable"] else reason or ("你已经加入其他宗门" if profile.get("sect_id") not in {None, sect["id"]} else "")
        rows.append(sect)
    return rows


def _get_sect_roster(sect_id: int) -> list[dict[str, Any]]:
    with Session() as session:
        rows = (
            session.query(XiuxianProfile)
            .filter(XiuxianProfile.sect_id == sect_id, XiuxianProfile.consented.is_(True))
            .order_by(XiuxianProfile.updated_at.desc())
            .all()
        )
        return [serialize_profile(row) for row in rows]


def get_current_sect_bundle(tg: int) -> dict[str, Any] | None:
    profile = serialize_profile(get_profile(tg, create=False))
    if not profile or not profile.get("sect_id"):
        return None
    sect = serialize_sect(get_sect(int(profile["sect_id"])))
    if not sect:
        return None
    sect["roles"] = list_sect_roles(sect["id"])
    sect["roster"] = _get_sect_roster(sect["id"])
    sect["current_role"] = get_sect_role_payload(sect["id"], profile.get("sect_role_key"))
    sect["leave_preview"] = {
        "stone_penalty": _sect_betrayal_stone_penalty(int(profile.get("spiritual_stone") or 0)),
        "cooldown_days": _sect_betrayal_cooldown_days(),
    }
    sect["can_leave"] = True
    return sect


def join_sect_for_user(tg: int, sect_id: int) -> dict[str, Any]:
    _, profile = _require_alive_profile_data(tg, "加入宗门")
    if profile.get("sect_id") and int(profile.get("sect_id")) == int(sect_id):
        raise ValueError("你已在该宗门门下，无需重复拜山。")
    if profile.get("sect_id") and int(profile.get("sect_id")) != int(sect_id):
        raise ValueError("你已加入其他宗门")
    sect = serialize_sect(get_sect(sect_id))
    if sect is None or not sect.get("enabled"):
        raise ValueError("宗门不存在")
    from bot.plugins.xiuxian_game.service import serialize_full_profile

    allowed, reason = _eligible_for_sect(profile, sect, combat_power=int((serialize_full_profile(tg) or {}).get("combat_power") or 0))
    if not allowed:
        raise ValueError(reason)
    upsert_profile(
        tg,
        sect_id=sect_id,
        sect_role_key="outer_disciple",
        sect_joined_at=utcnow(),
        sect_betrayal_until=None,
    )
    create_journal(tg, "sect", "加入宗门", f"重整衣冠，拜入宗门【{sect['name']}】门下。")
    return get_current_sect_bundle(tg)


def leave_sect_for_user(tg: int) -> dict[str, Any]:
    current = get_current_sect_bundle(tg)
    if not current:
        raise ValueError("你当前并未加入宗门")
    with Session() as session:
        profile = session.query(XiuxianProfile).filter(XiuxianProfile.tg == tg).with_for_update().first()
        if profile is None or not profile.consented:
            raise ValueError("你还没有踏入仙途")
        assert_profile_alive(profile, "叛出宗门")
        assert_currency_operation_allowed(tg, "叛出宗门", session=session, profile=profile)
        if not profile.sect_id:
            raise ValueError("你当前并未加入宗门")

        current_stone = max(int(profile.spiritual_stone or 0), 0)
        penalty = _sect_betrayal_stone_penalty(current_stone)
        if current_stone < penalty:
            raise ValueError(f"叛出宗门需要缴纳 {penalty} 灵石供奉，你当前灵石不足。")
        cooldown_until = utcnow() + timedelta(days=_sect_betrayal_cooldown_days())
        previous_contribution = int(profile.sect_contribution or 0)
        apply_spiritual_stone_delta(
            session,
            tg,
            -penalty,
            action_text="叛出宗门",
            allow_dead=False,
            apply_tribute=False,
        )
        profile.sect_id = None
        profile.sect_role_key = None
        profile.sect_contribution = 0
        profile.sect_joined_at = None
        profile.sect_betrayal_until = cooldown_until
        profile.last_salary_claim_at = None
        profile.updated_at = utcnow()
        session.commit()

    sect_name = (current or {}).get("name", "未知宗门")
    create_journal(
        tg,
        "sect",
        "叛出宗门",
        f"叛出宗门【{sect_name}】，被收回 {penalty} 灵石供奉，清空 {previous_contribution} 点宗门贡献，并禁投山门至 {cooldown_until.isoformat()}。",
    )
    return {
        "previous_sect": current,
        "profile": serialize_profile(get_profile(tg, create=False)),
        "betrayal": {
            "stone_penalty": penalty,
            "contribution_cleared": previous_contribution,
            "cooldown_until": cooldown_until.isoformat(),
            "cooldown_days": _sect_betrayal_cooldown_days(),
        },
    }


def set_user_sect_role(tg: int, sect_id: int, role_key: str) -> dict[str, Any]:
    sect = serialize_sect(get_sect(sect_id))
    if sect is None or not sect.get("enabled"):
        raise ValueError("宗门不存在")
    role = get_sect_role_payload(sect_id, role_key)
    if role is None:
        raise ValueError("宗门职位不存在")
    profile_obj = get_profile(tg, create=False)
    if profile_obj is None or not profile_obj.consented:
        raise ValueError("目标用户尚未踏入仙途")
    assert_profile_alive(profile_obj, "调整宗门职位")
    profile_payload = {"sect_id": sect_id, "sect_role_key": role_key}
    if int(profile_obj.sect_id or 0) != int(sect_id):
        profile_payload["sect_joined_at"] = utcnow()
        profile_payload["sect_betrayal_until"] = None
    updated = upsert_profile(tg, **profile_payload)
    return {"profile": serialize_profile(updated), "role": role, "sect": sect}


def claim_sect_salary_for_user(tg: int) -> dict[str, Any]:
    profile_obj, _ = _require_alive_profile_data(tg, "领取宗门俸禄")
    assert_currency_operation_allowed(tg, "领取宗门俸禄", profile=profile_obj)
    role = get_sect_role_payload(profile_obj.sect_id, profile_obj.sect_role_key)
    if not role:
        raise ValueError("当前没有宗门俸禄可领取")
    now = utcnow()
    joined_at = profile_obj.sect_joined_at or profile_obj.last_salary_claim_at or profile_obj.created_at or now
    last_claim = profile_obj.last_salary_claim_at
    if last_claim is None or last_claim < joined_at:
        min_stay = timedelta(days=_sect_salary_min_stay_days())
        if now - joined_at < min_stay:
            remaining = min_stay - (now - joined_at)
            raise ValueError(f"新入门弟子仍在考察期，需再留宗 {_format_remaining_delta(remaining)} 才能领取俸禄。")
    elif now - last_claim < timedelta(days=30):
        remaining = timedelta(days=30) - (now - last_claim)
        raise ValueError(f"距离下次领取俸禄还需 {_format_remaining_delta(remaining)}。")
    salary = int(role.get("monthly_salary", 0) or 0)
    with Session() as session:
        updated = session.query(XiuxianProfile).filter(XiuxianProfile.tg == tg).with_for_update().first()
        if updated is None or not updated.consented:
            raise ValueError("你还没有踏入仙途")
        apply_spiritual_stone_delta(session, tg, salary, action_text="领取宗门俸禄", apply_tribute=True)
        updated.last_salary_claim_at = now
        updated.updated_at = now
        session.commit()
    create_journal(tg, "sect", "领取俸禄", f"领取了 {salary} 灵石的宗门俸禄")
    return {"salary": salary, "profile": _full_profile_bundle(tg)["profile"], "role": role}


def _can_publish_sect_task(tg: int) -> bool:
    profile = serialize_profile(get_profile(tg, create=False))
    if not profile or not profile.get("sect_id"):
        return False
    role = get_sect_role_payload(profile.get("sect_id"), profile.get("sect_role_key"))
    return bool(role and role.get("can_publish_tasks"))


def _normalize_quiz_answer_text(answer_text: str | None) -> str:
    raw = str(answer_text or "").strip().casefold()
    raw = raw.strip("，。！？!?；;：:,.、 ")
    return re.sub(r"\s+", "", raw)


def _meaningful_text_length(value: str | None) -> int:
    raw = str(value or "").strip()
    if not raw:
        return 0
    normalized = re.sub(r"[^\w\u4e00-\u9fff]+", "", raw, flags=re.UNICODE)
    return len(normalized or re.sub(r"\s+", "", raw))


def create_bounty_task(
    *,
    actor_tg: int | None,
    title: str,
    description: str,
    task_scope: str,
    task_type: str,
    question_text: str = "",
    answer_text: str = "",
    image_url: str = "",
    required_item_kind: str | None = None,
    required_item_ref_id: int | None = None,
    required_item_quantity: int = 0,
    reward_stone: int = 0,
    reward_item_kind: str | None = None,
    reward_item_ref_id: int | None = None,
    reward_item_quantity: int = 0,
    max_claimants: int = 1,
    sect_id: int | None = None,
    active_in_group: bool = False,
    group_chat_id: int | None = None,
) -> dict[str, Any]:
    title_value = str(title or "").strip()
    description_value = str(description or "").strip()
    question_value = str(question_text or "").strip()
    image_value = str(image_url or "").strip()
    task_scope_value = str(task_scope or "personal").strip() or "personal"
    task_type_value = str(task_type or "custom").strip() or "custom"
    normalized_answer = _normalize_quiz_answer_text(answer_text)
    should_push_group = bool(active_in_group)
    required_kind = str(required_item_kind or "").strip() or None
    required_ref = int(required_item_ref_id or 0) or None
    required_qty = max(int(required_item_quantity or 0), 0)
    reward_kind = str(reward_item_kind or "").strip() or None
    reward_ref = int(reward_item_ref_id or 0) or None
    reward_qty = max(int(reward_item_quantity or 0), 0)
    reward_stone_value = max(int(reward_stone or 0), 0)
    publish_cost = 0

    if task_scope_value not in {"official", "sect", "personal"}:
        raise ValueError("任务范围不支持")
    if task_type_value not in {"quiz", "custom"}:
        raise ValueError("任务类型不支持")
    if actor_tg is not None and task_scope_value == "official":
        raise ValueError("玩家不能发布官方任务")
    if _meaningful_text_length(title_value) < 2:
        raise ValueError("任务标题至少填写 2 个字")

    if task_type_value == "quiz":
        if _meaningful_text_length(question_value) < 4:
            raise ValueError("答题任务必须填写清晰的题目内容")
        if not normalized_answer:
            raise ValueError("答题任务必须填写标准答案")
        if not group_chat_id:
            raise ValueError("答题任务必须绑定群聊后才能发布")
        if required_kind:
            raise ValueError("答题任务暂不支持提交物品")
        should_push_group = True
        max_claimants = 1
    elif _meaningful_text_length(description_value) < 6:
        raise ValueError("普通任务必须填写至少 6 个字的任务说明")

    if required_kind:
        if required_kind not in {"artifact", "pill", "talisman", "material"}:
            raise ValueError("任务提交物类型不支持")
        if required_ref is None:
            raise ValueError("请选择任务需要提交的物品")
        if required_qty <= 0:
            raise ValueError("任务提交物数量必须大于 0")
        if _get_item_payload(required_kind, required_ref) is None:
            raise ValueError("任务提交物不存在")
    else:
        required_ref = None
        required_qty = 0

    if reward_kind:
        if reward_kind not in {"artifact", "pill", "talisman", "material"}:
            raise ValueError("任务奖励物类型不支持")
        if reward_ref is None:
            raise ValueError("请选择任务奖励物")
        if reward_qty <= 0:
            raise ValueError("任务奖励物数量必须大于 0")
        if _get_item_payload(reward_kind, reward_ref) is None:
            raise ValueError("任务奖励物不存在")
    else:
        reward_ref = None
        reward_qty = 0

    if reward_stone_value <= 0 and not reward_kind:
        raise ValueError("悬赏任务必须设置奖励，不能发布无奖励任务")

    actor_profile = None
    settings = get_xiuxian_settings()
    if actor_tg is not None:
        # 玩家发布任务先过开关、身份与灵石扣费三道校验。
        if not bool(settings.get("allow_user_task_publish", DEFAULT_SETTINGS.get("allow_user_task_publish", True))):
            raise ValueError("当前未开放玩家发布任务")
        actor_obj, actor_profile = _require_alive_profile_data(actor_tg, "发布任务")
        assert_currency_operation_allowed(actor_tg, "发布任务", profile=actor_obj)
        publish_cost = max(int(settings.get("task_publish_cost", DEFAULT_SETTINGS.get("task_publish_cost", 0)) or 0), 0)
        daily_limit = _user_task_daily_limit()
        published_today = _user_task_publish_count_today(actor_tg)
        if daily_limit > 0 and published_today >= daily_limit:
            raise ValueError(f"你今日已发布 {published_today} 次悬赏，已达到上限 {daily_limit} 次。")

    if task_scope_value == "sect":
        if actor_tg is None:
            if not sect_id:
                raise ValueError("宗门任务必须指定宗门")
        else:
            if not _can_publish_sect_task(actor_tg):
                raise ValueError("当前身份无法发布宗门任务")
            sect_id = int(actor_profile.get("sect_id") or 0)
            if not sect_id:
                raise ValueError("你尚未加入宗门")

    with Session() as session:
        if actor_tg is not None:
            # 发布时对玩家记录加锁，防止并发发任务导致灵石重复扣减或余额穿透。
            publisher = session.query(XiuxianProfile).filter(XiuxianProfile.tg == actor_tg).with_for_update().first()
            if publisher is None or not publisher.consented:
                raise ValueError("你还没有踏入仙途")
            if publish_cost > 0:
                apply_spiritual_stone_delta(
                    session,
                    actor_tg,
                    -publish_cost,
                    action_text="发布任务",
                    enforce_currency_lock=False,
                    allow_dead=False,
                    apply_tribute=False,
                )

        task_row = XiuxianTask(
            title=title_value,
            description=description_value or None,
            task_scope=task_scope_value,
            task_type=task_type_value,
            owner_tg=actor_tg,
            sect_id=sect_id,
            question_text=question_value or None,
            answer_text=normalized_answer or None,
            image_url=image_value or None,
            required_item_kind=required_kind,
            required_item_ref_id=required_ref,
            required_item_quantity=required_qty,
            reward_stone=reward_stone_value,
            reward_item_kind=reward_kind,
            reward_item_ref_id=reward_ref,
            reward_item_quantity=reward_qty,
            max_claimants=max(int(max_claimants or 1), 1),
            active_in_group=should_push_group,
            group_chat_id=group_chat_id,
            status="open",
            enabled=True,
        )
        session.add(task_row)
        session.commit()
        session.refresh(task_row)
        payload = _decorate_task_payload(serialize_task(task_row))

    if payload is not None and actor_tg is not None:
        payload["publish_cost"] = publish_cost
    return payload


def list_task_claims_for_user(tg: int) -> list[dict[str, Any]]:
    with Session() as session:
        rows = (
            session.query(XiuxianTaskClaim)
            .filter(XiuxianTaskClaim.tg == tg)
            .order_by(XiuxianTaskClaim.id.desc())
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


def list_tasks_for_user(tg: int) -> list[dict[str, Any]]:
    profile = serialize_profile(get_profile(tg, create=False)) or {}
    claims_by_task = {claim["task_id"]: claim for claim in list_task_claims_for_user(tg)}
    rows = []
    for task in list_tasks(enabled_only=True):
        if task["status"] not in {"open", "active"}:
            continue
        if task["task_scope"] == "sect" and int(task.get("sect_id") or 0) != int(profile.get("sect_id") or 0):
            continue
        task["claimed"] = task["id"] in claims_by_task or int(task.get("winner_tg") or 0) == int(tg)
        task["claim"] = claims_by_task.get(task["id"])
        task["can_cancel"] = (
            int(task.get("owner_tg") or 0) == int(tg)
            and task.get("status") in {"open", "active"}
            and not int(task.get("winner_tg") or 0)
        )
        rows.append(_decorate_task_payload(task))
    return rows


def cancel_task_for_user(tg: int, task_id: int) -> dict[str, Any]:
    profile = serialize_profile(get_profile(tg, create=False))
    if not profile or not profile.get("consented"):
        raise ValueError("你还没有踏入仙途")
    with Session() as session:
        task = session.query(XiuxianTask).filter(XiuxianTask.id == task_id).with_for_update().first()
        if task is None or not task.enabled:
            raise ValueError("任务不存在")
        if int(task.owner_tg or 0) != int(tg):
            raise ValueError("只有发布者本人才能撤销任务")
        if task.status not in {"open", "active"}:
            raise ValueError("当前任务状态不允许撤销")
        if int(task.winner_tg or 0):
            raise ValueError("任务已经完成，不能撤销")
        claims = (
            session.query(XiuxianTaskClaim)
            .filter(XiuxianTaskClaim.task_id == task_id)
            .with_for_update()
            .all()
        )
        for claim in claims:
            if claim.status == "completed":
                raise ValueError("任务已经完成，不能撤销")
            claim.status = "cancelled"
        task.status = "cancelled"
        task.active_in_group = False
        task.updated_at = utcnow()
        session.commit()
        session.refresh(task)
        serialized = _decorate_task_payload(serialize_task(task))
    create_journal(tg, "task", "撤销任务", f"主动撤销了任务【{serialized['title']}】")
    return {"task": serialized}


def _decorate_task_payload(task: dict[str, Any] | None) -> dict[str, Any] | None:
    if task is None:
        return None
    payload = dict(task)
    if payload.get("required_item_kind") and payload.get("required_item_ref_id"):
        payload["required_item"] = _get_item_payload(payload["required_item_kind"], int(payload["required_item_ref_id"]))
    else:
        payload["required_item"] = None
    if payload.get("reward_item_kind") and payload.get("reward_item_ref_id"):
        payload["reward_item"] = _get_item_payload(payload["reward_item_kind"], int(payload["reward_item_ref_id"]))
    else:
        payload["reward_item"] = None
    return payload


def _required_item_name(kind: str, ref_id: int) -> str:
    item = _get_item_payload(kind, ref_id)
    if item and item.get("name"):
        return str(item["name"])
    return f"{kind}#{ref_id}"


def _consume_required_item(
    session: Session,
    tg: int,
    item_kind: str,
    item_ref_id: int,
    quantity: int,
) -> dict[str, Any]:
    amount = max(int(quantity or 0), 1)
    item = _get_item_payload(item_kind, int(item_ref_id))
    if item is None:
        raise ValueError("任务要求的提交物不存在")

    row = None
    if item_kind == "artifact":
        row = (
            session.query(XiuxianArtifactInventory)
            .filter(XiuxianArtifactInventory.tg == tg, XiuxianArtifactInventory.artifact_id == item_ref_id)
            .with_for_update()
            .first()
        )
    elif item_kind == "pill":
        row = (
            session.query(XiuxianPillInventory)
            .filter(XiuxianPillInventory.tg == tg, XiuxianPillInventory.pill_id == item_ref_id)
            .with_for_update()
            .first()
        )
    elif item_kind == "talisman":
        row = (
            session.query(XiuxianTalismanInventory)
            .filter(XiuxianTalismanInventory.tg == tg, XiuxianTalismanInventory.talisman_id == item_ref_id)
            .with_for_update()
            .first()
        )
    elif item_kind == "material":
        row = (
            session.query(XiuxianMaterialInventory)
            .filter(XiuxianMaterialInventory.tg == tg, XiuxianMaterialInventory.material_id == item_ref_id)
            .with_for_update()
            .first()
        )
    else:
        raise ValueError("暂不支持该类型的提交物")

    if row is None or int(row.quantity or 0) < amount:
        raise ValueError(f"提交所需物品不足：{item.get('name', '未知物品')} × {amount}")

    if item_kind == "artifact":
        bound_quantity = max(min(int(row.bound_quantity or 0), int(row.quantity or 0)), 0)
        equipped_count = (
            session.query(XiuxianEquippedArtifact)
            .filter(
                XiuxianEquippedArtifact.tg == tg,
                XiuxianEquippedArtifact.artifact_id == item_ref_id,
            )
            .count()
        )
        available_quantity = int(row.quantity or 0) - bound_quantity - int(equipped_count or 0)
        if available_quantity < amount:
            raise ValueError(f"提交所需法宝不足，已绑定或已装备的法宝无法提交：{item.get('name', '未知物品')} × {amount}")
    elif item_kind == "talisman":
        bound_quantity = max(min(int(row.bound_quantity or 0), int(row.quantity or 0)), 0)
        available_quantity = int(row.quantity or 0) - bound_quantity
        if available_quantity < amount:
            raise ValueError(f"提交所需符箓不足，已绑定的符箓无法提交：{item.get('name', '未知物品')} × {amount}")

    row.quantity -= amount
    row.updated_at = utcnow()
    if row.quantity <= 0:
        session.delete(row)
    return item


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


def _award_task_rewards(tg: int, task: XiuxianTask) -> dict[str, Any]:
    with Session() as session:
        updated = session.query(XiuxianProfile).filter(XiuxianProfile.tg == tg).with_for_update().first()
        if updated is None:
            raise ValueError("用户不存在")
        apply_spiritual_stone_delta(
            session,
            tg,
            int(task.reward_stone or 0),
            action_text="领取任务奖励",
            allow_dead=False,
            apply_tribute=True,
        )
        session.commit()
    reward_item = None
    if task.reward_item_kind and task.reward_item_ref_id and int(task.reward_item_quantity or 0) > 0:
        reward_item = _grant_item_by_kind(tg, task.reward_item_kind, int(task.reward_item_ref_id), int(task.reward_item_quantity))
    return {
        "profile": _full_profile_bundle(tg)["profile"],
        "reward_stone": int(task.reward_stone or 0),
        "reward_item": reward_item,
    }


def mark_task_group_message(task_id: int, chat_id: int, message_id: int) -> dict[str, Any]:
    with Session() as session:
        task = session.query(XiuxianTask).filter(XiuxianTask.id == task_id).first()
        if task is None:
            raise ValueError("任务不存在")
        task.active_in_group = True
        task.group_chat_id = chat_id
        task.group_message_id = message_id
        task.status = "active"
        task.updated_at = utcnow()
        session.commit()
        session.refresh(task)
        return serialize_task(task)


def active_quiz_tasks_for_group(chat_id: int) -> list[dict[str, Any]]:
    with Session() as session:
        rows = (
            session.query(XiuxianTask)
            .filter(
                XiuxianTask.group_chat_id == chat_id,
                XiuxianTask.active_in_group.is_(True),
                XiuxianTask.task_type == "quiz",
                XiuxianTask.status.in_(["open", "active"]),
                XiuxianTask.enabled.is_(True),
            )
            .order_by(XiuxianTask.id.asc())
            .all()
        )
        return [serialize_task(row) for row in rows]





def _get_item_payload(kind: str, ref_id: int) -> dict[str, Any] | None:
    if kind == "artifact":
        from bot.sql_helper.sql_xiuxian import serialize_artifact

        return serialize_artifact(get_artifact(ref_id))
    if kind == "pill":
        from bot.sql_helper.sql_xiuxian import serialize_pill

        return serialize_pill(get_pill(ref_id))
    if kind == "talisman":
        from bot.sql_helper.sql_xiuxian import serialize_talisman

        return serialize_talisman(get_talisman(ref_id))
    if kind == "material":
        return serialize_material(get_material(ref_id))
    if kind == "technique":
        return serialize_technique(get_technique(ref_id))
    if kind == "recipe":
        recipe = serialize_recipe(get_recipe(ref_id))
        if recipe:
            recipe["result_item"] = _get_item_payload(str(recipe.get("result_kind") or ""), int(recipe.get("result_ref_id") or 0))
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
            _get_item_payload(str(item.get("result_kind") or ""), int(item.get("result_ref_id") or 0)),
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


def create_recipe_with_ingredients(
    *,
    name: str,
    recipe_kind: str,
    result_kind: str,
    result_ref_id: int,
    result_quantity: int,
    base_success_rate: int,
    broadcast_on_success: bool,
    ingredients: list[dict[str, Any]],
) -> dict[str, Any]:
    recipe = create_recipe(
        name=name,
        recipe_kind=recipe_kind,
        result_kind=result_kind,
        result_ref_id=result_ref_id,
        result_quantity=max(int(result_quantity or 1), 1),
        base_success_rate=max(min(int(base_success_rate or 60), 100), 1),
        broadcast_on_success=bool(broadcast_on_success),
        enabled=True,
    )
    recipe["ingredients"] = replace_recipe_ingredients(
        recipe["id"],
        [
            {
                "material_id": int(item.get("material_id") or 0),
                "quantity": max(int(item.get("quantity") or 1), 1),
            }
            for item in ingredients
        ],
    )
    return recipe


def build_recipe_catalog(tg: int | None = None) -> list[dict[str, Any]]:
    rows = []
    source_rows: list[dict[str, Any]]
    if tg is None:
        source_rows = list_recipes(enabled_only=True)
    else:
        source_rows = []
        for row in list_user_recipes(tg, enabled_only=True):
            recipe = dict(row.get("recipe") or {})
            if not recipe:
                continue
            recipe["owned"] = True
            recipe["source"] = row.get("source")
            recipe["obtained_note"] = row.get("obtained_note")
            source_rows.append(recipe)
    for recipe in source_rows:
        recipe["ingredients"] = list_recipe_ingredients(recipe["id"])
        recipe["result_item"] = _get_item_payload(recipe["result_kind"], int(recipe["result_ref_id"]))
        recipe.setdefault("owned", True)
        rows.append(recipe)
    return rows


def sync_recipe_with_ingredients_by_name(
    *,
    name: str,
    recipe_kind: str,
    result_kind: str,
    result_ref_id: int,
    result_quantity: int,
    base_success_rate: int,
    broadcast_on_success: bool,
    ingredients: list[dict[str, Any]],
) -> dict[str, Any]:
    payload = {
        "name": str(name or "").strip(),
        "recipe_kind": str(recipe_kind or "").strip() or "artifact",
        "result_kind": str(result_kind or "").strip() or "material",
        "result_ref_id": max(int(result_ref_id or 0), 1),
        "result_quantity": max(int(result_quantity or 1), 1),
        "base_success_rate": max(min(int(base_success_rate or 60), 100), 1),
        "broadcast_on_success": bool(broadcast_on_success),
        "enabled": True,
    }
    with Session() as session:
        recipe = session.query(XiuxianRecipe).filter(XiuxianRecipe.name == payload["name"]).first()
        if recipe is None:
            recipe = XiuxianRecipe(**payload)
            session.add(recipe)
            session.commit()
            session.refresh(recipe)
        else:
            for key, value in payload.items():
                setattr(recipe, key, value)
            recipe.updated_at = utcnow()
            session.commit()
            session.refresh(recipe)
        recipe_id = int(recipe.id)
    recipe_payload = serialize_recipe(get_recipe(recipe_id))
    recipe_payload["ingredients"] = replace_recipe_ingredients(
        recipe_id,
        [
            {
                "material_id": int(item.get("material_id") or 0),
                "quantity": max(int(item.get("quantity") or 1), 1),
            }
            for item in ingredients
            if int(item.get("material_id") or 0) > 0
        ],
    )
    recipe_payload["result_item"] = _get_item_payload(payload["result_kind"], payload["result_ref_id"])
    return recipe_payload


def patch_recipe_with_ingredients(
    recipe_id: int,
    *,
    name: str,
    recipe_kind: str,
    result_kind: str,
    result_ref_id: int,
    result_quantity: int,
    base_success_rate: int,
    broadcast_on_success: bool,
    ingredients: list[dict[str, Any]],
) -> dict[str, Any]:
    with Session() as session:
        recipe = session.query(XiuxianRecipe).filter(XiuxianRecipe.id == recipe_id).first()
        if recipe is None:
            raise ValueError("配方不存在")
        recipe.name = str(name or "").strip()
        recipe.recipe_kind = str(recipe_kind or "").strip() or recipe.recipe_kind
        recipe.result_kind = str(result_kind or "").strip() or recipe.result_kind
        recipe.result_ref_id = max(int(result_ref_id or 0), 1)
        recipe.result_quantity = max(int(result_quantity or 1), 1)
        recipe.base_success_rate = max(min(int(base_success_rate or 60), 100), 1)
        recipe.broadcast_on_success = bool(broadcast_on_success)
        recipe.enabled = True
        recipe.updated_at = utcnow()
        session.commit()
    recipe_payload = serialize_recipe(get_recipe(recipe_id))
    recipe_payload["ingredients"] = replace_recipe_ingredients(
        recipe_id,
        [
            {
                "material_id": int(item.get("material_id") or 0),
                "quantity": max(int(item.get("quantity") or 1), 1),
            }
            for item in ingredients
            if int(item.get("material_id") or 0) > 0
        ],
    )
    recipe_payload["result_item"] = _get_item_payload(recipe_payload["result_kind"], int(recipe_payload["result_ref_id"]))
    return recipe_payload


def sync_scene_with_drops_by_name(
    *,
    name: str,
    description: str = "",
    image_url: str = "",
    max_minutes: int = 60,
    event_pool: list[dict[str, Any]] | list[str] | None = None,
    drops: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    payload = {
        "name": str(name or "").strip(),
        "description": str(description or "").strip(),
        "image_url": str(image_url or "").strip(),
        "max_minutes": max(min(int(max_minutes or 60), 60), 1),
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


def patch_scene_with_drops(
    scene_id: int,
    *,
    name: str,
    description: str = "",
    image_url: str = "",
    max_minutes: int = 60,
    event_pool: list[dict[str, Any]] | list[str] | None = None,
    drops: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    with Session() as session:
        scene = session.query(XiuxianScene).filter(XiuxianScene.id == scene_id).first()
        if scene is None:
            raise ValueError("场景不存在")
        scene.name = str(name or "").strip()
        scene.description = str(description or "").strip()
        scene.image_url = str(image_url or "").strip() or None
        scene.max_minutes = max(min(int(max_minutes or 60), 60), 1)
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
) -> dict[str, Any]:
    event = _weighted_random_choice(scene.get("event_pool") or []) or {}
    stone_bonus = 0
    stone_loss = 0
    bonus_reward = None
    if event:
        stone_bonus_min = max(int(event.get("stone_bonus_min") or 0), 0)
        stone_bonus_max = max(int(event.get("stone_bonus_max") or stone_bonus_min), stone_bonus_min)
        if stone_bonus_max > 0:
            stone_bonus = random.randint(stone_bonus_min, stone_bonus_max)
        stone_loss_min = max(int(event.get("stone_loss_min") or 0), 0)
        stone_loss_max = max(int(event.get("stone_loss_max") or stone_loss_min), stone_loss_min)
        if stone_loss_max > 0:
            mitigation = max(fortune // 4 + divine_sense // 6, 0)
            stone_loss = max(random.randint(stone_loss_min, stone_loss_max) - mitigation, 0)
        bonus_reward_kind = event.get("bonus_reward_kind")
        bonus_reward_ref_id = int(event.get("bonus_reward_ref_id") or 0)
        bonus_chance = max(min(int(event.get("bonus_chance") or 0), 100), 0)
        if bonus_reward_kind and bonus_reward_ref_id > 0 and roll_probability_percent(bonus_chance)["success"]:
            bonus_quantity_min = max(int(event.get("bonus_quantity_min") or 1), 1)
            bonus_quantity_max = max(int(event.get("bonus_quantity_max") or bonus_quantity_min), bonus_quantity_min)
            bonus_reward = {
                "kind": bonus_reward_kind,
                "ref_id": bonus_reward_ref_id,
                "quantity": random.randint(bonus_quantity_min, bonus_quantity_max),
                "is_recipe_like": _recipe_like_bonus_item(bonus_reward_kind, bonus_reward_ref_id),
            }
    parts = []
    if event.get("name"):
        parts.append(str(event.get("name")))
    if chosen_drop.get("event_text"):
        parts.append(str(chosen_drop.get("event_text")))
    if event.get("description"):
        parts.append(str(event.get("description")))
    return {
        "event": event,
        "stone_bonus": stone_bonus,
        "stone_loss": stone_loss,
        "bonus_reward": bonus_reward,
        "event_text": "，".join([part for part in parts if part]).strip("，"),
    }


def craft_recipe_for_user(tg: int, recipe_id: int) -> dict[str, Any]:
    recipe = serialize_recipe(get_recipe(recipe_id))
    if recipe is None or not recipe.get("enabled"):
        raise ValueError("配方不存在")
    if not any(int((row.get("recipe") or {}).get("id") or 0) == int(recipe_id) for row in list_user_recipes(tg, enabled_only=True)):
        raise ValueError("你尚未掌握这张配方，无法开炉炼制")
    profile = serialize_profile(get_profile(tg, create=False))
    if not profile or not profile.get("consented"):
        raise ValueError("你还没有踏入仙途")
    ingredients = list_recipe_ingredients(recipe_id)
    if not ingredients:
        raise ValueError("该配方还没有配置材料")
    result_item = _get_item_payload(recipe["result_kind"], int(recipe["result_ref_id"]))
    if result_item is None:
        raise ValueError("该配方的成品配置无效，请联系管理员修复后再炼制")
    inventory_map = {row["material"]["id"]: row for row in list_user_materials(tg)}
    total_quality = 0
    total_count = 0
    with Session() as session:
        for item in ingredients:
            material_id = int(item["material_id"])
            owned = inventory_map.get(material_id)
            if owned is None or int(owned["quantity"] or 0) < int(item["quantity"] or 0):
                raise ValueError(f"材料不足：{item['material']['name']}")
            row = (
                session.query(XiuxianMaterialInventory)
                .filter(XiuxianMaterialInventory.tg == tg, XiuxianMaterialInventory.material_id == material_id)
                .with_for_update()
                .first()
            )
            if row is None or row.quantity < int(item["quantity"] or 0):
                raise ValueError("材料数量已变更，请重新尝试")
            row.quantity -= int(item["quantity"] or 0)
            row.updated_at = utcnow()
            if row.quantity <= 0:
                session.delete(row)
            total_quality += int(item["material"].get("quality_level", 1) or 1) * int(item["quantity"] or 0)
            total_count += int(item["quantity"] or 0)
        session.commit()
    result_quality = _quality_from_item(recipe["result_kind"], result_item)
    avg_material_quality = total_quality / max(total_count, 1)
    sect_effects = get_sect_effects(profile)
    comprehension = int(profile.get("comprehension") or 0)
    fortune = int(profile.get("fortune") or 0)
    root_quality_level = int(profile.get("root_quality_level") or 1)
    quality_bonus = int(avg_material_quality * 4) - result_quality * 6
    attribute_bonus = max(comprehension - 12, 0) // 2 + max(fortune - 10, 0) // 3 + root_quality_level * 2
    success_rate = (
        int(recipe["base_success_rate"])
        + quality_bonus
        + attribute_bonus
        + int(sect_effects.get("cultivation_bonus", 0))
    )
    if str(profile.get("root_quality") or "") == "天灵根":
        success_rate += 4
    elif str(profile.get("root_quality") or "") == "变异灵根":
        success_rate += 3
    success_rate = max(min(success_rate, 95), 5)
    success_roll = roll_probability_percent(
        success_rate,
        actor_fortune=fortune,
        actor_weight=0.25,
        minimum=5,
        maximum=95,
    )
    roll = success_roll["roll"]
    success_rate = success_roll["chance"]
    success = bool(success_roll["success"])
    reward = None
    if success:
        reward = _grant_item_by_kind(tg, recipe["result_kind"], int(recipe["result_ref_id"]), int(recipe["result_quantity"]))
        create_journal(tg, "craft", "炼制成功", f"成功炼制【{(result_item or {}).get('name', '成品')}】")
    else:
        create_journal(tg, "craft", "炼制失败", f"尝试炼制【{(result_item or {}).get('name', '成品')}】但失败了")
    ingredient_names = {str((item.get("material") or {}).get("name") or "") for item in ingredients}
    is_repair_recipe = any("破损" in name or "残片" in name for name in ingredient_names) or "修复" in str(recipe.get("name") or "")
    achievement_unlocks = record_craft_metrics(tg, success=success, repair_success=bool(success and is_repair_recipe))
    return {
        "success": success,
        "roll": roll,
        "success_rate": success_rate,
        "recipe": recipe,
        "result_item": result_item,
        "result_quality": result_quality,
        "reward": reward,
        "should_broadcast": bool(success and recipe.get("broadcast_on_success") and result_quality >= int(get_xiuxian_settings().get("high_quality_broadcast_level", DEFAULT_SETTINGS["high_quality_broadcast_level"]) or 4)),
        "profile": serialize_profile(get_profile(tg, create=False)),
        "achievement_unlocks": achievement_unlocks,
    }


def create_scene_with_drops(
    *,
    name: str,
    description: str = "",
    image_url: str = "",
    max_minutes: int = 60,
    event_pool: list[str] | None = None,
    drops: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    scene = create_scene(
        name=name,
        description=description,
        image_url=image_url,
        max_minutes=max(min(int(max_minutes or 60), 60), 1),
        event_pool=event_pool or [],
        enabled=True,
    )
    created_drops = []
    for drop in drops or []:
        created_drops.append(
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
        )
    scene["drops"] = created_drops
    return scene


def _get_active_exploration(tg: int) -> dict[str, Any] | None:
    with Session() as session:
        row = (
            session.query(XiuxianExploration)
            .filter(XiuxianExploration.tg == tg, XiuxianExploration.claimed.is_(False))
            .order_by(XiuxianExploration.id.desc())
            .first()
        )
        return serialize_exploration(row)


def start_exploration_for_user(tg: int, scene_id: int, minutes: int) -> dict[str, Any]:
    _, profile = _require_alive_profile_data(tg, "进入秘境")
    active = _get_active_exploration(tg)
    if active and not active.get("claimed"):
        raise ValueError("你还有未结算的探索")
    scene = serialize_scene(get_scene(scene_id))
    if not scene or not scene.get("enabled"):
        raise ValueError("场景不存在")
    duration = max(min(int(minutes or 60), int(scene.get("max_minutes") or 60), 60), 1)
    drops = list_scene_drops(scene_id)
    if not drops:
        raise ValueError("该场景尚未配置掉落")
    divine_sense = int(profile.get("divine_sense") or 0)
    fortune = int(profile.get("fortune") or 0)
    root_quality_level = int(profile.get("root_quality_level") or 1)
    weight_rules = _exploration_drop_weight_rules()
    weighted = []
    for drop in drops:
        item_payload = _get_item_payload(str(drop.get("reward_kind") or ""), int(drop.get("reward_ref_id") or 0)) if drop.get("reward_ref_id") else None
        reward_quality = _quality_from_item(str(drop.get("reward_kind") or ""), item_payload)
        extra_weight = 0
        if str(drop.get("reward_kind") or "") == "material":
            extra_weight += max(divine_sense - 10, 0) // int(weight_rules["material_divine_sense_divisor"])
        if reward_quality >= int(weight_rules["high_quality_threshold"]):
            extra_weight += (
                max(fortune - 10, 0) // int(weight_rules["high_quality_fortune_divisor"])
                + max(root_quality_level - int(weight_rules["high_quality_root_level_start"]), 0)
            )
        weighted.extend([drop] * max(int(drop.get("weight") or 1) + extra_weight, 1))
    chosen = random.choice(weighted)
    quantity = random.randint(int(chosen.get("quantity_min") or 1), int(chosen.get("quantity_max") or chosen.get("quantity_min") or 1))
    outcome = _build_exploration_outcome(scene, chosen, fortune, divine_sense)
    event_text = outcome.get("event_text") or chosen.get("event_text") or ""
    with Session() as session:
        exploration = XiuxianExploration(
            tg=tg,
            scene_id=scene_id,
            started_at=utcnow(),
            end_at=utcnow() + timedelta(minutes=duration),
            claimed=False,
            reward_kind=chosen.get("reward_kind"),
            reward_ref_id=chosen.get("reward_ref_id"),
            reward_quantity=quantity,
            stone_reward=int(chosen.get("stone_reward", 0) or 0),
            event_text=event_text or None,
            outcome_payload=outcome,
        )
        session.add(exploration)
        session.commit()
        session.refresh(exploration)
        return {"scene": scene, "exploration": serialize_exploration(exploration)}


def claim_exploration_for_user(tg: int, exploration_id: int) -> dict[str, Any]:
    _require_alive_profile_data(tg, "结算探索")
    exploration_payload: dict[str, Any] | None = None
    reward_kind = None
    reward_ref_id = 0
    reward_quantity = 0
    stone_reward = 0
    outcome: dict[str, Any] = {}
    bonus_payload: dict[str, Any] | None = None
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
        bonus_payload = outcome.get("bonus_reward") if isinstance(outcome.get("bonus_reward"), dict) else None
        technique_rewards = []
        if exploration.reward_kind == "technique" and exploration.reward_ref_id:
            technique_rewards.append(int(exploration.reward_ref_id))
        if bonus_payload and str(bonus_payload.get("kind") or "") == "technique" and int(bonus_payload.get("ref_id") or 0) > 0:
            technique_rewards.append(int(bonus_payload.get("ref_id")))
        if technique_rewards:
            profile_obj = session.query(XiuxianProfile).filter(XiuxianProfile.tg == tg).first()
            capacity = max(int(getattr(profile_obj, "technique_capacity", 0) or 0), 1)
            owned_ids = {
                int(row[0] or 0)
                for row in session.query(XiuxianUserTechnique.technique_id)
                .filter(XiuxianUserTechnique.tg == tg)
                .all()
                if int(row[0] or 0) > 0
            }
            incoming_new = {technique_id for technique_id in technique_rewards if technique_id not in owned_ids}
            if len(owned_ids) + len(incoming_new) > capacity:
                raise ValueError(f"当前可参悟功法数量已满，上限为 {capacity}，请先让管理员调整后再领取该机缘。")
        reward_kind = exploration.reward_kind
        reward_ref_id = int(exploration.reward_ref_id or 0)
        reward_quantity = int(exploration.reward_quantity or 0)
        stone_reward = int(exploration.stone_reward or 0)
        exploration.claimed = True
        exploration.updated_at = utcnow()
        session.commit()
        session.refresh(exploration)
        exploration_payload = serialize_exploration(exploration)
    reward_item = None
    if reward_kind and reward_ref_id and reward_quantity > 0:
        reward_item = _grant_item_by_kind(tg, reward_kind, reward_ref_id, reward_quantity)
    bonus_reward = None
    if bonus_payload and bonus_payload.get("kind") and int(bonus_payload.get("ref_id") or 0) > 0 and int(bonus_payload.get("quantity") or 0) > 0:
        bonus_reward = _grant_item_by_kind(
            tg,
            str(bonus_payload.get("kind")),
            int(bonus_payload.get("ref_id")),
            int(bonus_payload.get("quantity")),
        )
    profile = get_profile(tg, create=False)
    event_stone_bonus = max(int(outcome.get("stone_bonus") or 0), 0)
    event_stone_loss = max(int(outcome.get("stone_loss") or 0), 0)
    current_stone = int(profile.spiritual_stone or 0) if profile else 0
    actual_stone_loss = min(current_stone, event_stone_loss)
    total_stone_delta = stone_reward + event_stone_bonus - actual_stone_loss
    with Session() as session:
        updated = session.query(XiuxianProfile).filter(XiuxianProfile.tg == tg).with_for_update().first()
        if updated is None or not updated.consented:
            raise ValueError("你还没有踏入仙途")
        if total_stone_delta:
            apply_spiritual_stone_delta(
                session,
                tg,
                total_stone_delta,
                action_text="结算探索",
                enforce_currency_lock=True,
                allow_dead=False,
                apply_tribute=total_stone_delta > 0,
            )
        session.commit()
    event_type = str((outcome.get("event") or {}).get("event_type") or "").strip()
    recipe_like_drop = bool(bonus_payload and bonus_payload.get("is_recipe_like")) or _recipe_like_bonus_item(
        reward_kind,
        reward_ref_id,
    )
    achievement_unlocks = record_exploration_metrics(
        tg,
        event_type=event_type,
        recipe_drop=recipe_like_drop,
    )
    create_journal(
        tg,
        "explore",
        "探索结算",
        (
            f"完成探索，灵石变化 {total_stone_delta:+d}。"
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
        "profile": _full_profile_bundle(tg)["profile"],
        "achievement_unlocks": achievement_unlocks,
    }


def create_red_envelope_for_user(
    *,
    tg: int,
    cover_text: str,
    image_url: str = "",
    mode: str,
    amount_total: int,
    count_total: int,
    target_tg: int | None = None,
    group_chat_id: int | None = None,
) -> dict[str, Any]:
    profile, _ = _require_alive_profile_data(tg, "发放红包")
    assert_currency_operation_allowed(tg, "发放红包", profile=profile)
    amount_total = max(int(amount_total or 0), 1)
    count_total = max(int(count_total or 1), 1)
    if int(profile.spiritual_stone or 0) < amount_total:
        raise ValueError("灵石不足")
    with Session() as session:
        updated = session.query(XiuxianProfile).filter(XiuxianProfile.tg == tg).with_for_update().first()
        if updated is None or not updated.consented:
            raise ValueError("你还没有踏入仙途")
        apply_spiritual_stone_delta(
            session,
            tg,
            -amount_total,
            action_text="发放红包",
            enforce_currency_lock=False,
            allow_dead=False,
            apply_tribute=False,
        )
        session.commit()
    with Session() as session:
        envelope = XiuxianRedEnvelope(
            creator_tg=tg,
            cover_text=cover_text or "恭喜发财",
            image_url=image_url or None,
            mode=mode,
            target_tg=target_tg,
            amount_total=amount_total,
            count_total=count_total,
            remaining_amount=amount_total,
            remaining_count=count_total,
            status="active",
            group_chat_id=group_chat_id,
        )
        session.add(envelope)
        session.commit()
        session.refresh(envelope)
        serialized = serialize_red_envelope(envelope)
    create_journal(tg, "red_envelope", "发放红包", f"发放了 {amount_total} 灵石红包【{serialized.get('cover_text') or '福运临门'}】")
    return {
        "envelope": serialized,
        "profile": serialize_profile(get_profile(tg, create=False)),
        "achievement_unlocks": record_red_envelope_metrics(tg, amount_total),
    }


def _draw_red_envelope_amount(envelope: XiuxianRedEnvelope) -> int:
    if int(envelope.remaining_count or 1) <= 1:
        return int(envelope.remaining_amount or 0)
    if envelope.mode == "normal":
        average = max(int(envelope.amount_total or 0) // max(int(envelope.count_total or 1), 1), 1)
        reserve = max(int(envelope.remaining_amount or 0) - (int(envelope.remaining_count or 1) - 1), 1)
        return min(average, reserve)
    remaining_amount = max(int(envelope.remaining_amount or 0), 1)
    remaining_count = max(int(envelope.remaining_count or 1), 1)
    average = remaining_amount / remaining_count
    reserve = max(remaining_amount - (remaining_count - 1), 1)
    upper = max(min(int(average * 2), reserve), 1)
    return random.randint(1, upper)


def claim_red_envelope_for_user(envelope_id: int, tg: int) -> dict[str, Any]:
    with Session() as session:
        profile = session.query(XiuxianProfile).filter(XiuxianProfile.tg == tg).with_for_update().first()
        if profile is None or not profile.consented:
            raise ValueError("你还没有踏入仙途")
        assert_profile_alive(profile, "领取红包")
        assert_currency_operation_allowed(tg, "领取红包", session=session, profile=profile)
        envelope = session.query(XiuxianRedEnvelope).filter(XiuxianRedEnvelope.id == envelope_id).with_for_update().first()
        if envelope is None or envelope.status != "active":
            raise ValueError("红包不存在或已领完")
        if envelope.target_tg and int(envelope.target_tg) != int(tg):
            raise ValueError("这是专属红包，你不能领取")
        existing = (
            session.query(XiuxianRedEnvelopeClaim)
            .filter(XiuxianRedEnvelopeClaim.envelope_id == envelope_id, XiuxianRedEnvelopeClaim.tg == tg)
            .first()
        )
        if existing is not None:
            raise ValueError("你已经领取过这个红包")
        if int(envelope.remaining_count or 0) <= 0 or int(envelope.remaining_amount or 0) <= 0:
            raise ValueError("红包已经被领完")
        amount = min(_draw_red_envelope_amount(envelope), int(envelope.remaining_amount or 0))
        envelope.remaining_amount = max(int(envelope.remaining_amount or 0) - amount, 0)
        envelope.remaining_count = max(int(envelope.remaining_count or 0) - 1, 0)
        if envelope.remaining_count <= 0 or envelope.remaining_amount <= 0:
            envelope.status = "finished"
        envelope.updated_at = utcnow()
        session.add(XiuxianRedEnvelopeClaim(envelope_id=envelope_id, tg=tg, amount=amount))
        session.commit()
    with Session() as session:
        updated = session.query(XiuxianProfile).filter(XiuxianProfile.tg == tg).with_for_update().first()
        if updated is None or not updated.consented:
            raise ValueError("你还没有踏入仙途")
        apply_spiritual_stone_delta(
            session,
            tg,
            amount,
            action_text="领取红包",
            enforce_currency_lock=True,
            allow_dead=False,
            apply_tribute=True,
        )
        session.commit()
    create_journal(tg, "red_envelope", "领取红包", f"领取了 {amount} 灵石红包")
    return {
        "envelope": serialize_red_envelope(get_red_envelope(envelope_id)),
        "amount": amount,
        "profile": _full_profile_bundle(tg)["profile"],
        "claims": list_red_envelope_claims(envelope_id),
    }


def gift_spirit_stone(sender_tg: int, target_tg: int, amount: int) -> dict[str, Any]:
    if int(sender_tg) == int(target_tg):
        raise ValueError("不能给自己赠送灵石")
    amount = max(int(amount or 0), 0)
    if amount <= 0:
        raise ValueError("赠送灵石数量必须大于 0")

    _require_alive_profile_data(sender_tg, "赠送灵石")
    _require_alive_profile_data(target_tg, "接收灵石")
    with Session() as session:
        sender = session.query(XiuxianProfile).filter(XiuxianProfile.tg == sender_tg).with_for_update().first()
        receiver = session.query(XiuxianProfile).filter(XiuxianProfile.tg == target_tg).with_for_update().first()
        if sender is None or receiver is None or not sender.consented or not receiver.consented:
            raise ValueError("双方都需要已踏入仙途")
        assert_currency_operation_allowed(sender_tg, "赠送灵石", session=session, profile=sender)
        assert_currency_operation_allowed(target_tg, "接收灵石", session=session, profile=receiver)
        apply_spiritual_stone_delta(
            session,
            sender_tg,
            -amount,
            action_text="赠送灵石",
            allow_dead=False,
            apply_tribute=False,
        )
        apply_spiritual_stone_delta(
            session,
            target_tg,
            amount,
            action_text="接收灵石",
            allow_dead=False,
            apply_tribute=True,
        )
        session.commit()

    create_journal(sender_tg, "gift", "赠送灵石", f"向 TG {target_tg} 赠送了 {amount} 灵石")
    create_journal(target_tg, "gift", "收到灵石", f"收到 TG {sender_tg} 赠送的 {amount} 灵石")
    return {
        "amount": amount,
        "sender": serialize_profile(get_profile(sender_tg, create=False)),
        "receiver": serialize_profile(get_profile(target_tg, create=False)),
        "achievement_unlocks": record_gift_metrics(sender_tg, amount),
    }


def reset_robbery_counter_if_needed(profile_obj: XiuxianProfile) -> XiuxianProfile:
    today = china_day_key()
    if profile_obj.robbery_day_key != today:
        return upsert_profile(profile_obj.tg, robbery_day_key=today, robbery_daily_count=0)
    return profile_obj


def rob_player(attacker_tg: int, defender_tg: int, success_hint: float = 0.5) -> dict[str, Any]:
    if attacker_tg == defender_tg:
        raise ValueError("不能抢劫自己")
    attacker_obj = reset_robbery_counter_if_needed(_require_alive_profile_data(attacker_tg, "发起抢劫")[0])
    defender_obj = _require_alive_profile_data(defender_tg, "被抢劫")[0]
    if attacker_obj is None or defender_obj is None or not attacker_obj.consented or not defender_obj.consented:
        raise ValueError("双方都需要已踏入仙途")
    if get_active_duel_lock(attacker_tg) or get_active_duel_lock(defender_tg):
        raise ValueError("斗法结算期间无法发起或响应抢劫。")
    settings = get_xiuxian_settings()
    if int(attacker_obj.robbery_daily_count or 0) >= int(settings.get("robbery_daily_limit", DEFAULT_SETTINGS["robbery_daily_limit"]) or 0):
        raise ValueError("今日抢劫次数已用完")
    from bot.plugins.xiuxian_game.service import compute_duel_odds

    duel = compute_duel_odds(attacker_tg, defender_tg)
    attacker = duel["challenger"]["profile"]
    defender = duel["defender"]["profile"]
    stage_diff = int(duel.get("weights", {}).get("stage_diff", 0) or 0)
    rate = float(duel.get("challenger_rate", success_hint) or success_hint)
    rate = rate * 0.85 + float(success_hint) * 0.15
    rate = max(min(rate, 0.985), 0.015 if abs(stage_diff) >= 2 else 0.05)
    roll = random.random()
    success = roll <= rate
    steal_cap = int(settings.get("robbery_max_steal", DEFAULT_SETTINGS["robbery_max_steal"]) or 180)
    artifact_plunder = None
    if success:
        amount = max(min(steal_cap, max(int(defender_obj.spiritual_stone or 0) // 6, 20)), 0)
        with Session() as session:
            attacker_updated = session.query(XiuxianProfile).filter(XiuxianProfile.tg == attacker_tg).with_for_update().first()
            defender_updated = session.query(XiuxianProfile).filter(XiuxianProfile.tg == defender_tg).with_for_update().first()
            if attacker_updated is None or defender_updated is None:
                raise ValueError("双方都需要已踏入仙途")
            apply_spiritual_stone_delta(session, defender_tg, -amount, action_text="被抢劫", allow_dead=False, apply_tribute=False)
            apply_spiritual_stone_delta(session, attacker_tg, amount, action_text="抢劫得手", allow_dead=False, apply_tribute=True)
            attacker_updated.robbery_daily_count = int(attacker_updated.robbery_daily_count or 0) + 1
            attacker_updated.robbery_day_key = china_day_key()
            attacker_updated.updated_at = utcnow()
            session.commit()
        artifact_roll = roll_probability_percent(
            int(settings.get("artifact_plunder_chance", DEFAULT_SETTINGS["artifact_plunder_chance"]) or 0),
            actor_fortune=float(duel["challenger_snapshot"]["stats"]["fortune"]),
            opponent_fortune=float(duel["defender_snapshot"]["stats"]["fortune"]),
            actor_weight=0.45,
            opponent_weight=0.35,
            minimum=0,
            maximum=95,
        )
        artifact_plunder = {
            **artifact_roll,
            "artifact": None,
            "was_equipped": False,
        }
        if artifact_roll["success"]:
            payload = plunder_random_artifact_to_user(attacker_tg, defender_tg)
            if payload and payload.get("artifact"):
                artifact_plunder["artifact"] = payload.get("artifact")
                artifact_plunder["was_equipped"] = bool(payload.get("was_equipped"))
                artifact_name = artifact_plunder["artifact"].get("name", "未知法宝")
                create_journal(attacker_tg, "rob", "顺手夺宝", f"抢劫得手后又夺得法宝【{artifact_name}】")
                create_journal(defender_tg, "rob", "法宝被夺", f"抢劫失手后被夺走法宝【{artifact_name}】")
    else:
        penalty = max(min(int(attacker_obj.spiritual_stone or 0) // 20, 30), 5)
        amount = -penalty
        with Session() as session:
            attacker_updated = session.query(XiuxianProfile).filter(XiuxianProfile.tg == attacker_tg).with_for_update().first()
            defender_updated = session.query(XiuxianProfile).filter(XiuxianProfile.tg == defender_tg).with_for_update().first()
            if attacker_updated is None or defender_updated is None:
                raise ValueError("双方都需要已踏入仙途")
            apply_spiritual_stone_delta(session, attacker_tg, -penalty, action_text="抢劫失败赔付", allow_dead=False, apply_tribute=False)
            apply_spiritual_stone_delta(session, defender_tg, penalty, action_text="获得抢劫赔付", allow_dead=False, apply_tribute=True)
            attacker_updated.robbery_daily_count = int(attacker_updated.robbery_daily_count or 0) + 1
            attacker_updated.robbery_day_key = china_day_key()
            attacker_updated.updated_at = utcnow()
            session.commit()
    return {
        "success": success,
        "roll": round(roll, 4),
        "success_rate": round(rate, 4),
        "amount": amount,
        "attacker": serialize_profile(get_profile(attacker_tg, create=False)),
        "defender": serialize_profile(get_profile(defender_tg, create=False)),
        "artifact_plunder": artifact_plunder,
        "achievement_unlocks": record_robbery_metrics(attacker_tg, success=success, amount=max(amount, 0)),
    }


def update_duel_bet_pool_message(pool_id: int, bet_message_id: int) -> None:
    with Session() as session:
        pool = session.query(XiuxianDuelBetPool).filter(XiuxianDuelBetPool.id == pool_id).first()
        if pool is not None:
            pool.bet_message_id = bet_message_id
            pool.updated_at = utcnow()
            session.commit()


def place_duel_bet(pool_id: int, tg: int, side: str, amount: int) -> dict[str, Any]:
    with Session() as session:
        pool = session.query(XiuxianDuelBetPool).filter(XiuxianDuelBetPool.id == pool_id).with_for_update().first()
        if pool is None or pool.resolved:
            raise ValueError("当前斗法下注已结束")
        if utcnow() >= pool.bets_close_at:
            raise ValueError("下注时间已截止")
        if tg in {pool.challenger_tg, pool.defender_tg}:
            raise ValueError("斗法双方不能下注")
        profile = session.query(XiuxianProfile).filter(XiuxianProfile.tg == tg).with_for_update().first()
        if profile is None or not profile.consented:
            raise ValueError("你还没有踏入仙途")
        assert_profile_alive(profile, "下注")
        assert_currency_operation_allowed(tg, "下注", session=session, profile=profile)
        amount = max(int(amount or 0), 1)
        bet = session.query(XiuxianDuelBet).filter(XiuxianDuelBet.pool_id == pool_id, XiuxianDuelBet.tg == tg).first()
        if bet is None:
            bet = XiuxianDuelBet(pool_id=pool_id, tg=tg, side=side, amount=0)
            session.add(bet)
        elif bet.side != side:
            raise ValueError("同一场斗法只能押注一方")
        bet.amount += amount
        apply_spiritual_stone_delta(session, tg, -amount, action_text="下注", allow_dead=False, apply_tribute=False)
        pool.updated_at = utcnow()
        session.commit()
        challenger_total = sum(int(row.amount or 0) for row in session.query(XiuxianDuelBet).filter(XiuxianDuelBet.pool_id == pool_id, XiuxianDuelBet.side == "challenger").all())
        defender_total = sum(int(row.amount or 0) for row in session.query(XiuxianDuelBet).filter(XiuxianDuelBet.pool_id == pool_id, XiuxianDuelBet.side == "defender").all())
    return {"totals": {"challenger": challenger_total, "defender": defender_total}}


def settle_duel_bet_pool(pool_id: int, winner_tg: int) -> dict[str, Any]:
    with Session() as session:
        pool = session.query(XiuxianDuelBetPool).filter(XiuxianDuelBetPool.id == pool_id).with_for_update().first()
        if pool is None:
            raise ValueError("下注池不存在")
        if pool.resolved:
            return {"pool_id": pool_id, "resolved": True, "entries": [], "payouts": []}
        pool.resolved = True
        pool.winner_tg = winner_tg
        winner_side = "challenger" if int(winner_tg) == int(pool.challenger_tg) else "defender"
        loser_side = "defender" if winner_side == "challenger" else "challenger"
        winner_bets = session.query(XiuxianDuelBet).filter(XiuxianDuelBet.pool_id == pool_id, XiuxianDuelBet.side == winner_side).all()
        loser_bets = session.query(XiuxianDuelBet).filter(XiuxianDuelBet.pool_id == pool_id, XiuxianDuelBet.side == loser_side).all()
        bettor_tgs = [int(row.tg) for row in winner_bets + loser_bets]
        name_map = get_emby_name_map(bettor_tgs)
        loser_total = sum(int(row.amount or 0) for row in loser_bets)
        winner_total = sum(int(row.amount or 0) for row in winner_bets)
        entries = []
        for bet in winner_bets:
            bonus = floor_div(loser_total * int(bet.amount or 0), winner_total)
            total_back = int(bet.amount or 0) + bonus
            profile = session.query(XiuxianProfile).filter(XiuxianProfile.tg == bet.tg).with_for_update().first()
            if profile is not None:
                apply_spiritual_stone_delta(session, int(bet.tg), total_back, action_text="领取斗法押注返还", allow_dead=False, apply_tribute=True)
            entries.append(
                {
                    "tg": int(bet.tg),
                    "name": name_map.get(int(bet.tg), f"TG {bet.tg}"),
                    "side": bet.side,
                    "result": "win",
                    "bet_amount": int(bet.amount or 0),
                    "amount": total_back,
                    "bonus": bonus,
                    "net_profit": bonus,
                }
            )
        for bet in loser_bets:
            entries.append(
                {
                    "tg": int(bet.tg),
                    "name": name_map.get(int(bet.tg), f"TG {bet.tg}"),
                    "side": bet.side,
                    "result": "lose",
                    "bet_amount": int(bet.amount or 0),
                    "amount": -int(bet.amount or 0),
                    "bonus": -int(bet.amount or 0),
                    "net_profit": -int(bet.amount or 0),
                }
            )
        entries.sort(
            key=lambda row: (
                int(row.get("net_profit") or 0),
                int(row.get("bet_amount") or 0),
                -int(row.get("tg") or 0),
            ),
            reverse=True,
        )
        payouts = [row for row in entries if row.get("result") == "win"]
        losses = [row for row in entries if row.get("result") == "lose"]
        pool.updated_at = utcnow()
        session.commit()
    return {
        "pool_id": pool_id,
        "resolved": True,
        "entries": entries,
        "payouts": payouts,
        "losses": losses,
        "winner_tg": winner_tg,
        "winner_side": winner_side,
        "loser_side": loser_side,
        "winner_total": winner_total,
        "loser_total": loser_total,
    }


def cancel_duel_bet_pool(pool_id: int, reason: str = "") -> dict[str, Any]:
    with Session() as session:
        pool = session.query(XiuxianDuelBetPool).filter(XiuxianDuelBetPool.id == pool_id).with_for_update().first()
        if pool is None:
            raise ValueError("下注池不存在")
        if pool.resolved:
            return {"pool_id": pool_id, "resolved": True, "cancelled": True, "entries": [], "reason": reason}
        bets = session.query(XiuxianDuelBet).filter(XiuxianDuelBet.pool_id == pool_id).all()
        name_map = get_emby_name_map([int(row.tg) for row in bets])
        entries = []
        for bet in bets:
            refund_amount = max(int(bet.amount or 0), 0)
            profile = session.query(XiuxianProfile).filter(XiuxianProfile.tg == bet.tg).with_for_update().first()
            if profile is not None and refund_amount > 0:
                apply_spiritual_stone_delta(session, int(bet.tg), refund_amount, action_text="退还斗法押注", allow_dead=False, apply_tribute=True)
            entries.append(
                {
                    "tg": int(bet.tg),
                    "name": name_map.get(int(bet.tg), f"TG {bet.tg}"),
                    "side": bet.side,
                    "bet_amount": refund_amount,
                    "amount": refund_amount,
                    "result": "refund",
                }
            )
        pool.resolved = True
        pool.winner_tg = None
        pool.updated_at = utcnow()
        session.commit()
    return {
        "pool_id": pool_id,
        "resolved": True,
        "cancelled": True,
        "entries": entries,
        "reason": reason,
    }


def format_duel_bet_board(pool_id: int) -> str:
    with Session() as session:
        pool = session.query(XiuxianDuelBetPool).filter(XiuxianDuelBetPool.id == pool_id).first()
        if pool is None:
            return "下注池不存在"
        challenger_total = sum(int(row.amount or 0) for row in session.query(XiuxianDuelBet).filter(XiuxianDuelBet.pool_id == pool_id, XiuxianDuelBet.side == "challenger").all())
        defender_total = sum(int(row.amount or 0) for row in session.query(XiuxianDuelBet).filter(XiuxianDuelBet.pool_id == pool_id, XiuxianDuelBet.side == "defender").all())
        remaining = max(int((pool.bets_close_at - utcnow()).total_seconds()), 0)
        from bot.plugins.xiuxian_game.service import compute_duel_odds, format_duel_matchup_text

        duel_mode = str(pool.duel_mode or "standard")
        duel = compute_duel_odds(int(pool.challenger_tg), int(pool.defender_tg), duel_mode=duel_mode)
        duel_label = DUEL_MODE_LABELS.get(duel_mode, "斗法")
        lines = [
            format_duel_matchup_text(
                duel,
                stake=int(pool.stake or 0),
                title=f"🎯 **{duel_label}押注中**" if not pool.resolved else f"🎯 **{duel_label}押注已结束**",
                duel_mode=duel_mode,
            ),
            "",
            "押注情况：",
            f"挑战者池：{challenger_total} 灵石",
            f"应战者池：{defender_total} 灵石",
            f"总赌池：{challenger_total + defender_total} 灵石",
        ]
        if pool.resolved:
            winner_side = "挑战者" if int(pool.winner_tg or 0) == int(pool.challenger_tg) else "应战者"
            lines.append(f"押注状态：已结算（胜方：{winner_side}）")
        else:
            lines.append(f"剩余时间：{remaining} 秒")
        return "\n".join(lines)


def claim_task_for_user(tg: int, task_id: int) -> dict[str, Any]:
    profile = serialize_profile(get_profile(tg, create=False))
    if not profile or not profile.get("consented"):
        raise ValueError("你还没有踏入仙途")
    with Session() as session:
        completed_now = False
        submitted_item = None
        task = session.query(XiuxianTask).filter(XiuxianTask.id == task_id).with_for_update().first()
        if task is None or not task.enabled:
            raise ValueError("任务不存在")
        if task.task_scope == "sect" and int(task.sect_id or 0) != int(profile.get("sect_id") or 0):
            raise ValueError("只有同宗门成员才能领取该任务")
        if task.task_type == "quiz":
            raise ValueError("答题任务需要在群内作答")
        existing = (
            session.query(XiuxianTaskClaim)
            .filter(XiuxianTaskClaim.task_id == task_id, XiuxianTaskClaim.tg == tg)
            .first()
        )
        if existing is not None:
            raise ValueError("你已经领取过该任务")
        if int(task.claimants_count or 0) >= int(task.max_claimants or 1):
            raise ValueError("该任务已被领取完")

        claim_status = "accepted"
        if task.required_item_kind and task.required_item_ref_id and int(task.required_item_quantity or 0) > 0:
            submitted_item = _consume_required_item(
                session,
                tg,
                str(task.required_item_kind),
                int(task.required_item_ref_id),
                int(task.required_item_quantity),
            )
            completed_now = True
            claim_status = "completed"

        session.add(XiuxianTaskClaim(task_id=task_id, tg=tg, status=claim_status))
        task.claimants_count = int(task.claimants_count or 0) + 1
        if completed_now and task.claimants_count >= int(task.max_claimants or 1):
            task.status = "completed"
        elif not completed_now and task.claimants_count >= int(task.max_claimants or 1):
            task.status = "active"
        task.updated_at = utcnow()
        session.commit()
        session.refresh(task)
        serialized = _decorate_task_payload(serialize_task(task))

    if not completed_now:
        create_journal(tg, "task", "接取任务", f"接取了任务【{serialized['title']}】")
        return {"task": serialized, "reward": None, "submitted_item": None}

    with Session() as session:
        refreshed_task = session.query(XiuxianTask).filter(XiuxianTask.id == task_id).first()
        reward = _award_task_rewards(tg, refreshed_task)
        if refreshed_task and refreshed_task.task_scope == "sect":
            profile_obj = get_profile(tg, create=False)
            if profile_obj is not None:
                upsert_profile(tg, sect_contribution=int(profile_obj.sect_contribution or 0) + 1)
        if refreshed_task is not None:
            item_name = _required_item_name(
                str(refreshed_task.required_item_kind or ""),
                int(refreshed_task.required_item_ref_id or 0),
            )
            create_journal(
                tg,
                "task",
                "提交物品完成任务",
                f"提交了 {item_name} × {int(refreshed_task.required_item_quantity or 0)}，完成任务【{refreshed_task.title}】",
            )
        return {
            "task": _decorate_task_payload(serialize_task(refreshed_task)),
            "reward": reward,
            "submitted_item": {
                "item": submitted_item,
                "quantity": serialized.get("required_item_quantity") or 0,
            },
        }


def resolve_quiz_answer(chat_id: int, tg: int, answer_text: str) -> dict[str, Any] | None:
    normalized = _normalize_quiz_answer_text(answer_text)
    if not normalized:
        return None
    profile = serialize_profile(get_profile(tg, create=False))
    if not profile or not profile.get("consented"):
        return None
    with Session() as session:
        rows = (
            session.query(XiuxianTask)
            .filter(
                XiuxianTask.group_chat_id == chat_id,
                XiuxianTask.active_in_group.is_(True),
                XiuxianTask.task_type == "quiz",
                XiuxianTask.status.in_(["open", "active"]),
                XiuxianTask.enabled.is_(True),
            )
            .with_for_update()
            .all()
        )
        for task in rows:
            if normalized != _normalize_quiz_answer_text(task.answer_text):
                continue
            if task.task_scope == "sect":
                if int(profile.get("sect_id") or 0) != int(task.sect_id or 0):
                    continue
            if task.winner_tg:
                continue
            task.winner_tg = tg
            task.claimants_count = int(task.claimants_count or 0) + 1
            task.status = "completed"
            task.active_in_group = False
            task.updated_at = utcnow()
            claim = (
                session.query(XiuxianTaskClaim)
                .filter(XiuxianTaskClaim.task_id == task.id, XiuxianTaskClaim.tg == tg)
                .first()
            )
            if claim is None:
                session.add(XiuxianTaskClaim(task_id=task.id, tg=tg, status="completed", submitted_answer=normalized))
            else:
                claim.status = "completed"
                claim.submitted_answer = normalized
            session.commit()
            session.refresh(task)
            reward = _award_task_rewards(tg, task)
            if task.task_scope == "sect":
                profile_obj = get_profile(tg, create=False)
                if profile_obj is not None:
                    upsert_profile(tg, sect_contribution=int(profile_obj.sect_contribution or 0) + 1)
            create_journal(tg, "task", "完成答题任务", f"第一个答对了【{task.title}】")
            return {"task": _decorate_task_payload(serialize_task(task)), "reward": reward}
    return None


def create_duel_bet_pool_for_duel(
    *,
    challenger_tg: int,
    defender_tg: int,
    stake: int,
    duel_mode: str = "standard",
    bet_minutes: int | None = None,
    group_chat_id: int,
    duel_message_id: int | None = None,
) -> dict[str, Any]:
    mode_aliases = {
        "standard": "standard",
        "normal": "standard",
        "master": "master",
        "slave": "master",
        "servant": "master",
        "主仆": "master",
        "death": "death",
        "dead": "death",
        "生死": "death",
    }
    duel_mode_value = mode_aliases.get(str(duel_mode or "standard").strip().lower(), "standard")
    for tg in (challenger_tg, defender_tg):
        active_lock = get_active_duel_lock(tg)
        if active_lock is not None:
            raise ValueError(f"{active_lock['duel_mode_label']}尚未结算，暂时不能再次开启新的斗法。")
    settings = get_xiuxian_settings()
    configured_minutes = int(settings.get("duel_bet_minutes", DEFAULT_SETTINGS.get("duel_bet_minutes", 2)) or 2)
    minutes = max(min(int(bet_minutes or configured_minutes), 15), 1)
    stake_amount = max(int(stake or 0), 0)
    if stake_amount > 0:
        from bot.plugins.xiuxian_game.service import assert_duel_stake_affordable

        challenger_profile_obj = get_profile(challenger_tg, create=False)
        defender_profile_obj = get_profile(defender_tg, create=False)
        if challenger_profile_obj is None or defender_profile_obj is None:
            raise ValueError("斗法双方的修仙资料缺失。")
        assert_duel_stake_affordable(
            serialize_profile(challenger_profile_obj),
            serialize_profile(defender_profile_obj),
            stake_amount,
        )
    with Session() as session:
        pool = XiuxianDuelBetPool(
            challenger_tg=challenger_tg,
            defender_tg=defender_tg,
            stake=stake_amount,
            group_chat_id=group_chat_id,
            duel_message_id=duel_message_id,
            duel_mode=duel_mode_value,
            bets_close_at=utcnow() + timedelta(minutes=minutes),
            resolved=False,
        )
        session.add(pool)
        session.commit()
        session.refresh(pool)
        return {
            "id": pool.id,
            "challenger_tg": pool.challenger_tg,
            "defender_tg": pool.defender_tg,
            "stake": pool.stake,
            "group_chat_id": pool.group_chat_id,
            "bet_minutes": minutes,
            "duel_mode": duel_mode_value,
            "duel_mode_label": DUEL_MODE_LABELS.get(duel_mode_value, duel_mode_value),
            "bets_close_at": serialize_datetime(pool.bets_close_at),
        }


def build_world_bundle(tg: int) -> dict[str, Any]:
    settings = get_xiuxian_settings()
    scenes = list_scenes(enabled_only=True)
    exploration_counts = _scene_exploration_counts(tg)
    for scene in scenes:
        scene["drops"] = list_scene_drops(scene["id"])
        scene["user_exploration_count"] = exploration_counts.get(int(scene["id"]), 0)
    recipes = build_recipe_catalog(tg)
    return {
        "sects": list_sects_for_user(tg),
        "current_sect": get_current_sect_bundle(tg),
        "tasks": list_tasks_for_user(tg),
        "materials": list_user_materials(tg),
        "recipes": recipes,
        "recipe_discovered_count": len(recipes),
        "recipe_total_count": len(list_recipes(enabled_only=True)),
        "technique_total_count": len(list_techniques(enabled_only=True)),
        "scenes": scenes,
        "active_exploration": _get_active_exploration(tg),
        "journal": list_recent_journals(tg),
        "settings": {
            "robbery_daily_limit": int(settings.get("robbery_daily_limit", DEFAULT_SETTINGS["robbery_daily_limit"]) or 3),
            "robbery_max_steal": int(settings.get("robbery_max_steal", DEFAULT_SETTINGS["robbery_max_steal"]) or 180),
            "artifact_plunder_chance": int(settings.get("artifact_plunder_chance", DEFAULT_SETTINGS["artifact_plunder_chance"]) or 0),
            "allow_user_task_publish": bool(settings.get("allow_user_task_publish", DEFAULT_SETTINGS["allow_user_task_publish"])),
            "task_publish_cost": max(int(settings.get("task_publish_cost", DEFAULT_SETTINGS["task_publish_cost"]) or 0), 0),
            "user_task_daily_limit": _user_task_daily_limit(),
            "user_task_published_today": _user_task_publish_count_today(tg),
        },
    }


from bot.plugins.xiuxian_game.features.economy import gift_spirit_stone as gift_spirit_stone  # noqa: E402
from bot.plugins.xiuxian_game.features.exploration import (  # noqa: E402
    _get_active_exploration as _get_active_exploration,
    claim_exploration_for_user as claim_exploration_for_user,
    create_scene_with_drops as create_scene_with_drops,
    patch_scene_with_drops as patch_scene_with_drops,
    start_exploration_for_user as start_exploration_for_user,
    sync_scene_with_drops_by_name as sync_scene_with_drops_by_name,
)

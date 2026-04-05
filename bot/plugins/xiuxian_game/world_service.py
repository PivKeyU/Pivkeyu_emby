from __future__ import annotations

import random
import re
from datetime import timedelta
from typing import Any

from bot.sql_helper import Session
from bot.sql_helper.sql_xiuxian import (
    DEFAULT_SETTINGS,
    QUALITY_LABEL_LEVELS,
    SECT_ROLE_LABELS,
    SECT_ROLE_PRESETS,
    XiuxianArtifactInventory,
    XiuxianPillInventory,
    XiuxianProfile,
    XiuxianRecipe,
    XiuxianRecipeIngredient,
    XiuxianSect,
    XiuxianSectRole,
    XiuxianTask,
    XiuxianTaskClaim,
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
    get_material,
    get_pill,
    get_profile,
    get_recipe,
    get_red_envelope,
    get_scene,
    get_sect,
    get_talisman,
    get_xiuxian_settings,
    grant_artifact_to_user,
    grant_material_to_user,
    grant_pill_to_user,
    grant_talisman_to_user,
    list_recipe_ingredients,
    list_recipes,
    list_recent_journals,
    list_red_envelope_claims,
    list_scene_drops,
    list_scenes,
    list_equipped_artifacts,
    list_sect_roles,
    list_sects,
    list_tasks,
    list_user_materials,
    realm_index,
    replace_recipe_ingredients,
    replace_sect_roles,
    serialize_exploration,
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


def floor_div(left: int, right: int) -> int:
    if right <= 0:
        return 0
    return int(left // right)


def _zero_effects() -> dict[str, int]:
    return {
        "attack_bonus": 0,
        "defense_bonus": 0,
        "duel_rate_bonus": 0,
        "cultivation_bonus": 0,
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
    role = get_sect_role_payload(profile_data.get("sect_id"), profile_data.get("sect_role_key"))
    if not role:
        return _zero_effects()
    return {
        "attack_bonus": int(role.get("attack_bonus", 0) or 0),
        "defense_bonus": int(role.get("defense_bonus", 0) or 0),
        "duel_rate_bonus": int(role.get("duel_rate_bonus", 0) or 0),
        "cultivation_bonus": int(role.get("cultivation_bonus", 0) or 0),
    }


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
    min_realm_stage: str | None = None,
    min_realm_layer: int = 1,
    min_stone: int = 0,
    roles: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    sect = create_sect(
        name=name,
        description=description,
        image_url=image_url,
        min_realm_stage=min_realm_stage,
        min_realm_layer=max(int(min_realm_layer or 1), 1),
        min_stone=max(int(min_stone or 0), 0),
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


def _count_sect_members(sect_id: int) -> int:
    with Session() as session:
        return (
            session.query(XiuxianProfile)
            .filter(XiuxianProfile.sect_id == sect_id, XiuxianProfile.consented.is_(True))
            .count()
        )


def _eligible_for_sect(profile_data: dict[str, Any], sect: dict[str, Any]) -> tuple[bool, str]:
    if sect.get("min_realm_stage") and realm_index(profile_data.get("realm_stage")) < realm_index(sect.get("min_realm_stage")):
        return False, "境界不满足宗门要求"
    if profile_data.get("realm_stage") == sect.get("min_realm_stage") and int(profile_data.get("realm_layer") or 0) < int(sect.get("min_realm_layer") or 1):
        return False, "层数不满足宗门要求"
    if int(profile_data.get("spiritual_stone") or 0) < int(sect.get("min_stone") or 0):
        return False, "灵石不满足宗门要求"
    return True, ""


def list_sects_for_user(tg: int) -> list[dict[str, Any]]:
    profile = serialize_profile(get_profile(tg, create=True))
    rows = []
    for sect in list_sects(enabled_only=True):
        sect["roles"] = list_sect_roles(sect["id"])
        sect["member_count"] = _count_sect_members(sect["id"])
        allowed, reason = _eligible_for_sect(profile, sect)
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
    return sect


def join_sect_for_user(tg: int, sect_id: int) -> dict[str, Any]:
    profile = serialize_profile(get_profile(tg, create=False))
    if profile is None or not profile.get("consented"):
        raise ValueError("你还没有踏入仙途")
    if profile.get("sect_id") and int(profile.get("sect_id")) != int(sect_id):
        raise ValueError("你已加入其他宗门")
    sect = serialize_sect(get_sect(sect_id))
    if sect is None or not sect.get("enabled"):
        raise ValueError("宗门不存在")
    allowed, reason = _eligible_for_sect(profile, sect)
    if not allowed:
        raise ValueError(reason)
    upsert_profile(tg, sect_id=sect_id, sect_role_key="outer_disciple")
    create_journal(tg, "sect", "加入宗门", f"加入了宗门【{sect['name']}】")
    return get_current_sect_bundle(tg)


def leave_sect_for_user(tg: int) -> dict[str, Any]:
    profile = serialize_profile(get_profile(tg, create=False))
    if profile is None or not profile.get("consented"):
        raise ValueError("你还没有踏入仙途")
    if not profile.get("sect_id"):
        raise ValueError("你当前并未加入宗门")
    current = get_current_sect_bundle(tg)
    upsert_profile(
        tg,
        sect_id=None,
        sect_role_key=None,
        sect_contribution=0,
        last_salary_claim_at=None,
    )
    create_journal(tg, "sect", "退出宗门", f"离开了宗门【{(current or {}).get('name', '未知宗门')}】")
    return {"previous_sect": current, "profile": serialize_profile(get_profile(tg, create=False))}


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
    updated = upsert_profile(tg, sect_id=sect_id, sect_role_key=role_key)
    return {"profile": serialize_profile(updated), "role": role, "sect": sect}


def claim_sect_salary_for_user(tg: int) -> dict[str, Any]:
    profile_obj = get_profile(tg, create=False)
    if profile_obj is None or not profile_obj.consented:
        raise ValueError("你还没有踏入仙途")
    role = get_sect_role_payload(profile_obj.sect_id, profile_obj.sect_role_key)
    if not role:
        raise ValueError("当前没有宗门俸禄可领取")
    last_claim = profile_obj.last_salary_claim_at
    if last_claim and utcnow() - last_claim < timedelta(days=30):
        remaining = timedelta(days=30) - (utcnow() - last_claim)
        raise ValueError(f"距离下次领取俸禄还需 {remaining.days} 天")
    salary = int(role.get("monthly_salary", 0) or 0)
    updated = upsert_profile(
        tg,
        spiritual_stone=int(profile_obj.spiritual_stone or 0) + salary,
        last_salary_claim_at=utcnow(),
    )
    create_journal(tg, "sect", "领取俸禄", f"领取了 {salary} 灵石的宗门俸禄")
    return {"salary": salary, "profile": serialize_profile(updated), "role": role}


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
    task_type_value = str(task_type or "custom").strip() or "custom"
    normalized_answer = _normalize_quiz_answer_text(answer_text)
    should_push_group = bool(active_in_group)
    required_kind = str(required_item_kind or "").strip() or None
    required_ref = int(required_item_ref_id or 0) or None
    required_qty = max(int(required_item_quantity or 0), 0)

    if task_type_value == "quiz":
        if not normalized_answer:
            raise ValueError("答题任务必须填写标准答案")
        if not group_chat_id:
            raise ValueError("答题任务必须绑定群聊后才能发布")
        if required_kind:
            raise ValueError("答题任务暂不支持提交物品")
        should_push_group = True
        max_claimants = 1

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

    if task_scope == "sect":
        if actor_tg is None:
            if not sect_id:
                raise ValueError("宗门任务必须指定宗门")
        else:
            if not _can_publish_sect_task(actor_tg):
                raise ValueError("当前身份无法发布宗门任务")
            actor_profile = serialize_profile(get_profile(actor_tg, create=False))
            sect_id = int(actor_profile.get("sect_id") or 0)
            if not sect_id:
                raise ValueError("你尚未加入宗门")
    return _decorate_task_payload(create_task(
        title=title,
        description=description,
        task_scope=task_scope,
        task_type=task_type_value,
        owner_tg=actor_tg,
        sect_id=sect_id,
        question_text=question_text or None,
        answer_text=normalized_answer or None,
        image_url=image_url or None,
        required_item_kind=required_kind,
        required_item_ref_id=required_ref,
        required_item_quantity=required_qty,
        reward_stone=max(int(reward_stone or 0), 0),
        reward_item_kind=reward_item_kind or None,
        reward_item_ref_id=reward_item_ref_id,
        reward_item_quantity=max(int(reward_item_quantity or 0), 0),
        max_claimants=max(int(max_claimants or 1), 1),
        active_in_group=should_push_group,
        group_chat_id=group_chat_id,
        status="open",
        enabled=True,
    ))


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
        rows.append(_decorate_task_payload(task))
    return rows


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
    raise ValueError("不支持的物品类型")


def _award_task_rewards(tg: int, task: XiuxianTask) -> dict[str, Any]:
    profile_obj = get_profile(tg, create=False)
    if profile_obj is None:
        raise ValueError("用户不存在")
    updated = upsert_profile(
        tg,
        spiritual_stone=int(profile_obj.spiritual_stone or 0) + int(task.reward_stone or 0),
    )
    reward_item = None
    if task.reward_item_kind and task.reward_item_ref_id and int(task.reward_item_quantity or 0) > 0:
        reward_item = _grant_item_by_kind(tg, task.reward_item_kind, int(task.reward_item_ref_id), int(task.reward_item_quantity))
    return {
        "profile": serialize_profile(updated),
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
    return None


def _quality_from_item(kind: str, item: dict[str, Any] | None) -> int:
    if not item:
        return 1
    if kind == "material":
        return max(int(item.get("quality_level", 1) or 1), 1)
    if kind in {"artifact", "talisman", "pill"}:
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


def build_recipe_catalog() -> list[dict[str, Any]]:
    rows = []
    for recipe in list_recipes(enabled_only=True):
        recipe["ingredients"] = list_recipe_ingredients(recipe["id"])
        recipe["result_item"] = _get_item_payload(recipe["result_kind"], int(recipe["result_ref_id"]))
        rows.append(recipe)
    return rows


def craft_recipe_for_user(tg: int, recipe_id: int) -> dict[str, Any]:
    recipe = serialize_recipe(get_recipe(recipe_id))
    if recipe is None or not recipe.get("enabled"):
        raise ValueError("配方不存在")
    profile = serialize_profile(get_profile(tg, create=False))
    if not profile or not profile.get("consented"):
        raise ValueError("你还没有踏入仙途")
    ingredients = list_recipe_ingredients(recipe_id)
    if not ingredients:
        raise ValueError("该配方还没有配置材料")
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
    result_item = _get_item_payload(recipe["result_kind"], int(recipe["result_ref_id"]))
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
    roll = random.randint(1, 100)
    success = roll <= success_rate
    reward = None
    if success:
        reward = _grant_item_by_kind(tg, recipe["result_kind"], int(recipe["result_ref_id"]), int(recipe["result_quantity"]))
        create_journal(tg, "craft", "炼制成功", f"成功炼制【{(result_item or {}).get('name', '成品')}】")
    else:
        create_journal(tg, "craft", "炼制失败", f"尝试炼制【{(result_item or {}).get('name', '成品')}】但失败了")
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
    profile = serialize_profile(get_profile(tg, create=False))
    if not profile or not profile.get("consented"):
        raise ValueError("你还没有踏入仙途")
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
    events = scene.get("event_pool") or []
    event_text = chosen.get("event_text") or (random.choice(events) if events else "")
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
        )
        session.add(exploration)
        session.commit()
        session.refresh(exploration)
        return {"scene": scene, "exploration": serialize_exploration(exploration)}


def claim_exploration_for_user(tg: int, exploration_id: int) -> dict[str, Any]:
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
        exploration.claimed = True
        exploration.updated_at = utcnow()
        session.commit()
        session.refresh(exploration)
    reward_item = None
    if exploration.reward_kind and exploration.reward_ref_id and int(exploration.reward_quantity or 0) > 0:
        reward_item = _grant_item_by_kind(tg, exploration.reward_kind, int(exploration.reward_ref_id), int(exploration.reward_quantity))
    profile = get_profile(tg, create=False)
    updated = upsert_profile(
        tg,
        spiritual_stone=int(profile.spiritual_stone or 0) + int(exploration.stone_reward or 0),
    )
    create_journal(
        tg,
        "explore",
        "探索结算",
        f"完成探索并获得 {int(exploration.stone_reward or 0)} 灵石",
    )
    return {"exploration": serialize_exploration(exploration), "reward_item": reward_item, "profile": serialize_profile(updated)}


def create_red_envelope_for_user(
    *,
    tg: int,
    cover_text: str,
    mode: str,
    amount_total: int,
    count_total: int,
    target_tg: int | None = None,
    group_chat_id: int | None = None,
) -> dict[str, Any]:
    profile = get_profile(tg, create=False)
    if profile is None or not profile.consented:
        raise ValueError("你还没有踏入仙途")
    amount_total = max(int(amount_total or 0), 1)
    count_total = max(int(count_total or 1), 1)
    if int(profile.spiritual_stone or 0) < amount_total:
        raise ValueError("灵石不足")
    updated = upsert_profile(tg, spiritual_stone=int(profile.spiritual_stone or 0) - amount_total)
    with Session() as session:
        envelope = XiuxianRedEnvelope(
            creator_tg=tg,
            cover_text=cover_text or "恭喜发财",
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
    row = get_red_envelope(serialized["id"])
    create_journal(tg, "red_envelope", "发放红包", f"发放了 {amount_total} 灵石红包【{serialized.get('cover_text') or '福运临门'}】")
    return {"envelope": serialized, "profile": serialize_profile(updated)}


def _draw_red_envelope_amount(envelope: XiuxianRedEnvelope) -> int:
    if int(envelope.remaining_count or 1) <= 1:
        return int(envelope.remaining_amount or 0)
    if envelope.mode == "normal":
        return max(int(envelope.amount_total or 0) // max(int(envelope.count_total or 1), 1), 1)
    max_pick = max(int(envelope.remaining_amount or 0) - (int(envelope.remaining_count or 1) - 1), 1)
    return random.randint(1, max_pick)


def claim_red_envelope_for_user(envelope_id: int, tg: int) -> dict[str, Any]:
    with Session() as session:
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
    profile = get_profile(tg, create=False)
    updated = upsert_profile(tg, spiritual_stone=int(profile.spiritual_stone or 0) + amount)
    create_journal(tg, "red_envelope", "领取红包", f"领取了 {amount} 灵石红包")
    return {
        "envelope": serialize_red_envelope(get_red_envelope(envelope_id)),
        "amount": amount,
        "profile": serialize_profile(updated),
        "claims": list_red_envelope_claims(envelope_id),
    }


def gift_spirit_stone(sender_tg: int, target_tg: int, amount: int) -> dict[str, Any]:
    if int(sender_tg) == int(target_tg):
        raise ValueError("不能给自己赠送灵石")
    amount = max(int(amount or 0), 0)
    if amount <= 0:
        raise ValueError("赠送灵石数量必须大于 0")

    with Session() as session:
        sender = session.query(XiuxianProfile).filter(XiuxianProfile.tg == sender_tg).with_for_update().first()
        receiver = session.query(XiuxianProfile).filter(XiuxianProfile.tg == target_tg).with_for_update().first()
        if sender is None or receiver is None or not sender.consented or not receiver.consented:
            raise ValueError("双方都需要已踏入仙途")
        if int(sender.spiritual_stone or 0) < amount:
            raise ValueError("你的灵石不足")
        sender.spiritual_stone -= amount
        receiver.spiritual_stone += amount
        sender.updated_at = utcnow()
        receiver.updated_at = utcnow()
        session.commit()

    create_journal(sender_tg, "gift", "赠送灵石", f"向 TG {target_tg} 赠送了 {amount} 灵石")
    create_journal(target_tg, "gift", "收到灵石", f"收到 TG {sender_tg} 赠送的 {amount} 灵石")
    return {
        "amount": amount,
        "sender": serialize_profile(get_profile(sender_tg, create=False)),
        "receiver": serialize_profile(get_profile(target_tg, create=False)),
    }


def reset_robbery_counter_if_needed(profile_obj: XiuxianProfile) -> XiuxianProfile:
    today = china_day_key()
    if profile_obj.robbery_day_key != today:
        return upsert_profile(profile_obj.tg, robbery_day_key=today, robbery_daily_count=0)
    return profile_obj


def rob_player(attacker_tg: int, defender_tg: int, success_hint: float = 0.5) -> dict[str, Any]:
    if attacker_tg == defender_tg:
        raise ValueError("不能抢劫自己")
    attacker_obj = reset_robbery_counter_if_needed(get_profile(attacker_tg, create=False))
    defender_obj = get_profile(defender_tg, create=False)
    if attacker_obj is None or defender_obj is None or not attacker_obj.consented or not defender_obj.consented:
        raise ValueError("双方都需要已踏入仙途")
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
    if success:
        amount = max(min(steal_cap, max(int(defender_obj.spiritual_stone or 0) // 6, 20)), 0)
        attacker_updated = upsert_profile(
            attacker_tg,
            spiritual_stone=int(attacker_obj.spiritual_stone or 0) + amount,
            robbery_daily_count=int(attacker_obj.robbery_daily_count or 0) + 1,
            robbery_day_key=china_day_key(),
        )
        defender_updated = upsert_profile(defender_tg, spiritual_stone=max(int(defender_obj.spiritual_stone or 0) - amount, 0))
    else:
        penalty = max(min(int(attacker_obj.spiritual_stone or 0) // 20, 30), 5)
        amount = -penalty
        attacker_updated = upsert_profile(
            attacker_tg,
            spiritual_stone=max(int(attacker_obj.spiritual_stone or 0) - penalty, 0),
            robbery_daily_count=int(attacker_obj.robbery_daily_count or 0) + 1,
            robbery_day_key=china_day_key(),
        )
        defender_updated = upsert_profile(defender_tg, spiritual_stone=int(defender_obj.spiritual_stone or 0) + penalty)
    return {
        "success": success,
        "roll": round(roll, 4),
        "success_rate": round(rate, 4),
        "amount": amount,
        "attacker": serialize_profile(attacker_updated),
        "defender": serialize_profile(defender_updated),
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
        amount = max(int(amount or 0), 1)
        if int(profile.spiritual_stone or 0) < amount:
            raise ValueError("灵石不足")
        bet = session.query(XiuxianDuelBet).filter(XiuxianDuelBet.pool_id == pool_id, XiuxianDuelBet.tg == tg).first()
        if bet is None:
            bet = XiuxianDuelBet(pool_id=pool_id, tg=tg, side=side, amount=0)
            session.add(bet)
        elif bet.side != side:
            raise ValueError("同一场斗法只能押注一方")
        bet.amount += amount
        profile.spiritual_stone -= amount
        profile.updated_at = utcnow()
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
            return {"pool_id": pool_id, "resolved": True, "payouts": []}
        pool.resolved = True
        pool.winner_tg = winner_tg
        winner_side = "challenger" if int(winner_tg) == int(pool.challenger_tg) else "defender"
        loser_side = "defender" if winner_side == "challenger" else "challenger"
        winner_bets = session.query(XiuxianDuelBet).filter(XiuxianDuelBet.pool_id == pool_id, XiuxianDuelBet.side == winner_side).all()
        loser_total = sum(int(row.amount or 0) for row in session.query(XiuxianDuelBet).filter(XiuxianDuelBet.pool_id == pool_id, XiuxianDuelBet.side == loser_side).all())
        winner_total = sum(int(row.amount or 0) for row in winner_bets)
        payouts = []
        for bet in winner_bets:
            bonus = floor_div(loser_total * int(bet.amount or 0), winner_total)
            total_back = int(bet.amount or 0) + bonus
            profile = session.query(XiuxianProfile).filter(XiuxianProfile.tg == bet.tg).with_for_update().first()
            if profile is not None:
                profile.spiritual_stone += total_back
                profile.updated_at = utcnow()
            payouts.append({"tg": bet.tg, "amount": total_back, "bonus": bonus})
        pool.updated_at = utcnow()
        session.commit()
    return {"pool_id": pool_id, "resolved": True, "payouts": payouts, "winner_tg": winner_tg}


def format_duel_bet_board(pool_id: int) -> str:
    with Session() as session:
        pool = session.query(XiuxianDuelBetPool).filter(XiuxianDuelBetPool.id == pool_id).first()
        if pool is None:
            return "下注池不存在"
        challenger_total = sum(int(row.amount or 0) for row in session.query(XiuxianDuelBet).filter(XiuxianDuelBet.pool_id == pool_id, XiuxianDuelBet.side == "challenger").all())
        defender_total = sum(int(row.amount or 0) for row in session.query(XiuxianDuelBet).filter(XiuxianDuelBet.pool_id == pool_id, XiuxianDuelBet.side == "defender").all())
        remaining = max(int((pool.bets_close_at - utcnow()).total_seconds()), 0)
        return f"斗法押注中\n挑战者池：{challenger_total} 灵石\n应战者池：{defender_total} 灵石\n剩余时间：{remaining} 秒"


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
                profile = serialize_profile(get_profile(tg, create=False))
                if not profile or int(profile.get("sect_id") or 0) != int(task.sect_id or 0):
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
    bet_minutes: int | None = None,
    group_chat_id: int,
    duel_message_id: int | None = None,
) -> dict[str, Any]:
    settings = get_xiuxian_settings()
    configured_minutes = int(settings.get("duel_bet_minutes", DEFAULT_SETTINGS.get("duel_bet_minutes", 2)) or 2)
    minutes = max(min(int(bet_minutes or configured_minutes), 15), 1)
    with Session() as session:
        pool = XiuxianDuelBetPool(
            challenger_tg=challenger_tg,
            defender_tg=defender_tg,
            stake=max(int(stake or 0), 0),
            group_chat_id=group_chat_id,
            duel_message_id=duel_message_id,
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
            "bets_close_at": pool.bets_close_at.isoformat() if pool.bets_close_at else None,
        }


def build_world_bundle(tg: int) -> dict[str, Any]:
    return {
        "sects": list_sects_for_user(tg),
        "current_sect": get_current_sect_bundle(tg),
        "tasks": list_tasks_for_user(tg),
        "materials": list_user_materials(tg),
        "recipes": build_recipe_catalog(),
        "scenes": list_scenes(enabled_only=True),
        "active_exploration": _get_active_exploration(tg),
        "journal": list_recent_journals(tg),
        "settings": {
            "robbery_daily_limit": int(get_xiuxian_settings().get("robbery_daily_limit", DEFAULT_SETTINGS["robbery_daily_limit"]) or 3),
            "robbery_max_steal": int(get_xiuxian_settings().get("robbery_max_steal", DEFAULT_SETTINGS["robbery_max_steal"]) or 180),
        },
    }

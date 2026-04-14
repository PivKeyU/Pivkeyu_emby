from __future__ import annotations

import random
from datetime import datetime, timedelta
from typing import Any

from bot.sql_helper.sql_xiuxian import (
    DEFAULT_SETTINGS,
    Session,
    XiuxianEncounterInstance,
    XiuxianEncounterTemplate,
    XiuxianProfile,
    create_encounter_instance,
    create_encounter_template as sql_create_encounter_template,
    delete_encounter_template as sql_delete_encounter_template,
    find_active_group_encounter,
    get_encounter_instance,
    get_latest_group_encounter_time,
    get_xiuxian_settings,
    list_encounter_templates as sql_list_encounter_templates,
    patch_encounter_instance,
    patch_encounter_template as sql_patch_encounter_template,
    serialize_encounter_instance,
    serialize_encounter_template,
    serialize_profile,
    utcnow,
)


def _legacy_service():
    from bot.plugins.xiuxian_game import service as legacy_service

    return legacy_service


def list_encounter_templates(enabled_only: bool = False) -> list[dict[str, Any]]:
    _legacy_service().ensure_seed_data()
    return sql_list_encounter_templates(enabled_only=enabled_only)


def create_encounter_template(**fields) -> dict[str, Any]:
    return sql_create_encounter_template(**fields)


def patch_encounter_template(template_id: int, **fields) -> dict[str, Any] | None:
    return sql_patch_encounter_template(template_id, **fields)


def delete_encounter_template(template_id: int) -> bool:
    return sql_delete_encounter_template(template_id)


def _weighted_choice(rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not rows:
        return None
    total = sum(max(int(row.get("weight") or 0), 1) for row in rows)
    pick = random.randint(1, max(total, 1))
    cursor = 0
    for row in rows:
        cursor += max(int(row.get("weight") or 0), 1)
        if pick <= cursor:
            return row
    return rows[-1]


def _encounter_reward_payload(template: dict[str, Any]) -> dict[str, Any]:
    stone_min = max(int(template.get("reward_stone_min") or 0), 0)
    stone_max = max(int(template.get("reward_stone_max") or stone_min), stone_min)
    cultivation_min = max(int(template.get("reward_cultivation_min") or 0), 0)
    cultivation_max = max(int(template.get("reward_cultivation_max") or cultivation_min), cultivation_min)
    quantity_min = max(int(template.get("reward_item_quantity_min") or 1), 1)
    quantity_max = max(int(template.get("reward_item_quantity_max") or quantity_min), quantity_min)
    payload = {
        "stone_reward": random.randint(stone_min, stone_max) if stone_max > 0 else 0,
        "cultivation_reward": random.randint(cultivation_min, cultivation_max) if cultivation_max > 0 else 0,
        "reward_item_kind": template.get("reward_item_kind"),
        "reward_item_ref_id": int(template.get("reward_item_ref_id") or 0) or None,
        "reward_item_quantity": random.randint(quantity_min, quantity_max) if template.get("reward_item_kind") and template.get("reward_item_ref_id") else 0,
        "reward_willpower": int(template.get("reward_willpower") or 0),
        "reward_charisma": int(template.get("reward_charisma") or 0),
        "reward_karma": int(template.get("reward_karma") or 0),
    }
    return payload


def maybe_spawn_group_encounter(chat_id: int) -> dict[str, Any] | None:
    if not int(chat_id or 0):
        return None
    _legacy_service().ensure_seed_data()
    if find_active_group_encounter(int(chat_id)):
        return None

    settings = get_xiuxian_settings()
    cooldown_minutes = max(
        int(settings.get("encounter_group_cooldown_minutes", DEFAULT_SETTINGS.get("encounter_group_cooldown_minutes", 12)) or 0),
        0,
    )
    latest_time = get_latest_group_encounter_time(int(chat_id))
    if latest_time and utcnow() - latest_time < timedelta(minutes=cooldown_minutes):
        return None

    chance = max(min(int(settings.get("encounter_spawn_chance", DEFAULT_SETTINGS.get("encounter_spawn_chance", 5)) or 0), 100), 0)
    if chance <= 0 or random.randint(1, 100) > chance:
        return None

    template = _weighted_choice(list_encounter_templates(enabled_only=True))
    if not template:
        return None

    active_seconds = max(
        int(template.get("active_seconds") or settings.get("encounter_active_seconds", DEFAULT_SETTINGS.get("encounter_active_seconds", 90)) or 90),
        15,
    )
    instance = create_encounter_instance(
        template_id=int(template.get("id") or 0) or None,
        template_name=str(template.get("name") or "无名奇遇"),
        group_chat_id=int(chat_id),
        button_text=str(template.get("button_text") or "争抢机缘"),
        reward_payload=_encounter_reward_payload(template),
        expires_at=utcnow() + timedelta(seconds=active_seconds),
    )
    return {"template": template, "instance": instance}


def spawn_group_encounter(chat_id: int, template_id: int | None = None) -> dict[str, Any]:
    if not int(chat_id or 0):
        raise ValueError("缺少可投放的群聊 ID。")
    _legacy_service().ensure_seed_data()
    if find_active_group_encounter(int(chat_id)):
        raise ValueError("当前群里已有未结束的奇遇，请等这桩机缘结算后再投放。")

    template: dict[str, Any] | None = None
    if int(template_id or 0) > 0:
        template = next(
            (
                row
                for row in sql_list_encounter_templates(enabled_only=False)
                if int(row.get("id") or 0) == int(template_id)
            ),
            None,
        )
        if template is None:
            raise ValueError("奇遇模板不存在。")
        if not bool(template.get("enabled", True)):
            raise ValueError("该奇遇模板未启用，无法手动投放。")
    else:
        template = _weighted_choice(list_encounter_templates(enabled_only=True))
        if template is None:
            raise ValueError("当前没有可投放的启用奇遇模板。")

    settings = get_xiuxian_settings()
    active_seconds = max(
        int(template.get("active_seconds") or settings.get("encounter_active_seconds", DEFAULT_SETTINGS.get("encounter_active_seconds", 90)) or 90),
        15,
    )
    instance = create_encounter_instance(
        template_id=int(template.get("id") or 0) or None,
        template_name=str(template.get("name") or "无名奇遇"),
        group_chat_id=int(chat_id),
        button_text=str(template.get("button_text") or "争抢机缘"),
        reward_payload=_encounter_reward_payload(template),
        expires_at=utcnow() + timedelta(seconds=active_seconds),
    )
    return {"template": template, "instance": instance}


def mark_group_encounter_message(instance_id: int, message_id: int) -> dict[str, Any] | None:
    return patch_encounter_instance(instance_id, message_id=message_id)


def _encounter_reward_summary(reward_payload: dict[str, Any]) -> str:
    legacy_service = _legacy_service()
    rows = []
    if int(reward_payload.get("stone_reward") or 0) > 0:
        rows.append(f"{int(reward_payload['stone_reward'])} 灵石")
    if int(reward_payload.get("cultivation_reward") or 0) > 0:
        rows.append(f"{int(reward_payload['cultivation_reward'])} 修为")
    reward_item_kind = reward_payload.get("reward_item_kind")
    reward_item_ref_id = int(reward_payload.get("reward_item_ref_id") or 0)
    reward_item_quantity = int(reward_payload.get("reward_item_quantity") or 0)
    if reward_item_kind and reward_item_ref_id and reward_item_quantity > 0:
        item = legacy_service._get_item_payload(reward_item_kind, reward_item_ref_id)
        item_name = (item or {}).get("name") or f"{reward_item_kind}#{reward_item_ref_id}"
        rows.append(f"{reward_item_quantity} 个{item_name}")
    if int(reward_payload.get("reward_willpower") or 0):
        rows.append(f"心志 +{int(reward_payload['reward_willpower'])}")
    if int(reward_payload.get("reward_charisma") or 0):
        rows.append(f"魅力 +{int(reward_payload['reward_charisma'])}")
    if int(reward_payload.get("reward_karma") or 0):
        rows.append(f"因果 +{int(reward_payload['reward_karma'])}")
    return "、".join(rows) if rows else "随机机缘"


def render_group_encounter_text(template: dict[str, Any], instance: dict[str, Any]) -> str:
    reward_summary = _encounter_reward_summary(instance.get("reward_payload") or {})
    action_text = template.get("broadcast_text") or f"群内忽有异象显化，{template.get('name') or '一桩奇遇'} 出世。"
    expires_at = instance.get("expires_at") or "很快"
    return (
        f"🌠 **群机缘降世**\n"
        f"📜 **{template.get('name') or '未命名奇遇'}**\n"
        f"{action_text}\n\n"
        f"🎁 奖励预览：{reward_summary}\n"
        f"⏳ 截止：{expires_at}\n"
        "谁先抢到，机缘便归谁。"
    )


def _claim_requirement_message(template: dict[str, Any]) -> str:
    legacy_service = _legacy_service()
    if template.get("min_realm_stage"):
        return legacy_service.format_realm_requirement(template.get("min_realm_stage"), template.get("min_realm_layer"))
    return "当前修为"


def claim_group_encounter(instance_id: int, tg: int) -> dict[str, Any]:
    legacy_service = _legacy_service()
    bundle = legacy_service.serialize_full_profile(tg)
    profile_data = bundle.get("profile") or {}
    if not profile_data.get("consented"):
        raise ValueError("你还没有踏入仙途。")

    with Session() as session:
        instance = (
            session.query(XiuxianEncounterInstance)
            .filter(XiuxianEncounterInstance.id == instance_id)
            .with_for_update()
            .first()
        )
        if instance is None:
            raise ValueError("奇遇已经消散。")
        template = None
        if instance.template_id:
            template = session.query(XiuxianEncounterTemplate).filter(XiuxianEncounterTemplate.id == instance.template_id).first()
        template_payload = serialize_encounter_template(template) or {
            "name": instance.template_name,
            "button_text": instance.button_text,
            "success_text": None,
            "broadcast_text": None,
            "min_realm_stage": None,
            "min_realm_layer": 1,
            "min_combat_power": 0,
        }
        now = utcnow()
        if instance.status != "active":
            raise ValueError("这桩奇遇已经被别人抢走了。")
        if instance.expires_at <= now:
            instance.status = "expired"
            instance.updated_at = now
            session.commit()
            raise ValueError("你还是慢了一步，机缘已经消散。")
        if template_payload.get("min_realm_stage") and not legacy_service.realm_requirement_met(
            profile_data,
            template_payload.get("min_realm_stage"),
            template_payload.get("min_realm_layer"),
        ):
            raise ValueError(f"境界不足，需要至少达到 {_claim_requirement_message(template_payload)}。")
        if int(bundle.get("combat_power") or 0) < int(template_payload.get("min_combat_power") or 0):
            raise ValueError(f"战力不足，需要至少 {int(template_payload.get('min_combat_power') or 0)} 战力。")

        reward_payload = dict(instance.reward_payload or {})
        profile = session.query(XiuxianProfile).filter(XiuxianProfile.tg == tg).with_for_update().first()
        if profile is None or not profile.consented:
            raise ValueError("你还没有踏入仙途。")

        cultivation_gain = max(int(reward_payload.get("cultivation_reward") or 0), 0)
        stone_reward = max(int(reward_payload.get("stone_reward") or 0), 0)
        willpower_gain = int(reward_payload.get("reward_willpower") or 0)
        charisma_gain = int(reward_payload.get("reward_charisma") or 0)
        karma_gain = int(reward_payload.get("reward_karma") or 0)
        layer, cultivation, upgraded_layers, remaining = legacy_service.apply_cultivation_gain(
            profile.realm_stage or "炼气",
            int(profile.realm_layer or 1),
            int(profile.cultivation or 0),
            cultivation_gain,
        )
        profile.spiritual_stone = int(profile.spiritual_stone or 0) + stone_reward
        profile.cultivation = cultivation
        profile.realm_layer = layer
        profile.willpower = int(profile.willpower or 0) + willpower_gain
        profile.charisma = int(profile.charisma or 0) + charisma_gain
        profile.karma = int(profile.karma or 0) + karma_gain
        profile.updated_at = now

        instance.status = "claimed"
        instance.claimer_tg = tg
        instance.claimed_at = now
        instance.updated_at = now
        session.commit()
        session.refresh(instance)

    item_reward = None
    reward_item_kind = reward_payload.get("reward_item_kind")
    reward_item_ref_id = int(reward_payload.get("reward_item_ref_id") or 0)
    reward_item_quantity = int(reward_payload.get("reward_item_quantity") or 0)
    if reward_item_kind and reward_item_ref_id and reward_item_quantity > 0:
        item_reward = legacy_service.grant_item_to_user(tg, reward_item_kind, reward_item_ref_id, reward_item_quantity)

    legacy_service._apply_profile_growth_floor(tg)
    final_bundle = legacy_service.serialize_full_profile(tg)
    legacy_service.create_journal(
        tg,
        "encounter",
        "夺得奇遇",
        f"在群内抢到了【{template_payload.get('name') or instance.template_name}】，收获 {_encounter_reward_summary(reward_payload)}",
    )
    return {
        "instance": serialize_encounter_instance(get_encounter_instance(instance_id)),
        "template": template_payload,
        "reward": reward_payload,
        "item_reward": item_reward,
        "profile": final_bundle,
        "upgraded_layers": upgraded_layers,
        "remaining": remaining,
    }


def expire_group_encounter(instance_id: int) -> dict[str, Any] | None:
    instance = get_encounter_instance(instance_id)
    if instance is None:
        return None
    if instance.status != "active":
        return instance
    expires_at = instance.get("expires_at")
    if expires_at:
        if isinstance(expires_at, str):
            try:
                expires_at = datetime.fromisoformat(expires_at)
            except ValueError:
                expires_at = None
        if expires_at is not None and expires_at > utcnow():
            return instance
    return patch_encounter_instance(instance_id, status="expired")


def render_group_encounter_success_text(result: dict[str, Any], winner_name: str) -> str:
    template = result.get("template") or {}
    reward = result.get("reward") or {}
    success_text = str(template.get("success_text") or "").strip()
    reward_summary = _encounter_reward_summary(reward)
    mapping = {
        "{user}": winner_name,
        "{encounter}": str(template.get("name") or "奇遇"),
        "{reward}": reward_summary,
        "{stone}": str(int(reward.get("stone_reward") or 0)),
        "{cultivation}": str(int(reward.get("cultivation_reward") or 0)),
    }
    for key, value in mapping.items():
        success_text = success_text.replace(key, value)
    if success_text:
        return success_text
    return (
        f"🎉 **奇遇已被夺得**\n"
        f"{winner_name} 抢先拿下了 **{template.get('name') or '一桩奇遇'}**。\n"
        f"🎁 收获：{reward_summary}"
    )

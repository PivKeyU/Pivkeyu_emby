from __future__ import annotations

import random
from datetime import datetime, timedelta, timezone
from typing import Any

from bot.sql_helper import Session
from bot.sql_helper.sql_xiuxian import (
    XiuxianBossConfig,
    XiuxianProfile,
    apply_spiritual_stone_delta,
    create_journal,
    get_boss_config,
    get_boss_defeat,
    get_active_world_boss,
    get_profile,
    list_boss_configs,
    list_world_boss_damages,
    realm_index,
    serialize_boss_config,
    serialize_profile,
    upsert_boss_defeat,
    upsert_world_boss_damage,
    create_world_boss_instance,
    settle_world_boss_instance,
    update_world_boss_hp,
    utcnow,
)
from bot.plugins.xiuxian_game.probability import roll_probability_percent
from bot.plugins.xiuxian_game.achievement_service import record_boss_metrics


def _legacy_service():
    from bot.plugins.xiuxian_game import service as legacy_service
    return legacy_service


def _grant_item_by_kind(tg: int, kind: str, ref_id: int, quantity: int) -> dict[str, Any]:
    from bot.plugins.xiuxian_game.world_service import _grant_item_by_kind as _grant
    return _grant(tg, kind, ref_id, quantity)


# ── Personal Boss ──────────────────────────────────────────────


def list_personal_bosses_for_user(tg: int) -> dict[str, Any]:
    profile_data = serialize_profile(get_profile(tg, create=False))
    if not profile_data or not profile_data.get("consented"):
        return {"bosses": [], "profile": None}

    all_bosses = list_boss_configs(boss_type="personal")
    player_stage_index = realm_index(profile_data.get("realm_stage"))

    boss_list: list[dict[str, Any]] = []
    for boss in all_bosses:
        boss_stage_index = realm_index(boss.get("realm_stage"))
        defeat_record = get_boss_defeat(tg, int(boss["id"]))
        unlocked = boss_stage_index <= player_stage_index
        beaten = bool(defeat_record and int(defeat_record.get("defeat_count") or 0) > 0)
        from datetime import date
        today = date.today().strftime("%Y%m%d")
        daily_used = 0
        if defeat_record and defeat_record.get("day_key") == today:
            daily_used = int(defeat_record.get("daily_attempts") or 0)
        daily_limit = int(boss.get("daily_attempt_limit") or 0)
        boss_list.append({
            **boss,
            "unlocked": unlocked,
            "beaten": beaten,
            "daily_attempts_used": daily_used,
            "daily_attempts_remaining": max(daily_limit - daily_used, 0),
            "defeat_count": int((defeat_record or {}).get("defeat_count") or 0),
        })

    boss_list.sort(key=lambda b: (b["sort_order"], realm_index(b.get("realm_stage")), b["id"]))
    return {"bosses": boss_list, "profile": profile_data}


def challenge_personal_boss(tg: int, boss_id: int) -> dict[str, Any]:
    legacy_service = _legacy_service()
    profile_data = serialize_profile(get_profile(tg, create=False))
    if not profile_data or not profile_data.get("consented"):
        raise ValueError("你尚未踏入仙途，道基未立")

    boss_row = get_boss_config(boss_id)
    if not boss_row or not boss_row.enabled:
        raise ValueError("这个Boss已消散于天地间，寻不到踪迹。")
    boss = serialize_boss_config(boss_row)

    if boss["boss_type"] != "personal":
        raise ValueError("此乃天地共伐之物，非一人可独战。")

    player_stage_index = realm_index(profile_data.get("realm_stage"))
    boss_stage_index = realm_index(boss.get("realm_stage"))
    if boss_stage_index > player_stage_index:
        raise ValueError("你境界未至，贸然挑战无异于送死。")

    # Daily limit check
    from datetime import date
    today = date.today().strftime("%Y%m%d")
    defeat_record = get_boss_defeat(tg, boss_id)
    daily_used = 0
    if defeat_record and defeat_record.get("day_key") == today:
        daily_used = int(defeat_record.get("daily_attempts") or 0)
    daily_limit = int(boss.get("daily_attempt_limit") or 3)
    if daily_used >= daily_limit:
        raise ValueError(f"今日挑战次数已尽（{daily_used}/{daily_limit}），明日再来吧。")

    # Ticket cost
    ticket_cost = int(boss.get("ticket_cost_stone") or 0)
    from bot.sql_helper.sql_xiuxian import get_shared_spiritual_stone_total
    current_stone = max(int(get_shared_spiritual_stone_total(tg) or 0), 0)
    if ticket_cost > 0 and current_stone < ticket_cost:
        raise ValueError(f"囊中灵石不足，挑战此兽需 {ticket_cost} 灵石作为门票。")

    # Retreat check
    from bot.plugins.xiuxian_game.features.retreat import is_retreating
    if is_retreating(profile_data):
        raise ValueError("闭关之中，心神内敛，不宜外出挑战。")

    # Build player battle bundle
    bundle = legacy_service.serialize_full_profile(tg)
    player_bundle = legacy_service._battle_bundle(bundle, apply_random=True)
    player_state = player_bundle.copy()

    # Build boss battle bundle
    boss_bundle = _build_boss_battle_bundle(boss)
    boss_state = boss_bundle.copy()

    # Run duel simulation
    result = legacy_service._simulate_duel_battle(player_bundle, boss_bundle, player_state, boss_state)

    won = result.get("winner_tg") == tg

    # Apply ticket cost
    with Session() as session:
        if ticket_cost > 0:
            apply_spiritual_stone_delta(session, tg, -ticket_cost, action_text="挑战Boss门票")

        # Update defeat record
        upsert_boss_defeat(tg, boss_id, won)

        # Grant rewards if won
        rewards: dict[str, Any] = {"items": [], "stone": 0, "cultivation": 0}
        if won:
            # Roll loot
            loot_items = _roll_boss_loot(boss)
            for loot in loot_items:
                granted = _grant_item_by_kind(tg, loot["kind"], loot["ref_id"], loot["quantity"])
                if granted:
                    rewards["items"].append({
                        "kind": loot["kind"],
                        "ref_id": loot["ref_id"],
                        "quantity": loot["quantity"],
                        "item": granted,
                    })

            # Stone reward
            stone_min = int(boss.get("stone_reward_min") or 0)
            stone_max = int(boss.get("stone_reward_max") or 0)
            if stone_max > 0:
                stone_amount = random.randint(stone_min, max(stone_max, stone_min))
                if stone_amount > 0:
                    apply_spiritual_stone_delta(session, tg, stone_amount, action_text="击败Boss灵石奖励")
                    rewards["stone"] = stone_amount

            # Cultivation reward
            cultivation_gain = int(boss.get("cultivation_reward") or 0)
            if cultivation_gain > 0:
                from bot.plugins.xiuxian_game.core.realm import apply_cultivation_gain
                profile_obj = session.query(XiuxianProfile).filter(XiuxianProfile.tg == tg).with_for_update().first()
                if profile_obj is not None:
                    stage = legacy_service.normalize_realm_stage(profile_obj.realm_stage or legacy_service.FIRST_REALM_STAGE)
                    layer = max(int(profile_obj.realm_layer or 1), 1)
                    current_cult = max(int(profile_obj.cultivation or 0), 0)
                    new_layer, new_cult, gained = apply_cultivation_gain(stage, layer, current_cult, cultivation_gain)
                    profile_obj.realm_layer = new_layer
                    profile_obj.cultivation = new_cult
                    profile_obj.updated_at = utcnow()
                    rewards["cultivation"] = gained

            session.commit()

            # Record boss kill achievement
            record_boss_metrics(tg, kill=1)

        # Build battle report
        battle_log = result.get("battle_log") or []
        summary = _format_boss_battle_summary(boss, result, won, rewards)
        challenger_actor = result.get("challenger_actor") or {}
        defender_actor = result.get("defender_actor") or {}

        # Journal
        if won:
            create_journal(tg, "boss", "Boss讨伐胜利",
                           f"击败【{boss['name']}】{'，获得灵石 ' + str(rewards['stone']) if rewards['stone'] else ''}"
                           f"{'，修为 +' + str(rewards['cultivation']) if rewards['cultivation'] else ''}")
        else:
            create_journal(tg, "boss", "Boss讨伐失败",
                           f"挑战【{boss['name']}】惜败，损失门票 {ticket_cost} 灵石。")

        updated_profile = serialize_profile(get_profile(tg, create=False))

        return {
            "boss": boss,
            "won": won,
            "summary": summary,
            "battle_log": battle_log,
            "round_count": result.get("round_count", 0),
            "player_hp_remaining": int(challenger_actor.get("hp") or 0),
            "boss_hp_remaining": int(defender_actor.get("hp") or 0),
            "rewards": rewards,
            "profile": updated_profile,
            "daily_attempts_used": daily_used + 1,
            "daily_attempts_limit": daily_limit,
        }


def _build_boss_battle_bundle(boss: dict[str, Any]) -> dict[str, Any]:
    profile = {
        "tg": 0,
        "name": boss["name"],
        "realm_stage": boss["realm_stage"],
        "realm_layer": 9,
        "cultivation": 0,
        "bone": int(boss.get("body_movement") or 10),
        "comprehension": 10,
        "divine_sense": int(boss.get("divine_sense") or 10),
        "fortune": int(boss.get("fortune") or 10),
        "willpower": 10,
        "charisma": 10,
        "karma": 10,
        "qi_blood": int(boss.get("qi_blood") or 500),
        "true_yuan": int(boss.get("true_yuan") or 200),
        "body_movement": int(boss.get("body_movement") or 10),
        "attack_power": int(boss.get("attack_power") or 30),
        "defense_power": int(boss.get("defense_power") or 15),
        "consented": True,
    }
    stats = {
        "bone": float(profile["bone"]),
        "comprehension": float(profile["comprehension"]),
        "divine_sense": float(profile["divine_sense"]),
        "fortune": float(profile["fortune"]),
        "willpower": float(profile["willpower"]),
        "charisma": float(profile["charisma"]),
        "karma": float(profile["karma"]),
        "qi_blood": float(profile["qi_blood"]),
        "true_yuan": float(profile["true_yuan"]),
        "body_movement": float(profile["body_movement"]),
        "attack_power": float(profile["attack_power"]),
        "defense_power": float(profile["defense_power"]),
        "duel_rate_bonus": 0.0,
    }
    stage_index = max(realm_index(boss.get("realm_stage")), 0)
    realm_score = 560 + stage_index * 1750 + 9 * 200
    attribute_score = (
        stats["bone"] * 5.2 + stats["comprehension"] * 5.8
        + stats["divine_sense"] * 5.9 + stats["fortune"] * 2.4
        + stats["willpower"] * 4.6 + stats["charisma"] * 1.5
        + stats["karma"] * 3.0
    )
    combat_score = (
        stats["attack_power"] * 19.5 + stats["defense_power"] * 17.5
        + stats["body_movement"] * 12.5 + stats["qi_blood"] * 0.40
        + stats["true_yuan"] * 0.32
    )
    power = (realm_score + (attribute_score + combat_score) * 1.0) * 0.75

    # Build combat_config for the boss's synthetic technique
    combat_config: dict[str, Any] = {"skills": [], "passives": [], "openings": []}

    skill_name = boss.get("skill_name")
    if skill_name:
        combat_config["skills"].append({
            "kind": "attack",
            "name": skill_name,
            "ratio_percent": int(boss.get("skill_ratio_percent") or 130),
            "hit_bonus": int(boss.get("skill_hit_bonus") or 0),
        })

    passive_name = boss.get("passive_name")
    passive_kind = boss.get("passive_effect_kind")
    if passive_name and passive_kind:
        combat_config["passives"].append({
            "kind": passive_kind,
            "name": passive_name,
            "chance": int(boss.get("passive_chance") or 25),
            "ratio_percent": int(boss.get("passive_ratio_percent") or 0),
        })

    flavor = boss.get("flavor_text") or ""
    if flavor:
        combat_config["openings"].append(flavor)

    synthetic_technique = {
        "name": boss["name"] + "·本命神通",
        "combat_config": combat_config,
    }

    return {
        "profile": profile,
        "quality": "凡品",
        "quality_payload": {"combat_factor": 1.0},
        "root_factor": 1.0,
        "realm_score": float(realm_score),
        "stats": stats,
        "artifact_effects": {},
        "talisman_effects": {},
        "sect_effects": {},
        "technique_effects": {},
        "title_effects": {},
        "power": float(power),
        "combat_power": int(power),
        "equipped_artifacts": [],
        "active_talisman": None,
        "current_technique": synthetic_technique,
        "current_title": None,
    }


def _roll_boss_loot(boss: dict[str, Any]) -> list[dict[str, Any]]:
    drops: list[dict[str, Any]] = []
    loot_specs = [
        ("pill", boss.get("loot_pills_json")),
        ("material", boss.get("loot_materials_json")),
        ("artifact", boss.get("loot_artifacts_json")),
        ("talisman", boss.get("loot_talismans_json")),
        ("recipe", boss.get("loot_recipes_json")),
        ("technique", boss.get("loot_techniques_json")),
    ]
    for kind, loot_json in loot_specs:
        if not loot_json or not isinstance(loot_json, list):
            continue
        for entry in loot_json:
            if not isinstance(entry, dict):
                continue
            ref_id = int(entry.get("ref_id") or 0)
            if ref_id <= 0:
                continue
            chance = max(min(int(entry.get("chance") or 100), 100), 0)
            if not roll_probability_percent(chance)["success"]:
                continue
            qty_min = max(int(entry.get("quantity_min") or 1), 1)
            qty_max = max(int(entry.get("quantity_max") or qty_min), qty_min)
            quantity = random.randint(qty_min, qty_max)
            if quantity > 0:
                drops.append({"kind": kind, "ref_id": ref_id, "quantity": quantity})
    return drops


def _format_boss_battle_summary(boss: dict[str, Any], result: dict[str, Any], won: bool, rewards: dict[str, Any]) -> str:
    if won:
        parts = [f"大败【{boss['name']}】！鏖战 {result.get('round_count', 0)} 回合，终将其斩于马下。"]
        if rewards.get("stone"):
            parts.append(f"获得灵石 {rewards['stone']}。")
        if rewards.get("cultivation"):
            parts.append(f"修为精进 {rewards['cultivation']}。")
        if rewards.get("items"):
            parts.append("另得灵物若干。")
        return "".join(parts)
    else:
        return f"与【{boss['name']}】苦战 {result.get('round_count', 0)} 合，终究不敌，败下阵来。"


# ── World Boss ─────────────────────────────────────────────────


_WORLD_BOSS_ATTACK_COOLDOWN_SECONDS = 30
_WORLD_BOSS_SPAWN_INTERVAL_HOURS = 6
_WORLD_BOSS_HP_MULTIPLIER = 12
_WORLD_BOSS_TIMEOUT_HOURS = 3


def _parse_serialized_datetime(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)
    raw = str(value).strip()
    if raw.endswith("Z"):
        raw = f"{raw[:-1]}+00:00"
    try:
        parsed = datetime.fromisoformat(raw)
    except (TypeError, ValueError):
        return None
    return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=timezone.utc)


def get_world_boss_status_for_user(tg: int) -> dict[str, Any]:
    instance = get_active_world_boss()
    if not instance:
        return {"active": False, "instance": None, "boss": None, "player_damage": None, "ranking": []}

    boss = serialize_boss_config(get_boss_config(int(instance["boss_id"])))
    player_damage = None
    all_damages = list_world_boss_damages(int(instance["id"]))
    for dmg in all_damages:
        if int(dmg.get("tg") or 0) == tg:
            player_damage = dmg
            break

    # Ranking (top 10)
    ranking = all_damages[:10]
    from bot.sql_helper.sql_xiuxian import get_emby_name_map
    tgs = [int(r["tg"]) for r in ranking]
    name_map = get_emby_name_map(tgs) if tgs else {}
    for r in ranking:
        r["display_name"] = name_map.get(int(r["tg"]), f"TG {r['tg']}")

    # Cooldown
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    cooldown_remaining = 0
    if player_damage:
        last_at = _parse_serialized_datetime(player_damage.get("last_attack_at"))
        if last_at:
            elapsed = (now - last_at).total_seconds()
            cooldown_remaining = max(int(_WORLD_BOSS_ATTACK_COOLDOWN_SECONDS - elapsed), 0)

    return {
        "active": True,
        "instance": instance,
        "boss": boss,
        "player_damage": player_damage,
        "cooldown_seconds_remaining": cooldown_remaining,
        "ranking": ranking,
    }


def attack_world_boss(tg: int) -> dict[str, Any]:
    legacy_service = _legacy_service()
    profile_data = serialize_profile(get_profile(tg, create=False))
    if not profile_data or not profile_data.get("consented"):
        raise ValueError("你尚未踏入仙途，道基未立")

    instance = get_active_world_boss()
    if not instance:
        raise ValueError("当下并无世界Boss降临，天地一片安宁。")

    boss = serialize_boss_config(get_boss_config(int(instance["boss_id"])))
    if not boss:
        raise ValueError("Boss已消散，等待下次降临吧。")

    # Cooldown check
    from datetime import datetime, timezone
    all_damages = list_world_boss_damages(int(instance["id"]))
    player_dmg = None
    for dmg in all_damages:
        if int(dmg.get("tg") or 0) == tg:
            player_dmg = dmg
            break
    now = datetime.now(timezone.utc)
    if player_dmg:
        last_attack_at = _parse_serialized_datetime(player_dmg.get("last_attack_at"))
    else:
        last_attack_at = None
    if last_attack_at:
        elapsed = (now - last_attack_at).total_seconds()
        if elapsed < _WORLD_BOSS_ATTACK_COOLDOWN_SECONDS:
            remaining = int(_WORLD_BOSS_ATTACK_COOLDOWN_SECONDS - elapsed)
            raise ValueError(f"气力未复，还需等待 {remaining} 秒方可再次出手。")

    # Compute player combat power
    bundle = legacy_service.serialize_full_profile(tg)
    player_bundle = legacy_service._battle_bundle(bundle, apply_random=False)
    stats = player_bundle.get("stats") or {}

    # Simplified damage formula
    attack_power = float(stats.get("attack_power") or 0)
    defense_power = float(boss.get("defense_power") or 0)
    divine_sense = float(stats.get("divine_sense") or 0)
    fortune = float(stats.get("fortune") or 0)
    combat_power = float(player_bundle.get("power") or bundle.get("combat_power") or 0)

    base_damage = (
        attack_power * random.uniform(1.8, 2.6)
        + combat_power * random.uniform(0.018, 0.028)
        + divine_sense * 0.75
        + fortune * 0.45
    )
    crit_chance = min(8 + divine_sense * 0.15 + fortune * 0.1, 30)
    crit = roll_probability_percent(int(crit_chance))["success"]
    if crit:
        base_damage *= 1.5
    damage_floor = max(8, int(attack_power * 0.6), int(combat_power * 0.004))
    effective_damage = max(int(base_damage - defense_power * 0.18), damage_floor)

    # Apply damage to boss
    updated_instance = update_world_boss_hp(int(instance["id"]), -effective_damage)
    damage_record = upsert_world_boss_damage(int(instance["id"]), tg, effective_damage)

    # Check if boss was just defeated
    boss_defeated = updated_instance and updated_instance.get("status") == "defeated"

    # If defeated, settle
    settlement = None
    if boss_defeated:
        settlement = _settle_world_boss_kill(int(instance["id"]))

    # Journal
    create_journal(tg, "boss", "攻击世界Boss",
                   f"对【{boss['name']}】造成 {effective_damage} 点伤害{'（暴击）' if crit else ''}。"
                   f"{' Boss已被击败！' if boss_defeated else ''}")

    # Record world boss damage achievement
    record_boss_metrics(tg, world_damage=effective_damage)

    return {
        "boss": boss,
        "instance": updated_instance,
        "damage_dealt": effective_damage,
        "crit": crit,
        "boss_defeated": boss_defeated,
        "player_total_damage": int((damage_record or {}).get("total_damage") or 0),
        "player_attack_count": int((damage_record or {}).get("attack_count") or 0),
        "settlement": settlement,
    }


def _settle_world_boss_kill(instance_id: int) -> dict[str, Any]:
    damages = list_world_boss_damages(instance_id)
    if not damages:
        settle_world_boss_instance(instance_id, "defeated")
        return {"rankings": [], "mvp": None}

    from bot.sql_helper.sql_xiuxian import get_emby_name_map
    tgs = [int(d["tg"]) for d in damages]
    name_map = get_emby_name_map(tgs) if tgs else {}

    rankings = []
    for rank_idx, dmg in enumerate(damages):
        tg = int(dmg["tg"])
        rank = rank_idx + 1
        tier = "participation"
        loot_multiplier = 1
        if rank == 1:
            tier = "mvp"
            loot_multiplier = 3
        elif rank <= 3:
            tier = "top3"
            loot_multiplier = 2
        elif rank <= 10:
            tier = "top10"
            loot_multiplier = 1

        rankings.append({
            "rank": rank,
            "tg": tg,
            "display_name": name_map.get(tg, f"TG {tg}"),
            "total_damage": int(dmg.get("total_damage") or 0),
            "tier": tier,
            "loot_multiplier": loot_multiplier,
            "rewarded": False,
        })

    # Grant rewards
    boss_id = None
    instance = _get_world_boss_instance_raw(instance_id)
    if instance:
        boss_id = int(instance.boss_id)
    boss = serialize_boss_config(get_boss_config(boss_id)) if boss_id else None

    if boss:
        with Session() as session:
            for entry in rankings:
                tg = entry["tg"]
                multiplier = entry["loot_multiplier"]
                # Stone reward
                stone_min = int(boss.get("stone_reward_min") or 0)
                stone_max = int(boss.get("stone_reward_max") or 0)
                stone_amount = random.randint(stone_min, max(stone_max, stone_min)) * multiplier
                if stone_amount > 0:
                    apply_spiritual_stone_delta(session, tg, stone_amount, action_text="世界Boss排名灵石奖励")
                # Loot (multiplier times rolls)
                for _ in range(multiplier):
                    loot_items = _roll_boss_loot(boss)
                    for loot in loot_items:
                        _grant_item_by_kind(tg, loot["kind"], loot["ref_id"], loot["quantity"])
                entry["stone_reward"] = stone_amount
                entry["rewarded"] = True
            session.commit()

        # Send MVP journal
        mvp = rankings[0] if rankings else None
        if mvp:
            create_journal(mvp["tg"], "boss", "世界Boss MVP",
                           f"在讨伐【{boss['name']}】中伤害排名第一，获得MVP称号！")
            record_boss_metrics(mvp["tg"], world_mvp=1)

    settle_world_boss_instance(instance_id, "defeated")
    return {
        "rankings": rankings,
        "mvp": rankings[0] if rankings else None,
        "boss_name": boss["name"] if boss else "",
    }


def _get_world_boss_instance_raw(instance_id: int) -> XiuxianBossConfig | None:
    from bot.sql_helper.sql_xiuxian import XiuxianWorldBossInstance as WBInstance
    with Session() as session:
        return session.query(WBInstance).filter(WBInstance.id == instance_id).first()


def settle_world_boss_timeout(instance_id: int) -> dict[str, Any]:
    from bot.sql_helper.sql_xiuxian import get_emby_name_map
    damages = list_world_boss_damages(instance_id)
    if damages:
        with Session() as session:
            for dmg in damages:
                tg = int(dmg["tg"])
                consolation_stone = random.randint(20, 80)
                apply_spiritual_stone_delta(session, tg, consolation_stone, action_text="世界Boss参与奖")
                create_journal(tg, "boss", "世界Boss参与奖",
                               f"世界Boss已遁走，获得参与奖 {consolation_stone} 灵石。")
            session.commit()

    settle_world_boss_instance(instance_id, "escaped")
    return {"rankings": [], "escaped": True}


def spawn_world_boss(boss_id: int | None = None) -> dict[str, Any]:
    existing = get_active_world_boss()
    if existing:
        raise ValueError("当前已有世界Boss降临，请等待其被击败或消散后再手动降临。")

    bosses = list_boss_configs(boss_type="world")
    if not bosses:
        raise ValueError("当前没有已启用的世界Boss配置。")

    if int(boss_id or 0) > 0:
        boss = next((item for item in bosses if int(item.get("id") or 0) == int(boss_id)), None)
        if boss is None:
            raise ValueError("指定的世界Boss不存在或未启用。")
    else:
        boss = random.choice(bosses)
    base_hp = int(boss.get("hp") or 500)
    max_hp = base_hp * _WORLD_BOSS_HP_MULTIPLIER
    expires_at = utcnow() + timedelta(hours=_WORLD_BOSS_TIMEOUT_HOURS)

    instance = create_world_boss_instance(int(boss["id"]), max_hp, expires_at)

    # Broadcast to main group
    from bot.plugins.xiuxian_game import plugin as _plugin
    try:
        chat_id = _plugin._main_group_chat_id()
        if chat_id:
            text = (
                f"【世界Boss降临】\n\n"
                f"{boss['name']} 撕裂虚空而来！\n"
                f"全服HP：{max_hp}/{max_hp}\n"
                f"存在时限：{expires_at.strftime('%m月%d日 %H:%M')} (北京时间)\n\n"
                f"所有在群道友速来降妖除魔！"
            )
            # Schedule to be sent via bot client
            instance["broadcast_text"] = text
            instance["broadcast_chat_id"] = chat_id
    except Exception:
        pass

    return {"boss": boss, "instance": instance}


def try_spawn_world_boss() -> dict[str, Any] | None:
    try:
        return spawn_world_boss()
    except ValueError:
        return None

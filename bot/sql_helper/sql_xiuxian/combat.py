from __future__ import annotations

import copy
import random
import re
from datetime import datetime, timedelta, timezone
from typing import Any, Iterable

from sqlalchemy import event
from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    BigInteger,
    String,
    Text,
    UniqueConstraint,
    or_,
)
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session as OrmSession

from bot.plugins.xiuxian_game import cache as xiuxian_cache
from bot.sql_helper import Base, Session
from bot.sql_helper.sql_emby import Emby
from .constants import *  # noqa: F401 F403
from .models import *  # noqa: F401 F403
from .serializers import *  # noqa: F401 F403
from .profile import *  # noqa: F401 F403

def calculate_arena_cultivation_cap(stage: str | None) -> int:
    normalized = str(stage or "").strip()
    if normalized not in REALM_STAGE_RULES:
        normalized = REALM_ORDER[0]
    threshold_base = int((REALM_STAGE_RULES.get(normalized) or REALM_STAGE_RULES[REALM_ORDER[0]])["threshold_base"])
    return max(int(round(threshold_base * 0.05)), 15)


def _default_arena_stage_rule(stage: str, index: int) -> dict[str, Any]:
    duration_minutes = 60 if index < 2 else 90 if index < 5 else 120 if index < 9 else 180
    return {
        "realm_stage": stage,
        "duration_minutes": duration_minutes,
        "reward_cultivation": calculate_arena_cultivation_cap(stage),
    }


DEFAULT_ARENA_STAGE_RULES = [_default_arena_stage_rule(stage, index) for index, stage in enumerate(REALM_ORDER)]


def _arena_stage_rule_key(entry: Any) -> str | None:
    if not isinstance(entry, dict):
        return None
    stage = normalize_realm_stage(entry.get("realm_stage"))
    return stage if stage in REALM_ORDER else None


def _merge_default_arena_stage_rules(raw: Any) -> list[dict[str, Any]]:
    current_rows = [copy.deepcopy(entry) for entry in raw] if isinstance(raw, list) else []
    normalized: list[dict[str, Any]] = []
    seen: set[str] = set()
    for entry in current_rows:
        stage = _arena_stage_rule_key(entry)
        if stage is None or stage in seen:
            continue
        default_rule = _default_arena_stage_rule(stage, REALM_ORDER.index(stage))
        legacy_reward = int(get_realm_stage_rule(stage)["threshold_base"])
        reward_cultivation = max(int(entry.get("reward_cultivation", default_rule["reward_cultivation"]) or 0), 0)
        if reward_cultivation == legacy_reward:
            reward_cultivation = int(default_rule["reward_cultivation"])
        normalized.append(
            {
                "realm_stage": stage,
                "duration_minutes": max(int(entry.get("duration_minutes", default_rule["duration_minutes"]) or default_rule["duration_minutes"]), 1),
                "reward_cultivation": reward_cultivation,
            }
        )
        seen.add(stage)
    for index, stage in enumerate(REALM_ORDER):
        if stage in seen:
            continue
        normalized.append(copy.deepcopy(_default_arena_stage_rule(stage, index)))
    normalized.sort(key=lambda item: REALM_ORDER.index(item["realm_stage"]))
    return normalized


DEFAULT_SETTINGS = {
    "coin_stone_exchange_enabled": True,
    "coin_exchange_rate": 100,
    "exchange_fee_percent": 1,
    "min_coin_exchange": 1,
    "message_auto_delete_seconds": 180,
    "equipment_unbind_cost": 100,
    "artifact_plunder_chance": 20,
    "shop_broadcast_cost": 20,
    "shop_notice_group_id": 0,
    "official_shop_name": "官方商店",
    "auction_fee_percent": 5,
    "auction_duration_minutes": 60,
    "auction_notice_group_id": 0,
    "allow_user_task_publish": True,
    "task_publish_cost": 20,
    "user_task_daily_limit": 3,
    "artifact_equip_limit": 3,
    "duel_bet_enabled": True,
    "duel_bet_seconds": 120,
    "duel_bet_min_amount": 10,
    "duel_bet_max_amount": 100,
    "duel_bet_amount_options": [10, 50, 100],
    "duel_winner_steal_percent": 25,
    "duel_invite_timeout_seconds": 90,
    "arena_open_fee_stone": 0,
    "arena_challenge_fee_stone": 0,
    "arena_notice_group_id": 0,
    "arena_stage_rules": DEFAULT_ARENA_STAGE_RULES,
    "event_summary_interval_minutes": 10,
    "allow_non_admin_image_upload": False,
    "chat_cultivation_chance": 6,
    "chat_cultivation_min_gain": 1,
    "chat_cultivation_max_gain": 2,
    "robbery_daily_limit": 3,
    "robbery_max_steal": 180,
    "exploration_daily_limit": 10,
    "fishing_daily_limit": 30,
    "encounter_claim_daily_limit": 5,
    "high_quality_broadcast_level": 6,
    "gambling_exchange_cost_stone": 120,
    "gambling_exchange_max_count": 20,
    "gambling_open_max_count": 100,
    "gambling_broadcast_quality_level": 6,
    "gambling_fortune_divisor": 6,
    "gambling_fortune_bonus_per_quality_percent": 8,
    "gambling_quality_weight_rules": DEFAULT_GAMBLING_QUALITY_WEIGHT_RULES,
    "fishing_quality_weight_rules": DEFAULT_FISHING_QUALITY_WEIGHT_RULES,
    "gambling_reward_pool": DEFAULT_GAMBLING_REWARD_POOL,
    "root_quality_value_rules": DEFAULT_ROOT_QUALITY_VALUE_RULES,
    "exploration_drop_weight_rules": DEFAULT_EXPLORATION_DROP_WEIGHT_RULES,
    "item_quality_value_rules": DEFAULT_ITEM_QUALITY_VALUE_RULES,
    "activity_stat_growth_rules": DEFAULT_ACTIVITY_STAT_GROWTH_RULES,
    "immortal_touch_infusion_layers": 1,
    "encounter_auto_dispatch_enabled": True,
    "encounter_auto_dispatch_hour": 12,
    "encounter_auto_dispatch_minute": 0,
    "encounter_auto_dispatch_last_dates": {},
    "encounter_spawn_chance": 5,
    "encounter_group_cooldown_minutes": 12,
    "encounter_active_seconds": 90,
    "slave_tribute_percent": 20,
    "slave_challenge_cooldown_hours": 24,
    "rebirth_cooldown_enabled": False,
    "rebirth_cooldown_base_hours": 12,
    "rebirth_cooldown_increment_hours": 6,
    "furnace_harvest_cultivation_percent": 10,
    "sect_salary_min_stay_days": 30,
    "sect_betrayal_cooldown_days": 7,
    "marriage_divorce_cooldown_days": 7,
    "sect_betrayal_stone_percent": 10,
    "sect_betrayal_stone_min": 20,
    "sect_betrayal_stone_max": 300,
    "error_log_retention_count": 500,
    "seclusion_cultivation_efficiency_percent": 60,
}
DEFAULT_SETTINGS["duel_bet_minutes"] = 2
STALE_DUEL_LOCK_GRACE_SECONDS = 120

QUALITY_LEVEL_LABELS = {
    1: "凡品",
    2: "下品",
    3: "中品",
    4: "上品",
    5: "极品",
    6: "仙品",
    7: "先天至宝",
}
QUALITY_LABEL_LEVELS = {label: level for level, label in QUALITY_LEVEL_LABELS.items()}
QUALITY_LEVEL_COLORS = {
    1: "#9ca3af",
    2: "#22c55e",
    3: "#3b82f6",
    4: "#8b5cf6",
    5: "#f59e0b",
    6: "#ef4444",
    7: "linear-gradient(135deg, #fb7185 0%, #f59e0b 18%, #fde047 36%, #34d399 54%, #60a5fa 72%, #a78bfa 88%, #f472b6 100%)",
}
QUALITY_LEVEL_DESCRIPTIONS = {
    1: "凡铁凡草，灵韵初生。多为刚入道途者随手可得的寻常之物，胜在稳妥。",
    2: "略有打磨，已蕴一丝灵气。散修行走江湖时最常依仗的品阶，不求惊艳但求踏实。",
    3: "锻火初成，器纹浮现。此阶宝物已能隐约引动天地灵气，入手便觉与凡物截然不同。",
    4: "地脉滋养，百炼成器。或藏前辈心血，或吸一方灵气，已能隐约改变斗法走势。",
    5: "天工开物，宝光自生。材取天地至纯，火候十年方成，持之如携一小天地在身。",
    6: "见之如见传说。古籍里零星留下名字，能得一件便是气运加身，坊间数年未必现世一次。",
    7: "先天之宝，道痕自生。混沌初开时便已存在，或从劫灭中幸存，天下仅此一件。",
}
QUALITY_LEVEL_FEATURES = {
    1: "灵纹未显，胜在质朴稳妥",
    2: "仅凝一道灵纹，妙用虽浅却实在可靠",
    3: "灵纹渐明，偶有微末异象相随",
    4: "灵纹交织，已能引动小范围灵潮变动",
    5: "灵纹自成小周天，特效不卑不亢",
    6: "宝纹通玄，御敌之时如臂使指，斗法节奏为之一变",
    7: "混沌道纹，天地间仅此一缕，可逆转乾坤",
}

SOCIAL_MODE_LABELS = {
    "worldly": "入世",
    "secluded": "避世",
}
GENDER_LABELS = {
    "male": "男",
    "female": "女",
}
MENTORSHIP_REQUEST_ROLE_LABELS = {
    "mentor": "收徒邀请",
    "disciple": "拜师申请",
}
MENTORSHIP_STATUS_LABELS = {
    "active": "师徒在籍",
    "graduated": "已出师",
    "dissolved": "已解除",
}
MENTORSHIP_REQUEST_STATUS_LABELS = {
    "pending": "待处理",
    "accepted": "已接受",
    "rejected": "已婉拒",
    "cancelled": "已撤回",
    "expired": "已过期",
}
MARRIAGE_STATUS_LABELS = {
    "active": "已结为道侣",
    "divorced": "已和离",
}
MARRIAGE_REQUEST_STATUS_LABELS = {
    "pending": "待处理",
    "accepted": "已接受",
    "rejected": "已婉拒",
    "cancelled": "已撤回",
    "expired": "已过期",
}
MATERIAL_QUALITY_NOTES = {
    1: "常见基础灵材，适合入门炼制、任务收集与日常积累。",
    2: "灵性稳定的常备材料，足以支撑前中期常规配方。",
    3: "已具明显灵韵，可作为中阶丹器符配方的主辅材料。",
    4: "材质精纯、灵息凝实，常用于高阶炼制与精修。",
    5: "珍稀核心灵材，往往决定成品的上限与方向。",
    6: "传说层次的异材，多见于险地奇遇、榜单奖励或古修遗藏。",
    7: "天材地宝级重宝，足以左右顶级炼制与机缘布局。",
}
PILL_TYPE_LABELS = {
    "foundation": "突破加成",
    "clear_poison": "解毒",
    "cultivation": "提升修为",
    "bone": "提升根骨",
    "comprehension": "提升悟性",
    "divine_sense": "提升神识",
    "fortune": "提升机缘",
    "willpower": "提升心志",
    "charisma": "提升魅力",
    "karma": "提升因果",
    "qi_blood": "提升气血",
    "true_yuan": "提升真元",
    "body_movement": "提升身法",
    "attack": "提升攻击",
    "defense": "提升防御",
    "root_refine": "淬炼灵根",
    "root_remold": "重塑灵根",
    "root_single": "洗成单灵根",
    "root_double": "洗成双灵根",
    "root_earth": "洗成地灵根",
    "root_heaven": "洗成天灵根",
    "root_variant": "洗成变异灵根",
}
REMOVED_PILL_TYPES = {"stone"}
PILL_EFFECT_VALUE_LABELS = {
    "foundation": "突破增幅",
    "clear_poison": "解毒值",
    "cultivation": "修为增量",
    "bone": "根骨增量",
    "comprehension": "悟性增量",
    "divine_sense": "神识增量",
    "fortune": "机缘增量",
    "willpower": "心志增量",
    "charisma": "魅力增量",
    "karma": "因果增量",
    "qi_blood": "气血增量",
    "true_yuan": "真元增量",
    "body_movement": "身法增量",
    "attack": "攻击增量",
    "defense": "防御增量",
    "root_refine": "淬灵阶数",
    "root_remold": "保底品阶",
    "root_single": "保底品阶",
    "root_double": "保底品阶",
    "root_earth": "效果值未用",
    "root_heaven": "效果值未用",
    "root_variant": "效果值未用",
}



def _active_duel_pool_row(
    session: Session,
    tg: int,
    *,
    for_update: bool = False,
) -> XiuxianDuelBetPool | None:
    stale_cutoff = utcnow() - timedelta(seconds=STALE_DUEL_LOCK_GRACE_SECONDS)
    query = session.query(XiuxianDuelBetPool).filter(
        XiuxianDuelBetPool.resolved.is_(False),
        XiuxianDuelBetPool.bets_close_at > stale_cutoff,
        or_(XiuxianDuelBetPool.challenger_tg == tg, XiuxianDuelBetPool.defender_tg == tg),
    )
    if for_update:
        query = query.with_for_update()
    return query.order_by(XiuxianDuelBetPool.id.desc()).first()


def _cleanup_stale_duel_locks(
    session: Session,
    tg: int,
    *,
    for_update: bool = False,
) -> list[int]:
    stale_cutoff = utcnow() - timedelta(seconds=STALE_DUEL_LOCK_GRACE_SECONDS)
    query = session.query(XiuxianDuelBetPool).filter(
        XiuxianDuelBetPool.resolved.is_(False),
        XiuxianDuelBetPool.bets_close_at <= stale_cutoff,
        or_(XiuxianDuelBetPool.challenger_tg == tg, XiuxianDuelBetPool.defender_tg == tg),
    )
    if for_update:
        query = query.with_for_update()
    stale_pools = query.order_by(XiuxianDuelBetPool.id.asc()).all()
    cleaned_ids: list[int] = []

    for pool in stale_pools:
        bets = session.query(XiuxianDuelBet).filter(XiuxianDuelBet.pool_id == pool.id).all()
        for bet in bets:
            refund_amount = max(int(bet.amount or 0), 0)
            if refund_amount <= 0:
                continue
            profile = session.query(XiuxianProfile).filter(XiuxianProfile.tg == int(bet.tg)).with_for_update().first()
            if profile is None:
                continue
            apply_spiritual_stone_delta(
                session,
                int(bet.tg),
                refund_amount,
                action_text="退还过期斗法押注",
                allow_dead=True,
                apply_tribute=True,
            )
        pool.resolved = True
        pool.winner_tg = None
        pool.updated_at = utcnow()
        cleaned_ids.append(int(pool.id))

    if cleaned_ids:
        session.flush()
    return cleaned_ids


def get_active_duel_lock(tg: int) -> dict[str, Any] | None:
    with Session() as session:
        cleaned_ids = _cleanup_stale_duel_locks(session, tg, for_update=False)
        if cleaned_ids:
            session.commit()
        row = _active_duel_pool_row(session, tg, for_update=False)
        if row is None:
            return None
        return {
            "pool_id": int(row.id),
            "duel_mode": str(row.duel_mode or "standard"),
            "duel_mode_label": DUEL_MODE_LABELS.get(str(row.duel_mode or "standard"), str(row.duel_mode or "standard")),
            "challenger_tg": int(row.challenger_tg),
            "defender_tg": int(row.defender_tg),
            "bets_close_at": serialize_datetime(row.bets_close_at),
        }



def _fallback_duel_bet_amount_options(minimum: int, maximum: int) -> list[int]:
    if maximum <= minimum:
        return [minimum]
    midpoint = (minimum + maximum) // 2
    values = [minimum]
    if midpoint not in {minimum, maximum}:
        values.append(midpoint)
    values.append(maximum)
    return sorted(set(values))



def resolve_duel_bet_settings(settings: dict[str, Any] | None = None) -> dict[str, Any]:
    source = settings if isinstance(settings, dict) else {}
    default_options = list(DEFAULT_SETTINGS.get("duel_bet_amount_options") or [10, 50, 100])
    default_minimum = max(_coerce_int(DEFAULT_SETTINGS.get("duel_bet_min_amount"), min(default_options or [10])), 1)
    default_maximum = max(
        _coerce_int(DEFAULT_SETTINGS.get("duel_bet_max_amount"), max(default_options or [100])),
        default_minimum,
    )
    legacy_minutes = max(_coerce_int(source.get("duel_bet_minutes"), DEFAULT_SETTINGS.get("duel_bet_minutes", 2)), 1)
    raw_seconds = source.get("duel_bet_seconds")
    if raw_seconds is None:
        raw_seconds = legacy_minutes * 60
    seconds = min(max(_coerce_int(raw_seconds, DEFAULT_SETTINGS.get("duel_bet_seconds", 120)), 10), 3600)
    enabled = _coerce_bool(source.get("duel_bet_enabled"), _coerce_bool(DEFAULT_SETTINGS.get("duel_bet_enabled"), True))
    minimum = min(max(_coerce_int(source.get("duel_bet_min_amount"), default_minimum), 1), 1_000_000)
    maximum = min(max(_coerce_int(source.get("duel_bet_max_amount"), default_maximum), minimum), 1_000_000)
    options = _normalize_duel_bet_amount_options(
        source.get("duel_bet_amount_options"),
        minimum=minimum,
        maximum=maximum,
    )
    if not options:
        options = _fallback_duel_bet_amount_options(minimum, maximum)
    return {
        "duel_bet_enabled": enabled,
        "duel_bet_seconds": seconds,
        "duel_bet_min_amount": minimum,
        "duel_bet_max_amount": maximum,
        "duel_bet_amount_options": options,
    }



def create_duel_record(
    challenger_tg: int,
    defender_tg: int,
    winner_tg: int,
    loser_tg: int,
    challenger_rate: int,
    defender_rate: int,
    summary: str,
    duel_mode: str = "standard",
    battle_log: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    with Session() as session:
        record = XiuxianDuelRecord(
            challenger_tg=challenger_tg,
            defender_tg=defender_tg,
            winner_tg=winner_tg,
            loser_tg=loser_tg,
            duel_mode=str(duel_mode or "standard"),
            challenger_rate=challenger_rate,
            defender_rate=defender_rate,
            summary=summary,
            battle_log=_sanitize_json_value(battle_log) if battle_log else [],
        )
        session.add(record)
        session.commit()
        session.refresh(record)
        return {
            "id": record.id,
            "challenger_tg": record.challenger_tg,
            "defender_tg": record.defender_tg,
            "winner_tg": record.winner_tg,
            "loser_tg": record.loser_tg,
            "duel_mode": record.duel_mode,
            "challenger_rate": record.challenger_rate,
            "defender_rate": record.defender_rate,
            "summary": record.summary,
            "battle_log": _sanitize_json_value(record.battle_log) or [],
            "created_at": serialize_datetime(record.created_at),
        }



def create_red_envelope(**fields) -> dict[str, Any]:
    with Session() as session:
        envelope = XiuxianRedEnvelope(**fields)
        session.add(envelope)
        session.commit()
        session.refresh(envelope)
        return serialize_red_envelope(envelope)


def get_red_envelope(envelope_id: int) -> XiuxianRedEnvelope | None:
    with Session() as session:
        return session.query(XiuxianRedEnvelope).filter(XiuxianRedEnvelope.id == envelope_id).first()


def list_red_envelope_claims(envelope_id: int) -> list[dict[str, Any]]:
    with Session() as session:
        rows = (
            session.query(XiuxianRedEnvelopeClaim)
            .filter(XiuxianRedEnvelopeClaim.envelope_id == envelope_id)
            .order_by(XiuxianRedEnvelopeClaim.id.asc())
            .all()
        )
        payload = [
            {
                "id": row.id,
                "envelope_id": row.envelope_id,
                "tg": row.tg,
                "amount": row.amount,
                "created_at": serialize_datetime(row.created_at),
            }
            for row in rows
        ]
    name_map = get_emby_name_map([int(item["tg"]) for item in payload])
    for item in payload:
        item["name"] = name_map.get(int(item["tg"]), f"TG {item['tg']}")
    return payload



def create_duel_bet_pool(**fields) -> dict[str, Any]:
    with Session() as session:
        pool = XiuxianDuelBetPool(**fields)
        session.add(pool)
        session.commit()
        session.refresh(pool)
        return {
            "id": pool.id,
            "challenger_tg": pool.challenger_tg,
            "defender_tg": pool.defender_tg,
            "stake": pool.stake,
            "group_chat_id": pool.group_chat_id,
            "duel_message_id": pool.duel_message_id,
            "bet_message_id": pool.bet_message_id,
            "bets_close_at": serialize_datetime(pool.bets_close_at),
            "resolved": pool.resolved,
            "winner_tg": pool.winner_tg,
        }


def get_duel_bet_pool(pool_id: int) -> XiuxianDuelBetPool | None:
    with Session() as session:
        return session.query(XiuxianDuelBetPool).filter(XiuxianDuelBetPool.id == pool_id).first()

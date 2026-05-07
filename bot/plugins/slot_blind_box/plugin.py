from __future__ import annotations

import json
import os
import random
import time
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from pathlib import Path
from threading import RLock
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from pyrogram import enums

from bot import LOGGER, api as api_config, bot, config, group, owner, pivkeyu
from bot.plugins import list_miniapp_plugins
from bot.sql_helper import Session
from bot.sql_helper.sql_emby import Emby, _invalidate_emby_payload, _serialize_emby_row, sql_get_emby
from bot.web.api.miniapp import is_admin_user_id, verify_init_data
from bot.web.presenters import get_level_meta, serialize_emby_user


PLUGIN_ROOT = Path(__file__).resolve().parent
STATIC_DIR = PLUGIN_ROOT / "static"
PROJECT_ROOT = PLUGIN_ROOT.parents[2]
PLUGIN_MANIFEST = json.loads((PLUGIN_ROOT / "plugin.json").read_text(encoding="utf-8"))
SHANGHAI_TZ = timezone(timedelta(hours=8))
MAX_WEIGHT = 1_000_000
MAX_STOCK = 2_147_483_647
MAX_SPIN_COST = 9_007_199_254_740_991
LEVEL_CODES = ("a", "b", "c", "d")
REWARD_TYPE_MANUAL = "manual"
REWARD_TYPE_FREE_SPIN_TICKET = "free_spin_ticket"
REWARD_TYPE_GROUP_INVITE = "group_invite_credit"
REWARD_TYPE_ACCOUNT_OPEN = "account_open_credit"
REWARD_TYPES = {
    REWARD_TYPE_MANUAL,
    REWARD_TYPE_FREE_SPIN_TICKET,
    REWARD_TYPE_GROUP_INVITE,
    REWARD_TYPE_ACCOUNT_OPEN,
}
BACKPACK_ITEM_TYPES = {REWARD_TYPE_FREE_SPIN_TICKET, REWARD_TYPE_GROUP_INVITE, REWARD_TYPE_ACCOUNT_OPEN}
BACKPACK_ITEM_META = {
    REWARD_TYPE_FREE_SPIN_TICKET: {"label": "抽奖券", "icon": "🎟️"},
    REWARD_TYPE_GROUP_INVITE: {"label": "邀请资格", "icon": "📨"},
    REWARD_TYPE_ACCOUNT_OPEN: {"label": "开号资格", "icon": "🪪"},
}
STATE_LOCK = RLock()
RNG = random.SystemRandom()
STATE_PATH = PROJECT_ROOT / "data" / "plugin_state" / "slot-blind-box" / "state.json"


DEFAULT_SETTINGS = {
    "enabled": True,
    "title": "幸运老虎机盲盒",
    "notice": "奖池已开放。",
    "blank_enabled": True,
    "blank_label": "轮空",
    "blank_icon": "◇",
    "blank_weight": 50,
    "pity_enabled": True,
    "pity_after": 10,
    "daily_limit": 0,
    "spin_cost_iv": 10,
    "currency_name": pivkeyu,
    "daily_limit_by_level": {"a": 0, "b": 0, "c": 0, "d": 0},
    "daily_gift_by_level": {"a": 3, "b": 1, "c": 0, "d": 0},
    "cooldown_seconds": 0,
    "record_limit": 300,
}


DEFAULT_PRIZES = [
    {
        "id": "starter-ticket",
        "name": "体验券",
        "icon": "🎫",
        "description": "默认示例奖品，可在后台修改或删除。",
        "delivery_text": "请联系管理员兑换体验券。",
        "reward_type": REWARD_TYPE_MANUAL,
        "free_spin_quantity": 0,
        "weight": 20,
        "stock": -1,
        "enabled": True,
        "guarantee_eligible": True,
        "broadcast_enabled": False,
        "broadcast_image_url": "",
    },
    {
        "id": "bonus-points",
        "name": "积分礼包",
        "icon": "💎",
        "description": "默认示例奖品，可替换为你的真实奖励。",
        "delivery_text": "请联系管理员领取积分礼包。",
        "reward_type": REWARD_TYPE_MANUAL,
        "free_spin_quantity": 0,
        "weight": 10,
        "stock": -1,
        "enabled": True,
        "guarantee_eligible": True,
        "broadcast_enabled": False,
        "broadcast_image_url": "",
    },
    {
        "id": "rare-box",
        "name": "稀有盲盒",
        "icon": "🎁",
        "description": "低概率奖品示例。",
        "delivery_text": "请联系管理员确认稀有盲盒发放方式。",
        "reward_type": REWARD_TYPE_MANUAL,
        "free_spin_quantity": 0,
        "weight": 3,
        "stock": 20,
        "enabled": True,
        "guarantee_eligible": True,
        "broadcast_enabled": True,
        "broadcast_image_url": "",
    },
    {
        "id": "free-spin-ticket",
        "name": "抽奖券",
        "icon": "🎟️",
        "description": "中奖后可免费再抽一次。",
        "delivery_text": "已自动发放 1 张免费抽奖券。",
        "reward_type": REWARD_TYPE_FREE_SPIN_TICKET,
        "free_spin_quantity": 1,
        "weight": 8,
        "stock": -1,
        "enabled": True,
        "guarantee_eligible": True,
        "broadcast_enabled": False,
        "broadcast_image_url": "",
    },
    {
        "id": "group-invite-credit",
        "name": "邀请资格",
        "icon": "📨",
        "description": "可在背包中转赠或上架交易的入群邀请资格。",
        "delivery_text": "已放入背包：邀请资格 1 个。",
        "reward_type": REWARD_TYPE_GROUP_INVITE,
        "free_spin_quantity": 0,
        "weight": 2,
        "stock": -1,
        "enabled": True,
        "guarantee_eligible": False,
        "broadcast_enabled": True,
        "broadcast_image_url": "",
    },
    {
        "id": "account-open-credit",
        "name": "开号资格",
        "icon": "🪪",
        "description": "可在背包中转赠或上架交易的 Emby 开号资格。",
        "delivery_text": "已放入背包：开号资格 1 个。",
        "reward_type": REWARD_TYPE_ACCOUNT_OPEN,
        "free_spin_quantity": 0,
        "weight": 1,
        "stock": -1,
        "enabled": True,
        "guarantee_eligible": False,
        "broadcast_enabled": True,
        "broadcast_image_url": "",
    },
]


class InitDataPayload(BaseModel):
    init_data: str


class RedeemCodePayload(InitDataPayload):
    code: str


class TransferItemPayload(InitDataPayload):
    item_type: str
    target_tg: int
    quantity: int = 1


class ListingPayload(InitDataPayload):
    item_type: str
    quantity: int = 1
    price_iv: int = 0


class ListingPurchasePayload(InitDataPayload):
    listing_id: str


class ListingCancelPayload(InitDataPayload):
    listing_id: str


class AdminBootstrapPayload(BaseModel):
    token: str | None = None
    init_data: str | None = None


class RedeemCodeAdminPayload(BaseModel):
    code: str | None = None
    title: str = ""
    max_uses: int = 1
    per_user_limit: int = 1
    enabled: bool = True
    grants: dict[str, int] | None = None


class RedeemCodeAdminPatchPayload(BaseModel):
    title: str | None = None
    max_uses: int | None = None
    per_user_limit: int | None = None
    enabled: bool | None = None
    grants: dict[str, int] | None = None


class SettingsPatchPayload(BaseModel):
    enabled: bool | None = None
    title: str | None = None
    notice: str | None = None
    blank_enabled: bool | None = None
    blank_label: str | None = None
    blank_icon: str | None = None
    blank_weight: int | None = None
    pity_enabled: bool | None = None
    pity_after: int | None = None
    daily_limit: int | None = None
    spin_cost_iv: int | None = None
    currency_name: str | None = None
    daily_limit_by_level: dict[str, int] | None = None
    daily_gift_by_level: dict[str, int] | None = None
    cooldown_seconds: int | None = None
    record_limit: int | None = None


class PrizePayload(BaseModel):
    name: str
    icon: str = "🎁"
    description: str = ""
    delivery_text: str = ""
    reward_type: str = REWARD_TYPE_MANUAL
    free_spin_quantity: int = 0
    weight: int = 10
    stock: int = -1
    enabled: bool = True
    guarantee_eligible: bool = True
    broadcast_enabled: bool = False
    broadcast_image_url: str = ""


class PrizePatchPayload(BaseModel):
    name: str | None = None
    icon: str | None = None
    description: str | None = None
    delivery_text: str | None = None
    reward_type: str | None = None
    free_spin_quantity: int | None = None
    weight: int | None = None
    stock: int | None = None
    enabled: bool | None = None
    guarantee_eligible: bool | None = None
    broadcast_enabled: bool | None = None
    broadcast_image_url: str | None = None


def _configure_state_path(context: Any | None = None) -> None:
    global STATE_PATH
    if context is not None and getattr(context, "data_dir", None):
        STATE_PATH = Path(context.data_dir) / "state.json"
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso_now() -> str:
    return _now().astimezone(SHANGHAI_TZ).isoformat(timespec="seconds")


def _today_key() -> str:
    return _now().astimezone(SHANGHAI_TZ).strftime("%Y-%m-%d")


def _clean_text(value: Any, *, default: str = "", max_length: int = 512) -> str:
    text = str(value if value is not None else default).strip()
    if not text:
        text = default
    return text[:max_length]


def _clean_bool(value: Any) -> bool:
    return bool(value)


def _clean_int(value: Any, *, default: int, minimum: int, maximum: int, field_name: str) -> int:
    if value is None or value == "":
        return default
    try:
        normalized = int(value)
    except (TypeError, ValueError):
        raise ValueError(f"{field_name}必须是整数") from None
    if normalized < minimum:
        raise ValueError(f"{field_name}不能小于 {minimum}")
    if normalized > maximum:
        raise ValueError(f"{field_name}不能超过 {maximum}")
    return normalized


def _clean_level_int_map(value: Any, *, default: dict[str, int], field_name: str, maximum: int = 100_000) -> dict[str, int]:
    raw = value if isinstance(value, dict) else {}
    normalized: dict[str, int] = {}
    for level in LEVEL_CODES:
        normalized[level] = _clean_int(
            raw.get(level, default.get(level, 0)),
            default=int(default.get(level, 0) or 0),
            minimum=0,
            maximum=maximum,
            field_name=f"{field_name}{level.upper()}",
        )
    return normalized


def _normalize_reward_type(value: Any) -> str:
    normalized = str(value or REWARD_TYPE_MANUAL).strip().lower()
    return normalized if normalized in REWARD_TYPES else REWARD_TYPE_MANUAL


def _normalize_backpack_item_type(value: Any) -> str:
    normalized = _normalize_reward_type(value)
    if normalized not in BACKPACK_ITEM_TYPES:
        raise ValueError("背包物品类型不正确")
    return normalized


def _clean_grants(value: Any) -> dict[str, int]:
    raw = value if isinstance(value, dict) else {}
    return {
        item_type: _clean_int(
            raw.get(item_type),
            default=0,
            minimum=0,
            maximum=100_000,
            field_name=BACKPACK_ITEM_META[item_type]["label"],
        )
        for item_type in BACKPACK_ITEM_TYPES
    }


def _normalize_redeem_code(value: Any | None = None) -> str:
    raw = str(value or uuid4().hex[:10]).strip().upper()
    cleaned = "".join(ch if ch.isalnum() else "-" for ch in raw)
    while "--" in cleaned:
        cleaned = cleaned.replace("--", "-")
    return cleaned.strip("-")[:40] or uuid4().hex[:10].upper()


def _clean_redeem_code(raw: dict[str, Any], *, existing: dict[str, Any] | None = None) -> dict[str, Any]:
    existing = existing or {}
    created_at = existing.get("created_at") or raw.get("created_at") or _iso_now()
    used_by = existing.get("used_by") or raw.get("used_by") or {}
    if not isinstance(used_by, dict):
        used_by = {}
    return {
        "code": _normalize_redeem_code(existing.get("code") or raw.get("code")),
        "title": _clean_text(raw.get("title", existing.get("title")), default="兑换码", max_length=80),
        "max_uses": _clean_int(
            raw.get("max_uses", existing.get("max_uses")),
            default=1,
            minimum=0,
            maximum=1_000_000,
            field_name="总使用次数",
        ),
        "per_user_limit": _clean_int(
            raw.get("per_user_limit", existing.get("per_user_limit")),
            default=1,
            minimum=1,
            maximum=10_000,
            field_name="单人使用次数",
        ),
        "enabled": _clean_bool(raw.get("enabled", existing.get("enabled", True))),
        "grants": _clean_grants(raw.get("grants", existing.get("grants"))),
        "used_count": _clean_int(
            raw.get("used_count", existing.get("used_count")),
            default=0,
            minimum=0,
            maximum=1_000_000,
            field_name="已使用次数",
        ),
        "used_by": {str(key): int(value or 0) for key, value in used_by.items()},
        "created_at": created_at,
        "updated_at": _iso_now() if existing else raw.get("updated_at") or created_at,
    }


def _clean_listing(raw: dict[str, Any]) -> dict[str, Any] | None:
    try:
        item_type = _normalize_backpack_item_type(raw.get("item_type"))
    except ValueError:
        return None
    quantity = _clean_int(raw.get("quantity"), default=1, minimum=1, maximum=1_000_000, field_name="上架数量")
    price_iv = _clean_int(raw.get("price_iv"), default=0, minimum=0, maximum=MAX_SPIN_COST, field_name="上架价格")
    seller_tg = raw.get("seller_tg")
    try:
        seller_tg = int(seller_tg)
    except (TypeError, ValueError):
        return None
    return {
        "id": _clean_prize_id(raw.get("id")),
        "seller_tg": seller_tg,
        "seller_display": _clean_text(raw.get("seller_display"), default=str(seller_tg), max_length=80),
        "item_type": item_type,
        "quantity": quantity,
        "price_iv": price_iv,
        "status": str(raw.get("status") or "active").strip().lower(),
        "created_at": raw.get("created_at") or _iso_now(),
        "updated_at": raw.get("updated_at") or raw.get("created_at") or _iso_now(),
    }


def _clean_prize_id(value: Any | None = None) -> str:
    raw = str(value or uuid4().hex[:12]).strip().lower()
    cleaned = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "-" for ch in raw)
    while "--" in cleaned:
        cleaned = cleaned.replace("--", "-")
    cleaned = cleaned.strip("-_")
    return cleaned[:48] or uuid4().hex[:12]


def _clean_prize(raw: dict[str, Any], *, existing: dict[str, Any] | None = None) -> dict[str, Any]:
    existing = existing or {}
    created_at = existing.get("created_at") or raw.get("created_at") or _iso_now()
    reward_type = _normalize_reward_type(raw.get("reward_type", existing.get("reward_type")))
    return {
        "id": _clean_prize_id(existing.get("id") or raw.get("id")),
        "name": _clean_text(raw.get("name", existing.get("name")), default="未命名奖品", max_length=80),
        "icon": _clean_text(raw.get("icon", existing.get("icon")), default="🎁", max_length=16),
        "description": _clean_text(raw.get("description", existing.get("description")), max_length=500),
        "delivery_text": _clean_text(raw.get("delivery_text", existing.get("delivery_text")), max_length=1000),
        "reward_type": reward_type,
        "free_spin_quantity": _clean_int(
            raw.get("free_spin_quantity", existing.get("free_spin_quantity")),
            default=1 if reward_type == REWARD_TYPE_FREE_SPIN_TICKET else 0,
            minimum=0,
            maximum=1000,
            field_name="抽奖券数量",
        ),
        "weight": _clean_int(
            raw.get("weight", existing.get("weight")),
            default=10,
            minimum=0,
            maximum=MAX_WEIGHT,
            field_name="中奖率权重",
        ),
        "stock": _clean_int(
            raw.get("stock", existing.get("stock")),
            default=-1,
            minimum=-1,
            maximum=MAX_STOCK,
            field_name="库存",
        ),
        "enabled": _clean_bool(raw.get("enabled", existing.get("enabled", True))),
        "guarantee_eligible": _clean_bool(
            raw.get("guarantee_eligible", existing.get("guarantee_eligible", True))
        ),
        "broadcast_enabled": _clean_bool(raw.get("broadcast_enabled", existing.get("broadcast_enabled", False))),
        "broadcast_image_url": _clean_text(
            raw.get("broadcast_image_url", existing.get("broadcast_image_url")), max_length=1000
        ),
        "created_at": created_at,
        "updated_at": _iso_now() if existing else raw.get("updated_at") or created_at,
    }


def _fresh_state() -> dict[str, Any]:
    timestamp = _iso_now()
    prizes = []
    for prize in DEFAULT_PRIZES:
        clean = _clean_prize({**prize, "created_at": timestamp, "updated_at": timestamp})
        prizes.append(clean)
    return {
        "schema_version": 3,
        "settings": deepcopy(DEFAULT_SETTINGS),
        "prizes": prizes,
        "users": {},
        "records": [],
        "redeem_codes": [],
        "market_listings": [],
        "created_at": timestamp,
        "updated_at": timestamp,
    }


def _normalize_settings(raw: dict[str, Any] | None) -> dict[str, Any]:
    raw = raw or {}
    settings = deepcopy(DEFAULT_SETTINGS)
    settings.update(raw)
    settings["enabled"] = bool(settings.get("enabled", True))
    settings["title"] = _clean_text(settings.get("title"), default=DEFAULT_SETTINGS["title"], max_length=80)
    settings["notice"] = _clean_text(settings.get("notice"), max_length=240)
    settings["blank_enabled"] = bool(settings.get("blank_enabled", True))
    settings["blank_label"] = _clean_text(settings.get("blank_label"), default="轮空", max_length=24)
    settings["blank_icon"] = _clean_text(settings.get("blank_icon"), default="◇", max_length=16)
    settings["blank_weight"] = _clean_int(
        settings.get("blank_weight"), default=50, minimum=0, maximum=MAX_WEIGHT, field_name="轮空权重"
    )
    settings["pity_enabled"] = bool(settings.get("pity_enabled", True))
    settings["pity_after"] = _clean_int(
        settings.get("pity_after"), default=10, minimum=1, maximum=10_000, field_name="保底次数"
    )
    settings["daily_limit"] = _clean_int(
        settings.get("daily_limit"), default=0, minimum=0, maximum=100_000, field_name="每日次数"
    )
    settings["spin_cost_iv"] = _clean_int(
        settings.get("spin_cost_iv"), default=10, minimum=0, maximum=MAX_SPIN_COST, field_name="单抽价格"
    )
    settings["currency_name"] = _clean_text(settings.get("currency_name"), default=pivkeyu, max_length=32)
    settings["daily_limit_by_level"] = _clean_level_int_map(
        settings.get("daily_limit_by_level"),
        default=DEFAULT_SETTINGS["daily_limit_by_level"],
        field_name="等级每日上限",
    )
    settings["daily_gift_by_level"] = _clean_level_int_map(
        settings.get("daily_gift_by_level"),
        default=DEFAULT_SETTINGS["daily_gift_by_level"],
        field_name="等级每日赠送次数",
    )
    settings["cooldown_seconds"] = _clean_int(
        settings.get("cooldown_seconds"), default=0, minimum=0, maximum=86_400, field_name="冷却秒数"
    )
    settings["record_limit"] = _clean_int(
        settings.get("record_limit"), default=300, minimum=50, maximum=5000, field_name="记录保留数"
    )
    return settings


def _normalize_state(state: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(state or {})
    raw_schema_version = int(normalized.get("schema_version") or 1)
    normalized["schema_version"] = 3
    normalized["settings"] = _normalize_settings(normalized.get("settings"))

    prizes: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for raw_prize in normalized.get("prizes") or []:
        if not isinstance(raw_prize, dict):
            continue
        prize = _clean_prize(raw_prize)
        original_id = prize["id"]
        while prize["id"] in seen_ids:
            prize["id"] = _clean_prize_id(f"{original_id}-{uuid4().hex[:4]}")
        seen_ids.add(prize["id"])
        prizes.append(prize)
    if raw_schema_version < 2 and "free-spin-ticket" not in seen_ids:
        prize = _clean_prize({**DEFAULT_PRIZES[3], "created_at": _iso_now(), "updated_at": _iso_now()})
        prizes.append(prize)
        seen_ids.add(prize["id"])
    if raw_schema_version < 3:
        for default_prize in DEFAULT_PRIZES[4:]:
            if default_prize["id"] in seen_ids:
                continue
            prize = _clean_prize({**default_prize, "created_at": _iso_now(), "updated_at": _iso_now()})
            prizes.append(prize)
            seen_ids.add(prize["id"])
    normalized["prizes"] = prizes
    normalized["users"] = normalized.get("users") if isinstance(normalized.get("users"), dict) else {}
    normalized["records"] = normalized.get("records") if isinstance(normalized.get("records"), list) else []
    redeem_codes = []
    seen_codes: set[str] = set()
    for raw_code in normalized.get("redeem_codes") or []:
        if not isinstance(raw_code, dict):
            continue
        code = _clean_redeem_code(raw_code)
        if code["code"] in seen_codes:
            continue
        seen_codes.add(code["code"])
        redeem_codes.append(code)
    normalized["redeem_codes"] = redeem_codes
    listings = []
    seen_listing_ids: set[str] = set()
    for raw_listing in normalized.get("market_listings") or []:
        if not isinstance(raw_listing, dict):
            continue
        listing = _clean_listing(raw_listing)
        if not listing or listing["id"] in seen_listing_ids:
            continue
        seen_listing_ids.add(listing["id"])
        listings.append(listing)
    normalized["market_listings"] = listings
    normalized.setdefault("created_at", _iso_now())
    normalized["updated_at"] = normalized.get("updated_at") or normalized["created_at"]
    return normalized


def _load_state_unlocked() -> dict[str, Any]:
    _configure_state_path()
    if not STATE_PATH.exists():
        state = _fresh_state()
        _save_state_unlocked(state)
        return state
    with STATE_PATH.open("r", encoding="utf-8") as state_file:
        state = json.load(state_file)
    return _normalize_state(state)


def _save_state_unlocked(state: dict[str, Any]) -> None:
    _configure_state_path()
    state["updated_at"] = _iso_now()
    temp_path = STATE_PATH.with_suffix(".tmp")
    temp_path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(temp_path, STATE_PATH)


def _verify_user_from_init_data(init_data: str) -> dict[str, Any]:
    verified = verify_init_data(init_data)
    return verified["user"]


def _verify_admin_credential(token: str | None, init_data: str | None) -> dict[str, Any]:
    expected_token = api_config.admin_token or ""
    if token and expected_token and token == expected_token:
        return {"id": owner, "auth": "token"}
    if init_data:
        user = _verify_user_from_init_data(init_data)
        if is_admin_user_id(int(user["id"])):
            user["auth"] = "telegram"
            return user
        raise HTTPException(status_code=403, detail="当前 Telegram 账号没有后台权限")
    raise HTTPException(status_code=401, detail="缺少后台登录凭证")


def _telegram_user_label(user: dict[str, Any]) -> str:
    display_name = " ".join(
        part for part in [str(user.get("first_name") or "").strip(), str(user.get("last_name") or "").strip()] if part
    ).strip()
    if display_name:
        return display_name[:80]
    username = str(user.get("username") or "").strip().lstrip("@")
    if username:
        return f"@{username}"[:80]
    return str(user.get("id") or "未知用户")[:80]


def _main_group_chat_id() -> int | None:
    for value in group:
        try:
            return int(value)
        except (TypeError, ValueError):
            continue
    return None


def _broadcast_text(*, user_label: str, prize: dict[str, Any], probabilities: dict[str, Any], pity_triggered: bool) -> str:
    rate = (probabilities.get("prize_rates") or {}).get(prize.get("id"), 0)
    stock = int(prize.get("stock") or 0)
    stock_text = "不限" if stock < 0 else str(stock)
    pity_text = "，这次还是保底触发的，算、算你坚持得不错啦" if pity_triggered else ""
    return (
        "🎰 哼，本女仆才不是特意给你们报喜呢！\n"
        f"{user_label} 刚刚在老虎机盲盒里抽中了 {prize.get('icon') or '🎁'} {prize.get('name')}！\n"
        f"这个奖项当前概率约 {rate}%{pity_text}。\n"
        f"剩余库存：{stock_text}\n"
        "既然中了大奖，本女仆就勉强恭喜一下吧。下次可别得意忘形哦。"
    )


async def _send_group_broadcast(payload: dict[str, Any] | None) -> None:
    if not payload:
        return
    chat_id = _main_group_chat_id()
    if not chat_id:
        return
    image_url = str(payload.get("image_url") or "").strip()
    text = str(payload.get("text") or "").strip()
    if not text:
        return
    try:
        if image_url:
            try:
                await bot.send_photo(chat_id=chat_id, photo=image_url, caption=text, parse_mode=enums.ParseMode.DISABLED)
                return
            except Exception as exc:
                LOGGER.warning(f"slot blind box broadcast image failed chat={chat_id}: {exc}")
        await bot.send_message(chat_id=chat_id, text=text, parse_mode=enums.ParseMode.DISABLED)
    except Exception as exc:
        LOGGER.warning(f"slot blind box broadcast failed chat={chat_id}: {exc}")


def _telegram_member_is_active(member: Any) -> bool:
    status = str(getattr(getattr(member, "status", None), "value", getattr(member, "status", "")) or "").lower()
    if status in {"creator", "owner", "administrator", "member"}:
        return True
    if status == "restricted":
        return bool(getattr(member, "is_member", True))
    return False


async def _ensure_account_open_receiver_in_group(target_tg: int, item_type: str) -> None:
    if _normalize_backpack_item_type(item_type) != REWARD_TYPE_ACCOUNT_OPEN:
        return
    chat_id = _main_group_chat_id()
    if not chat_id:
        raise HTTPException(status_code=400, detail="主群未配置，无法接收开号资格")
    try:
        member = await bot.get_chat_member(chat_id=chat_id, user_id=int(target_tg))
    except Exception as exc:
        LOGGER.warning(f"slot box account open receiver group check failed chat={chat_id} tg={target_tg}: {exc}")
        raise HTTPException(status_code=400, detail="接收方不在主群内，不能接收开号资格") from exc
    if not _telegram_member_is_active(member):
        raise HTTPException(status_code=400, detail="接收方不在主群内，不能接收开号资格")


async def _account_open_receiver_in_group(target_tg: int) -> bool:
    try:
        await _ensure_account_open_receiver_in_group(target_tg, REWARD_TYPE_ACCOUNT_OPEN)
        return True
    except HTTPException:
        return False


def _available_prizes(
    state: dict[str, Any],
    *,
    guarantee_only: bool = False,
    account_open_receiver_ok: bool = True,
) -> list[dict[str, Any]]:
    prizes = []
    for prize in state.get("prizes") or []:
        if not prize.get("enabled") or int(prize.get("weight") or 0) <= 0:
            continue
        if int(prize.get("stock") or 0) == 0:
            continue
        if not account_open_receiver_ok and _normalize_reward_type(prize.get("reward_type")) == REWARD_TYPE_ACCOUNT_OPEN:
            continue
        if guarantee_only and not prize.get("guarantee_eligible"):
            continue
        prizes.append(prize)
    return prizes


def _pick_weighted(entries: list[tuple[str, dict[str, Any] | None, int]]) -> tuple[str, dict[str, Any] | None]:
    total = sum(max(int(weight or 0), 0) for _, _, weight in entries)
    if total <= 0:
        raise ValueError("抽奖池为空")
    ticket = RNG.randrange(total)
    cursor = 0
    for kind, prize, weight in entries:
        cursor += max(int(weight or 0), 0)
        if ticket < cursor:
            return kind, prize
    kind, prize, _ = entries[-1]
    return kind, prize


def _probability_summary(state: dict[str, Any], *, account_open_receiver_ok: bool = True) -> dict[str, Any]:
    settings = state.get("settings") or {}
    prizes = _available_prizes(state, account_open_receiver_ok=account_open_receiver_ok)
    blank_weight = int(settings.get("blank_weight") or 0) if settings.get("blank_enabled") else 0
    total_weight = sum(int(prize.get("weight") or 0) for prize in prizes) + blank_weight
    prize_rates: dict[str, float] = {}
    for prize in state.get("prizes") or []:
        active = prize in prizes
        rate = (int(prize.get("weight") or 0) / total_weight * 100) if active and total_weight else 0
        prize_rates[prize["id"]] = round(rate, 4)
    blank_rate = (blank_weight / total_weight * 100) if total_weight else 0
    return {
        "total_weight": total_weight,
        "blank_rate": round(blank_rate, 4),
        "prize_rates": prize_rates,
    }


def _public_prize(prize: dict[str, Any], probabilities: dict[str, Any]) -> dict[str, Any]:
    payload = dict(prize)
    payload["computed_rate"] = (probabilities.get("prize_rates") or {}).get(prize.get("id"), 0)
    return payload


def _global_stats(state: dict[str, Any]) -> dict[str, int]:
    user_rows = [row for row in (state.get("users") or {}).values() if isinstance(row, dict)]
    spin_count = sum(int(row.get("total_spins") or 0) for row in user_rows)
    win_count = sum(int(row.get("win_count") or 0) for row in user_rows)
    blank_count = sum(int(row.get("blank_count") or 0) for row in user_rows)
    if spin_count <= 0:
        records = state.get("records") or []
        spin_count = len(records)
        win_count = sum(1 for record in records if record.get("outcome") == "win")
        blank_count = max(spin_count - win_count, 0)
    return {
        "prize_count": len(state.get("prizes") or []),
        "active_prize_count": len(_available_prizes(state)),
        "spin_count": spin_count,
        "win_count": win_count,
        "blank_count": blank_count,
        "user_count": len(state.get("users") or {}),
    }


def _get_user_stats(state: dict[str, Any], user_id: int) -> dict[str, Any]:
    users = state.setdefault("users", {})
    key = str(int(user_id))
    user_stats = users.setdefault(
        key,
        {
            "total_spins": 0,
            "win_count": 0,
            "blank_count": 0,
            "miss_streak": 0,
            "last_spin_at": 0,
            "free_spin_tickets": 0,
            "daily_free_used": 0,
            "daily_key": _today_key(),
            "daily_count": 0,
        },
    )
    if user_stats.get("daily_key") != _today_key():
        user_stats["daily_key"] = _today_key()
        user_stats["daily_count"] = 0
        user_stats["daily_free_used"] = 0
    user_stats.setdefault("total_spins", 0)
    user_stats.setdefault("win_count", 0)
    user_stats.setdefault("blank_count", 0)
    user_stats.setdefault("miss_streak", 0)
    user_stats.setdefault("last_spin_at", 0)
    user_stats.setdefault("free_spin_tickets", 0)
    user_stats.setdefault("daily_free_used", 0)
    backpack = user_stats.setdefault("backpack", {})
    if not isinstance(backpack, dict):
        backpack = {}
        user_stats["backpack"] = backpack
    for item_type in BACKPACK_ITEM_TYPES:
        backpack[item_type] = max(int(backpack.get(item_type) or 0), 0)
    backpack[REWARD_TYPE_FREE_SPIN_TICKET] = max(
        int(backpack.get(REWARD_TYPE_FREE_SPIN_TICKET) or 0),
        int(user_stats.get("free_spin_tickets") or 0),
    )
    user_stats["free_spin_tickets"] = int(backpack.get(REWARD_TYPE_FREE_SPIN_TICKET) or 0)
    return user_stats


def _backpack(user_stats: dict[str, Any]) -> dict[str, int]:
    backpack = user_stats.setdefault("backpack", {})
    if not isinstance(backpack, dict):
        backpack = {}
        user_stats["backpack"] = backpack
    for item_type in BACKPACK_ITEM_TYPES:
        backpack[item_type] = max(int(backpack.get(item_type) or 0), 0)
    user_stats["free_spin_tickets"] = int(backpack.get(REWARD_TYPE_FREE_SPIN_TICKET) or 0)
    return backpack


def _backpack_summary(user_stats: dict[str, Any]) -> list[dict[str, Any]]:
    backpack = _backpack(user_stats)
    return [
        {
            "type": item_type,
            "label": BACKPACK_ITEM_META[item_type]["label"],
            "icon": BACKPACK_ITEM_META[item_type]["icon"],
            "quantity": int(backpack.get(item_type) or 0),
        }
        for item_type in BACKPACK_ITEM_TYPES
    ]


def _add_backpack_item(user_stats: dict[str, Any], item_type: str, quantity: int) -> dict[str, Any] | None:
    normalized_type = _normalize_backpack_item_type(item_type)
    qty = max(int(quantity or 0), 0)
    if qty <= 0:
        return None
    backpack = _backpack(user_stats)
    backpack[normalized_type] = int(backpack.get(normalized_type) or 0) + qty
    if normalized_type == REWARD_TYPE_FREE_SPIN_TICKET:
        user_stats["free_spin_tickets"] = int(backpack[normalized_type])
    return {
        "type": normalized_type,
        "label": BACKPACK_ITEM_META[normalized_type]["label"],
        "quantity": qty,
        "quantity_after": int(backpack.get(normalized_type) or 0),
    }


def _remove_backpack_item(user_stats: dict[str, Any], item_type: str, quantity: int) -> dict[str, Any]:
    normalized_type = _normalize_backpack_item_type(item_type)
    qty = max(int(quantity or 0), 1)
    backpack = _backpack(user_stats)
    current = int(backpack.get(normalized_type) or 0)
    if current < qty:
        raise ValueError(f"{BACKPACK_ITEM_META[normalized_type]['label']}数量不足")
    backpack[normalized_type] = current - qty
    if normalized_type == REWARD_TYPE_FREE_SPIN_TICKET:
        user_stats["free_spin_tickets"] = int(backpack[normalized_type])
    return {
        "type": normalized_type,
        "label": BACKPACK_ITEM_META[normalized_type]["label"],
        "quantity": qty,
        "quantity_after": int(backpack.get(normalized_type) or 0),
    }


def _account_level(account: Emby | None) -> str:
    level = str(getattr(account, "lv", "") or "d").strip().lower()
    return level if level in LEVEL_CODES else "d"


def _effective_daily_limit(settings: dict[str, Any], level: str) -> int:
    level_limit = int((settings.get("daily_limit_by_level") or {}).get(level, 0) or 0)
    return level_limit if level_limit > 0 else int(settings.get("daily_limit") or 0)


def _daily_gift_total(settings: dict[str, Any], level: str) -> int:
    return int((settings.get("daily_gift_by_level") or {}).get(level, 0) or 0)


def _consume_spin_payment(user_stats: dict[str, Any], settings: dict[str, Any], account: Emby) -> dict[str, Any]:
    level = _account_level(account)
    gift_total = _daily_gift_total(settings, level)
    daily_free_used = int(user_stats.get("daily_free_used") or 0)
    if daily_free_used < gift_total:
        user_stats["daily_free_used"] = daily_free_used + 1
        return {
            "method": "daily_gift",
            "cost_iv": 0,
            "balance_after": int(account.iv or 0),
            "free_spin_tickets_after": int(user_stats.get("free_spin_tickets") or 0),
            "daily_free_remaining": max(gift_total - int(user_stats.get("daily_free_used") or 0), 0),
        }

    backpack = _backpack(user_stats)
    free_tickets = int(backpack.get(REWARD_TYPE_FREE_SPIN_TICKET) or 0)
    if free_tickets > 0:
        _remove_backpack_item(user_stats, REWARD_TYPE_FREE_SPIN_TICKET, 1)
        return {
            "method": "ticket",
            "cost_iv": 0,
            "balance_after": int(account.iv or 0),
            "free_spin_tickets_after": int(user_stats.get("free_spin_tickets") or 0),
            "daily_free_remaining": 0,
        }

    spin_cost = int(settings.get("spin_cost_iv") or 0)
    balance = int(account.iv or 0)
    if balance < spin_cost:
        raise HTTPException(status_code=400, detail=f"{settings.get('currency_name') or pivkeyu}不足")
    account.iv = balance - spin_cost
    return {
        "method": "currency",
        "cost_iv": spin_cost,
        "balance_after": int(account.iv or 0),
        "free_spin_tickets_after": int(user_stats.get("free_spin_tickets") or 0),
        "daily_free_remaining": 0,
    }


def _payment_label(payment: dict[str, Any], settings: dict[str, Any]) -> str:
    method = payment.get("method")
    if method == "daily_gift":
        return "每日赠送次数"
    if method == "ticket":
        return "抽奖券"
    return f"{int(payment.get('cost_iv') or 0)} {settings.get('currency_name') or pivkeyu}"


def _apply_prize_reward(user_stats: dict[str, Any], prize: dict[str, Any]) -> dict[str, Any] | None:
    reward_type = _normalize_reward_type(prize.get("reward_type"))
    if reward_type not in BACKPACK_ITEM_TYPES:
        return None
    quantity = max(int(prize.get("free_spin_quantity") or 1), 1)
    grant = _add_backpack_item(user_stats, reward_type, quantity)
    if grant is None:
        return None
    return {
        "type": reward_type,
        "label": BACKPACK_ITEM_META[reward_type]["label"],
        "quantity": quantity,
        "quantity_after": grant["quantity_after"],
        "free_spin_tickets_after": int(user_stats.get("free_spin_tickets") or 0),
    }


def _symbol_pool(state: dict[str, Any]) -> list[str]:
    symbols = [str(prize.get("icon") or "🎁") for prize in state.get("prizes") or [] if prize.get("enabled")]
    blank_icon = str((state.get("settings") or {}).get("blank_icon") or "◇")
    symbols.append(blank_icon)
    symbols.extend(["✦", "◆", "★"])
    unique = []
    for symbol in symbols:
        if symbol and symbol not in unique:
            unique.append(symbol[:16])
    return unique[:24] or ["🎁", "◇", "✦"]


def _blank_reels(state: dict[str, Any]) -> list[str]:
    pool = _symbol_pool(state)
    if len(pool) == 1:
        return [pool[0], "✦", "◆"]
    reels = [RNG.choice(pool) for _ in range(3)]
    if reels[0] == reels[1] == reels[2]:
        alternatives = [symbol for symbol in pool if symbol != reels[0]] or ["✦"]
        reels[2] = RNG.choice(alternatives)
    return reels


def _public_records(records: list[dict[str, Any]], *, user_id: int | None = None, limit: int = 20) -> list[dict[str, Any]]:
    filtered = records
    if user_id is not None:
        filtered = [record for record in records if int(record.get("user_id") or 0) == int(user_id)]
    return [dict(record) for record in filtered[: max(int(limit or 20), 1)]]


def _active_market_listings(state: dict[str, Any]) -> list[dict[str, Any]]:
    rows = [dict(item) for item in state.get("market_listings") or [] if item.get("status") == "active"]
    rows.sort(key=lambda item: item.get("created_at") or "", reverse=True)
    for item in rows:
        meta = BACKPACK_ITEM_META.get(item.get("item_type"), {})
        item["item_label"] = meta.get("label", item.get("item_type"))
        item["item_icon"] = meta.get("icon", "◇")
    return rows


def _public_redeem_codes(state: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for code in state.get("redeem_codes") or []:
        payload = dict(code)
        payload["used_by_count"] = len(payload.get("used_by") or {})
        rows.append(payload)
    rows.sort(key=lambda item: item.get("created_at") or "", reverse=True)
    return rows[:200]


def _build_bottom_nav() -> list[dict[str, str]]:
    items = [{"id": "home", "label": "主页", "path": "/miniapp", "icon": "🏠"}]
    plugin_nav = getattr(config, "plugin_nav", {}) or {}
    for plugin in list_miniapp_plugins():
        if not plugin.get("enabled") or not plugin.get("loaded") or not plugin.get("web_registered"):
            continue
        visible = bool(plugin_nav.get(plugin["id"], plugin.get("bottom_nav_default", False)))
        if not plugin.get("miniapp_path") or not visible:
            continue
        items.append(
            {
                "id": plugin["id"],
                "label": plugin.get("miniapp_label") or plugin["name"],
                "path": plugin["miniapp_path"],
                "icon": plugin.get("miniapp_icon") or "◇",
            }
        )
    return items


def _serialize_bundle(
    state: dict[str, Any],
    *,
    user_id: int | None = None,
    include_admin: bool = False,
    account: Emby | None = None,
) -> dict[str, Any]:
    probabilities = _probability_summary(state)
    prizes = [_public_prize(prize, probabilities) for prize in state.get("prizes") or []]
    settings = dict(state.get("settings") or {})
    bundle = {
        "meta": {
            "plugin_name": PLUGIN_MANIFEST.get("name"),
            "version": PLUGIN_MANIFEST.get("version"),
            "symbols": _symbol_pool(state),
            "bottom_nav": _build_bottom_nav(),
        },
        "settings": settings,
        "probabilities": probabilities,
        "prizes": prizes if include_admin else [prize for prize in prizes if prize.get("enabled")],
        "stats": _global_stats(state),
        "records": _public_records(
            state.get("records") or [],
            user_id=None if include_admin else user_id,
            limit=80 if include_admin else 20,
        ),
        "market_listings": _active_market_listings(state),
        "redeem_codes": _public_redeem_codes(state) if include_admin else [],
        "permissions": {
            "is_admin": bool(user_id is not None and is_admin_user_id(int(user_id))),
            "admin_url": "/plugins/slot-box/admin" if user_id is not None and is_admin_user_id(int(user_id)) else None,
        },
    }
    account_payload = None
    if user_id is not None:
        if account is None:
            account = sql_get_emby(user_id)
        if account is not None:
            account_payload = serialize_emby_user(account)

    bundle["account"] = account_payload

    if user_id is not None:
        user_stats = deepcopy(_get_user_stats(state, int(user_id)))
        level = _account_level(account)
        now_ts = int(time.time())
        cooldown = int(settings.get("cooldown_seconds") or 0)
        wait_seconds = max(cooldown - (now_ts - int(user_stats.get("last_spin_at") or 0)), 0) if cooldown else 0
        daily_limit = _effective_daily_limit(settings, level)
        daily_gift_total = _daily_gift_total(settings, level)
        daily_free_used = int(user_stats.get("daily_free_used") or 0)
        bundle["user_stats"] = user_stats
        bundle["backpack"] = _backpack_summary(user_stats)
        bundle["limits"] = {
            "daily_limit": daily_limit,
            "daily_remaining": None if daily_limit <= 0 else max(daily_limit - int(user_stats.get("daily_count") or 0), 0),
            "daily_gift_total": daily_gift_total,
            "daily_free_remaining": max(daily_gift_total - daily_free_used, 0),
            "cooldown_seconds": cooldown,
            "wait_seconds": wait_seconds,
            "spin_cost_iv": int(settings.get("spin_cost_iv") or 0),
            "currency_name": settings.get("currency_name") or pivkeyu,
            "free_spin_tickets": int(user_stats.get("free_spin_tickets") or 0),
            "user_level": level,
            "user_level_text": get_level_meta(level)["short_text"],
        }
    return bundle


def _update_settings(patch: dict[str, Any]) -> dict[str, Any]:
    allowed = set(DEFAULT_SETTINGS)
    sanitized = {key: value for key, value in patch.items() if key in allowed and value is not None}
    with STATE_LOCK:
        state = _load_state_unlocked()
        settings = dict(state.get("settings") or {})
        settings.update(sanitized)
        state["settings"] = _normalize_settings(settings)
        _save_state_unlocked(state)
        return _serialize_bundle(state, include_admin=True)


def _create_prize(payload: dict[str, Any]) -> dict[str, Any]:
    with STATE_LOCK:
        state = _load_state_unlocked()
        prize = _clean_prize(payload)
        existing_ids = {item["id"] for item in state.get("prizes") or []}
        original_id = prize["id"]
        while prize["id"] in existing_ids:
            prize["id"] = _clean_prize_id(f"{original_id}-{uuid4().hex[:4]}")
        state.setdefault("prizes", []).append(prize)
        _save_state_unlocked(state)
        return _serialize_bundle(state, include_admin=True)


def _patch_prize(prize_id: str, patch: dict[str, Any]) -> dict[str, Any]:
    with STATE_LOCK:
        state = _load_state_unlocked()
        for index, prize in enumerate(state.get("prizes") or []):
            if prize.get("id") != prize_id:
                continue
            merged = dict(prize)
            merged.update({key: value for key, value in patch.items() if value is not None})
            state["prizes"][index] = _clean_prize(merged, existing=prize)
            _save_state_unlocked(state)
            return _serialize_bundle(state, include_admin=True)
    raise HTTPException(status_code=404, detail="奖品不存在")


def _delete_prize(prize_id: str) -> dict[str, Any]:
    with STATE_LOCK:
        state = _load_state_unlocked()
        before_count = len(state.get("prizes") or [])
        state["prizes"] = [prize for prize in state.get("prizes") or [] if prize.get("id") != prize_id]
        if len(state["prizes"]) == before_count:
            raise HTTPException(status_code=404, detail="奖品不存在")
        _save_state_unlocked(state)
        return _serialize_bundle(state, include_admin=True)


def _create_redeem_code(payload: dict[str, Any]) -> dict[str, Any]:
    with STATE_LOCK:
        state = _load_state_unlocked()
        code = _clean_redeem_code(payload)
        existing_codes = {item.get("code") for item in state.get("redeem_codes") or []}
        original_code = code["code"]
        suffix = 1
        while code["code"] in existing_codes:
            suffix += 1
            code["code"] = _normalize_redeem_code(f"{original_code}-{suffix}")
        state.setdefault("redeem_codes", []).append(code)
        _save_state_unlocked(state)
        return _serialize_bundle(state, include_admin=True)


def _patch_redeem_code(code_value: str, patch: dict[str, Any]) -> dict[str, Any]:
    normalized_code = _normalize_redeem_code(code_value)
    with STATE_LOCK:
        state = _load_state_unlocked()
        for index, code in enumerate(state.get("redeem_codes") or []):
            if code.get("code") != normalized_code:
                continue
            merged = dict(code)
            merged.update({key: value for key, value in patch.items() if value is not None})
            state["redeem_codes"][index] = _clean_redeem_code(merged, existing=code)
            _save_state_unlocked(state)
            return _serialize_bundle(state, include_admin=True)
    raise HTTPException(status_code=404, detail="兑换码不存在")


def _delete_redeem_code(code_value: str) -> dict[str, Any]:
    normalized_code = _normalize_redeem_code(code_value)
    with STATE_LOCK:
        state = _load_state_unlocked()
        before_count = len(state.get("redeem_codes") or [])
        state["redeem_codes"] = [code for code in state.get("redeem_codes") or [] if code.get("code") != normalized_code]
        if len(state["redeem_codes"]) == before_count:
            raise HTTPException(status_code=404, detail="兑换码不存在")
        _save_state_unlocked(state)
        return _serialize_bundle(state, include_admin=True)


def _redeem_code_for_user(user_id: int, code_value: str) -> dict[str, Any]:
    normalized_code = _normalize_redeem_code(code_value)
    with STATE_LOCK:
        state = _load_state_unlocked()
        account = sql_get_emby(user_id)
        for code in state.get("redeem_codes") or []:
            if code.get("code") != normalized_code:
                continue
            if not code.get("enabled"):
                raise HTTPException(status_code=400, detail="兑换码已停用")
            max_uses = int(code.get("max_uses") or 0)
            if max_uses > 0 and int(code.get("used_count") or 0) >= max_uses:
                raise HTTPException(status_code=400, detail="兑换码使用次数已满")
            used_by = code.setdefault("used_by", {})
            user_key = str(int(user_id))
            per_user_limit = int(code.get("per_user_limit") or 1)
            if int(used_by.get(user_key) or 0) >= per_user_limit:
                raise HTTPException(status_code=400, detail="你已经使用过这个兑换码")
            user_stats = _get_user_stats(state, int(user_id))
            grants = _clean_grants(code.get("grants"))
            granted = []
            for item_type, quantity in grants.items():
                grant = _add_backpack_item(user_stats, item_type, quantity)
                if grant:
                    granted.append(grant)
            if not granted:
                raise HTTPException(status_code=400, detail="兑换码没有可发放内容")
            code["used_count"] = int(code.get("used_count") or 0) + 1
            used_by[user_key] = int(used_by.get(user_key) or 0) + 1
            code["updated_at"] = _iso_now()
            _save_state_unlocked(state)
            bundle = _serialize_bundle(state, user_id=user_id, account=account)
            return {"granted": granted, **bundle}
    raise HTTPException(status_code=404, detail="兑换码不存在")


def _transfer_item(sender_tg: int, target_tg: int, item_type: str, quantity: int) -> dict[str, Any]:
    normalized_type = _normalize_backpack_item_type(item_type)
    qty = max(int(quantity or 1), 1)
    if int(sender_tg) == int(target_tg):
        raise HTTPException(status_code=400, detail="不能转赠给自己")
    with STATE_LOCK:
        state = _load_state_unlocked()
        sender_stats = _get_user_stats(state, int(sender_tg))
        target_stats = _get_user_stats(state, int(target_tg))
        _remove_backpack_item(sender_stats, normalized_type, qty)
        _add_backpack_item(target_stats, normalized_type, qty)
        _save_state_unlocked(state)
        return _serialize_bundle(state, user_id=int(sender_tg))


def _create_listing(user: dict[str, Any], item_type: str, quantity: int, price_iv: int) -> dict[str, Any]:
    seller_tg = int(user["id"])
    normalized_type = _normalize_backpack_item_type(item_type)
    qty = _clean_int(quantity, default=1, minimum=1, maximum=1_000_000, field_name="上架数量")
    price = _clean_int(price_iv, default=0, minimum=0, maximum=MAX_SPIN_COST, field_name="上架价格")
    with STATE_LOCK:
        state = _load_state_unlocked()
        seller_stats = _get_user_stats(state, seller_tg)
        _remove_backpack_item(seller_stats, normalized_type, qty)
        listing = {
            "id": uuid4().hex[:12],
            "seller_tg": seller_tg,
            "seller_display": _telegram_user_label(user),
            "item_type": normalized_type,
            "quantity": qty,
            "price_iv": price,
            "status": "active",
            "created_at": _iso_now(),
            "updated_at": _iso_now(),
        }
        state.setdefault("market_listings", []).insert(0, listing)
        _save_state_unlocked(state)
        return _serialize_bundle(state, user_id=seller_tg)


def _cancel_listing(user_id: int, listing_id: str) -> dict[str, Any]:
    with STATE_LOCK:
        state = _load_state_unlocked()
        for listing in state.get("market_listings") or []:
            if listing.get("id") != listing_id or listing.get("status") != "active":
                continue
            if int(listing.get("seller_tg") or 0) != int(user_id) and not is_admin_user_id(int(user_id)):
                raise HTTPException(status_code=403, detail="不能取消别人的上架")
            seller_stats = _get_user_stats(state, int(listing.get("seller_tg")))
            _add_backpack_item(seller_stats, listing.get("item_type"), int(listing.get("quantity") or 0))
            listing["status"] = "cancelled"
            listing["updated_at"] = _iso_now()
            _save_state_unlocked(state)
            return _serialize_bundle(state, user_id=int(user_id))
    raise HTTPException(status_code=404, detail="上架商品不存在")


def _purchase_listing(user_id: int, listing_id: str) -> dict[str, Any]:
    with STATE_LOCK:
        state = _load_state_unlocked()
        state_before_purchase = deepcopy(state)
        listing = next(
            (item for item in state.get("market_listings") or [] if item.get("id") == listing_id and item.get("status") == "active"),
            None,
        )
        if listing is None:
            raise HTTPException(status_code=404, detail="上架商品不存在或已售出")
        seller_tg = int(listing.get("seller_tg") or 0)
        if seller_tg == int(user_id):
            raise HTTPException(status_code=400, detail="不能购买自己上架的物品")
        with Session() as session:
            buyer = session.query(Emby).filter(Emby.tg == int(user_id)).with_for_update().first()
            if buyer is None:
                raise HTTPException(status_code=403, detail="未找到你的 Emby 账户")
            seller = session.query(Emby).filter(Emby.tg == seller_tg).with_for_update().first()
            if seller is None:
                raise HTTPException(status_code=400, detail="卖家 Emby 账户不存在")
            price = int(listing.get("price_iv") or 0)
            if int(buyer.iv or 0) < price:
                raise HTTPException(status_code=400, detail=f"{pivkeyu}不足")
            buyer_before = _serialize_emby_row(buyer)
            seller_before = _serialize_emby_row(seller)
            buyer.iv = int(buyer.iv or 0) - price
            seller.iv = int(seller.iv or 0) + price
            buyer_stats = _get_user_stats(state, int(user_id))
            _add_backpack_item(buyer_stats, listing.get("item_type"), int(listing.get("quantity") or 0))
            listing["status"] = "sold"
            listing["buyer_tg"] = int(user_id)
            listing["sold_at"] = _iso_now()
            listing["updated_at"] = _iso_now()
            try:
                session.commit()
            except Exception:
                session.rollback()
                _save_state_unlocked(state_before_purchase)
                raise
            session.refresh(buyer)
            session.refresh(seller)
            _invalidate_emby_payload(buyer_before)
            _invalidate_emby_payload(_serialize_emby_row(buyer))
            _invalidate_emby_payload(seller_before)
            _invalidate_emby_payload(_serialize_emby_row(seller))
            _save_state_unlocked(state)
            return _serialize_bundle(state, user_id=int(user_id), account=buyer)
    raise HTTPException(status_code=404, detail="上架商品不存在或已售出")


def _spin_for_user(user: dict[str, Any], *, account_open_receiver_ok: bool = True) -> dict[str, Any]:
    user_id = int(user["id"])
    user_label = _telegram_user_label(user)
    with STATE_LOCK:
        state = _load_state_unlocked()
        state_before_spin = deepcopy(state)
        settings = state.get("settings") or {}
        if not settings.get("enabled", True):
            raise HTTPException(status_code=403, detail="盲盒当前未开放")

        with Session() as session:
            account = session.query(Emby).filter(Emby.tg == user_id).with_for_update().first()
            if account is None:
                raise HTTPException(status_code=403, detail="未找到你的 Emby 账户，不能参与抽奖")
            account_before_payload = _serialize_emby_row(account)

            user_stats = _get_user_stats(state, user_id)
            level = _account_level(account)
            now_ts = int(time.time())
            cooldown = int(settings.get("cooldown_seconds") or 0)
            if cooldown and now_ts - int(user_stats.get("last_spin_at") or 0) < cooldown:
                wait_seconds = cooldown - (now_ts - int(user_stats.get("last_spin_at") or 0))
                raise HTTPException(status_code=429, detail=f"抽取冷却中，还需等待 {wait_seconds} 秒")

            daily_limit = _effective_daily_limit(settings, level)
            if daily_limit and int(user_stats.get("daily_count") or 0) >= daily_limit:
                raise HTTPException(status_code=429, detail="今日抽取次数已用完")

            prize_pool = _available_prizes(state, account_open_receiver_ok=account_open_receiver_ok)
            guarantee_pool = _available_prizes(
                state,
                guarantee_only=True,
                account_open_receiver_ok=account_open_receiver_ok,
            )
            blank_weight = int(settings.get("blank_weight") or 0) if settings.get("blank_enabled") else 0
            if not prize_pool and blank_weight <= 0:
                raise HTTPException(status_code=400, detail="抽奖池为空，请先在后台配置奖品或轮空权重")

            payment = _consume_spin_payment(user_stats, settings, account)
            payment_label = _payment_label(payment, settings)

            pity_after = int(settings.get("pity_after") or 0)
            pity_triggered = bool(
                settings.get("pity_enabled")
                and pity_after > 0
                and guarantee_pool
                and int(user_stats.get("miss_streak") or 0) + 1 >= pity_after
            )

            if pity_triggered:
                entries = [("prize", prize, int(prize.get("weight") or 0)) for prize in guarantee_pool]
                outcome, prize = _pick_weighted(entries)
            else:
                entries = [("prize", prize, int(prize.get("weight") or 0)) for prize in prize_pool]
                if blank_weight > 0:
                    entries.append(("blank", None, blank_weight))
                outcome, prize = _pick_weighted(entries)

            draw_probabilities = _probability_summary(state, account_open_receiver_ok=account_open_receiver_ok)

            user_stats["total_spins"] = int(user_stats.get("total_spins") or 0) + 1
            user_stats["daily_count"] = int(user_stats.get("daily_count") or 0) + 1
            user_stats["last_spin_at"] = now_ts

            record: dict[str, Any]
            broadcast_payload: dict[str, Any] | None = None
            reward_grant: dict[str, Any] | None = None
            if outcome == "prize" and prize is not None:
                if int(prize.get("stock") or 0) > 0:
                    prize["stock"] = int(prize.get("stock") or 0) - 1
                    prize["updated_at"] = _iso_now()
                reward_grant = _apply_prize_reward(user_stats, prize)
                user_stats["win_count"] = int(user_stats.get("win_count") or 0) + 1
                user_stats["miss_streak"] = 0
                reels = [str(prize.get("icon") or "🎁") for _ in range(3)]
                message = prize.get("delivery_text") or prize.get("description") or "请联系管理员处理奖励发放。"
                if reward_grant:
                    message = (
                        f"{message}\n已放入背包：{reward_grant.get('label')} "
                        f"x{int(reward_grant.get('quantity') or 0)}。"
                    )
                result = {
                    "outcome": "win",
                    "title": f"抽中 {prize.get('name')}",
                    "message": message,
                    "prize": dict(prize),
                    "reels": reels,
                    "pity_triggered": pity_triggered,
                    "payment": payment,
                    "payment_label": payment_label,
                    "reward_grant": reward_grant,
                }
                record = {
                    "id": uuid4().hex[:12],
                    "user_id": user_id,
                    "user_display": user_label,
                    "outcome": "win",
                    "prize_id": prize.get("id"),
                    "prize_name": prize.get("name"),
                    "prize_icon": prize.get("icon"),
                    "payment_method": payment.get("method"),
                    "cost_iv": payment.get("cost_iv", 0),
                    "reward_type": prize.get("reward_type"),
                    "reward_quantity": 0 if not reward_grant else reward_grant.get("quantity", 0),
                    "pity_triggered": pity_triggered,
                    "created_at": _iso_now(),
                }
                if prize.get("broadcast_enabled"):
                    broadcast_payload = {
                        "text": _broadcast_text(
                            user_label=user_label,
                            prize=prize,
                            probabilities=draw_probabilities,
                            pity_triggered=pity_triggered,
                        ),
                        "image_url": prize.get("broadcast_image_url") or "",
                    }
            else:
                user_stats["blank_count"] = int(user_stats.get("blank_count") or 0) + 1
                user_stats["miss_streak"] = int(user_stats.get("miss_streak") or 0) + 1
                result = {
                    "outcome": "blank",
                    "title": settings.get("blank_label") or "轮空",
                    "message": "本次没有抽中奖品。",
                    "prize": None,
                    "reels": _blank_reels(state),
                    "pity_triggered": False,
                    "payment": payment,
                    "payment_label": payment_label,
                    "reward_grant": None,
                }
                record = {
                    "id": uuid4().hex[:12],
                    "user_id": user_id,
                    "user_display": user_label,
                    "outcome": "blank",
                    "prize_id": None,
                    "prize_name": settings.get("blank_label") or "轮空",
                    "prize_icon": settings.get("blank_icon") or "◇",
                    "payment_method": payment.get("method"),
                    "cost_iv": payment.get("cost_iv", 0),
                    "pity_triggered": False,
                    "created_at": _iso_now(),
                }

            state.setdefault("records", []).insert(0, record)
            record_limit = int(settings.get("record_limit") or 300)
            state["records"] = state["records"][:record_limit]
            _save_state_unlocked(state)

            try:
                session.commit()
            except Exception:
                session.rollback()
                _save_state_unlocked(state_before_spin)
                raise
            session.refresh(account)
            _invalidate_emby_payload(account_before_payload)
            _invalidate_emby_payload(_serialize_emby_row(account))

            bundle = _serialize_bundle(state, user_id=user_id, account=account)
            return {"result": result, "broadcast": broadcast_payload, **bundle}


def _bootstrap_user_bundle(user_id: int) -> dict[str, Any]:
    with STATE_LOCK:
        state = _load_state_unlocked()
        return _serialize_bundle(state, user_id=user_id)


def _bootstrap_admin_bundle() -> dict[str, Any]:
    with STATE_LOCK:
        state = _load_state_unlocked()
        return _serialize_bundle(state, include_admin=True)


def _raise_value_error(exc: Exception) -> HTTPException:
    if isinstance(exc, HTTPException):
        return exc
    if isinstance(exc, ValueError):
        return HTTPException(status_code=400, detail=str(exc))
    return HTTPException(status_code=500, detail="老虎机盲盒数据写入失败")


def register_web(app, context=None) -> None:
    _configure_state_path(context)
    user_router = APIRouter(prefix="/plugins/slot-box", tags=["slot-box-user"])
    admin_router = APIRouter(prefix="/plugins/slot-box/admin-api", tags=["slot-box-admin"])

    if STATIC_DIR.exists():
        app.mount("/plugins/slot-box/static", StaticFiles(directory=STATIC_DIR), name="slot-box-static")

    @user_router.get("/app")
    def slot_app_page():
        return FileResponse(STATIC_DIR / "app.html")

    @user_router.get("/admin")
    def slot_admin_page():
        return FileResponse(STATIC_DIR / "admin.html")

    @user_router.post("/api/bootstrap")
    async def slot_bootstrap(payload: InitDataPayload):
        user = await run_in_threadpool(_verify_user_from_init_data, payload.init_data)
        bundle = await run_in_threadpool(_bootstrap_user_bundle, int(user["id"]))
        return {"code": 200, "data": bundle}

    @user_router.post("/api/spin")
    async def slot_spin(payload: InitDataPayload):
        user = await run_in_threadpool(_verify_user_from_init_data, payload.init_data)
        account_open_receiver_ok = await _account_open_receiver_in_group(int(user["id"]))
        try:
            bundle = await run_in_threadpool(_spin_for_user, user, account_open_receiver_ok=account_open_receiver_ok)
        except Exception as exc:
            raise _raise_value_error(exc) from exc
        await _send_group_broadcast(bundle.pop("broadcast", None))
        return {"code": 200, "data": bundle}

    @user_router.post("/api/redeem")
    async def slot_redeem(payload: RedeemCodePayload):
        user = await run_in_threadpool(_verify_user_from_init_data, payload.init_data)
        with STATE_LOCK:
            state = _load_state_unlocked()
            code = next((item for item in state.get("redeem_codes") or [] if item.get("code") == _normalize_redeem_code(payload.code)), None)
            grants = _clean_grants(code.get("grants") if code else {})
        if grants.get(REWARD_TYPE_ACCOUNT_OPEN, 0) > 0:
            await _ensure_account_open_receiver_in_group(int(user["id"]), REWARD_TYPE_ACCOUNT_OPEN)
        try:
            bundle = await run_in_threadpool(_redeem_code_for_user, int(user["id"]), payload.code)
        except Exception as exc:
            raise _raise_value_error(exc) from exc
        return {"code": 200, "data": bundle}

    @user_router.post("/api/transfer")
    async def slot_transfer(payload: TransferItemPayload):
        user = await run_in_threadpool(_verify_user_from_init_data, payload.init_data)
        await _ensure_account_open_receiver_in_group(int(payload.target_tg), payload.item_type)
        try:
            bundle = await run_in_threadpool(
                _transfer_item,
                int(user["id"]),
                int(payload.target_tg),
                payload.item_type,
                payload.quantity,
            )
        except Exception as exc:
            raise _raise_value_error(exc) from exc
        return {"code": 200, "data": bundle}

    @user_router.post("/api/listing")
    async def slot_create_listing(payload: ListingPayload):
        user = await run_in_threadpool(_verify_user_from_init_data, payload.init_data)
        try:
            bundle = await run_in_threadpool(
                _create_listing,
                user,
                payload.item_type,
                payload.quantity,
                payload.price_iv,
            )
        except Exception as exc:
            raise _raise_value_error(exc) from exc
        return {"code": 200, "data": bundle}

    @user_router.post("/api/listing/purchase")
    async def slot_purchase_listing(payload: ListingPurchasePayload):
        user = await run_in_threadpool(_verify_user_from_init_data, payload.init_data)
        with STATE_LOCK:
            state = _load_state_unlocked()
            listing = next(
                (item for item in state.get("market_listings") or [] if item.get("id") == payload.listing_id and item.get("status") == "active"),
                None,
            )
            listing_type = None if listing is None else listing.get("item_type")
        if listing_type:
            await _ensure_account_open_receiver_in_group(int(user["id"]), listing_type)
        try:
            bundle = await run_in_threadpool(_purchase_listing, int(user["id"]), payload.listing_id)
        except Exception as exc:
            raise _raise_value_error(exc) from exc
        return {"code": 200, "data": bundle}

    @user_router.post("/api/listing/cancel")
    async def slot_cancel_listing(payload: ListingCancelPayload):
        user = await run_in_threadpool(_verify_user_from_init_data, payload.init_data)
        try:
            bundle = await run_in_threadpool(_cancel_listing, int(user["id"]), payload.listing_id)
        except Exception as exc:
            raise _raise_value_error(exc) from exc
        return {"code": 200, "data": bundle}

    @admin_router.post("/bootstrap")
    async def slot_admin_bootstrap(payload: AdminBootstrapPayload):
        admin_user = await run_in_threadpool(_verify_admin_credential, payload.token, payload.init_data)
        bundle = await run_in_threadpool(_bootstrap_admin_bundle)
        return {"code": 200, "data": {"admin_user": admin_user, **bundle}}

    @admin_router.post("/settings")
    async def slot_settings_api(payload: SettingsPatchPayload, request: Request):
        token = request.headers.get("x-admin-token")
        init_data = request.headers.get("x-telegram-init-data")
        await run_in_threadpool(_verify_admin_credential, token, init_data)
        try:
            bundle = await run_in_threadpool(_update_settings, payload.model_dump(exclude_unset=True))
        except Exception as exc:
            raise _raise_value_error(exc) from exc
        return {"code": 200, "data": bundle}

    @admin_router.post("/prize")
    async def slot_prize_api(payload: PrizePayload, request: Request):
        token = request.headers.get("x-admin-token")
        init_data = request.headers.get("x-telegram-init-data")
        await run_in_threadpool(_verify_admin_credential, token, init_data)
        try:
            bundle = await run_in_threadpool(_create_prize, payload.model_dump())
        except Exception as exc:
            raise _raise_value_error(exc) from exc
        return {"code": 200, "data": bundle}

    @admin_router.patch("/prize/{prize_id}")
    async def slot_prize_patch_api(prize_id: str, payload: PrizePatchPayload, request: Request):
        token = request.headers.get("x-admin-token")
        init_data = request.headers.get("x-telegram-init-data")
        await run_in_threadpool(_verify_admin_credential, token, init_data)
        try:
            bundle = await run_in_threadpool(_patch_prize, prize_id, payload.model_dump(exclude_unset=True))
        except Exception as exc:
            raise _raise_value_error(exc) from exc
        return {"code": 200, "data": bundle}

    @admin_router.delete("/prize/{prize_id}")
    async def slot_prize_delete_api(prize_id: str, request: Request):
        token = request.headers.get("x-admin-token")
        init_data = request.headers.get("x-telegram-init-data")
        await run_in_threadpool(_verify_admin_credential, token, init_data)
        try:
            bundle = await run_in_threadpool(_delete_prize, prize_id)
        except Exception as exc:
            raise _raise_value_error(exc) from exc
        return {"code": 200, "data": bundle}

    @admin_router.post("/redeem-code")
    async def slot_redeem_code_create_api(payload: RedeemCodeAdminPayload, request: Request):
        token = request.headers.get("x-admin-token")
        init_data = request.headers.get("x-telegram-init-data")
        await run_in_threadpool(_verify_admin_credential, token, init_data)
        try:
            bundle = await run_in_threadpool(_create_redeem_code, payload.model_dump())
        except Exception as exc:
            raise _raise_value_error(exc) from exc
        return {"code": 200, "data": bundle}

    @admin_router.patch("/redeem-code/{code_value}")
    async def slot_redeem_code_patch_api(code_value: str, payload: RedeemCodeAdminPatchPayload, request: Request):
        token = request.headers.get("x-admin-token")
        init_data = request.headers.get("x-telegram-init-data")
        await run_in_threadpool(_verify_admin_credential, token, init_data)
        try:
            bundle = await run_in_threadpool(_patch_redeem_code, code_value, payload.model_dump(exclude_unset=True))
        except Exception as exc:
            raise _raise_value_error(exc) from exc
        return {"code": 200, "data": bundle}

    @admin_router.delete("/redeem-code/{code_value}")
    async def slot_redeem_code_delete_api(code_value: str, request: Request):
        token = request.headers.get("x-admin-token")
        init_data = request.headers.get("x-telegram-init-data")
        await run_in_threadpool(_verify_admin_credential, token, init_data)
        try:
            bundle = await run_in_threadpool(_delete_redeem_code, code_value)
        except Exception as exc:
            raise _raise_value_error(exc) from exc
        return {"code": 200, "data": bundle}

    app.include_router(user_router)
    app.include_router(admin_router)


def register_bot(_bot, context=None) -> None:
    _configure_state_path(context)
    return None

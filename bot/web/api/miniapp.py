from __future__ import annotations

import asyncio
import hmac
import json
from datetime import datetime, timedelta
from hashlib import sha256
from time import time
from urllib.parse import parse_qsl

from fastapi import APIRouter, HTTPException
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel

from bot import LOGGER, admins, api as api_config, bot, bot_token, config, owner, pivkeyu, ranks
from bot.plugins import list_miniapp_plugins
from bot.sql_helper.sql_bot_access import find_bot_access_block
from bot.sql_helper.sql_emby import sql_get_emby
from bot.sql_helper.sql_invite import (
    INVITE_CREDIT_TYPE_ACCOUNT_OPEN,
    INVITE_CREDIT_TYPE_GROUP,
    available_invite_credit_count,
    cancel_pending_invite_record,
    create_account_open_invite_record,
    create_invite_record,
    get_invite_settings,
    has_viewing_access,
    list_invite_records,
)
from bot.web.presenters import serialize_emby_user

router = APIRouter(prefix="/miniapp-api", tags=["小程序"])


class MiniAppInitRequest(BaseModel):
    init_data: str


class MiniAppInviteCreateRequest(MiniAppInitRequest):
    invitee_tg: int
    note: str | None = None


def _public_invite_record(record: dict | None, *, include_link: bool = False) -> dict | None:
    if record is None:
        return None
    payload = dict(record)
    if not include_link:
        payload.pop("invite_link", None)
    return payload


def _public_invite_bundle(user_id: int, account=None) -> dict:
    account = account if account is not None else sql_get_emby(user_id)
    settings = get_invite_settings()
    has_access = has_viewing_access(account)
    group_count = available_invite_credit_count(user_id, credit_type=INVITE_CREDIT_TYPE_GROUP) if has_access else 0
    account_open_count = (
        available_invite_credit_count(user_id, credit_type=INVITE_CREDIT_TYPE_ACCOUNT_OPEN) if has_access else 0
    )
    group_records = [
        _public_invite_record(item)
        for item in list_invite_records(inviter_tg=user_id, credit_type=INVITE_CREDIT_TYPE_GROUP, limit=20)
    ]
    account_open_records = [
        _public_invite_record(item)
        for item in list_invite_records(inviter_tg=user_id, credit_type=INVITE_CREDIT_TYPE_ACCOUNT_OPEN, limit=20)
    ]
    return {
        "settings": {
            "enabled": bool(settings.get("enabled")),
            "target_chat_id": settings.get("target_chat_id"),
            "expire_hours": int(settings.get("expire_hours") or 24),
            "strict_target": bool(settings.get("strict_target", True)),
            "account_open_days": int(settings.get("account_open_days") or 30),
        },
        "permissions": {
            "has_viewing_access": bool(has_access),
            "can_create": bool(settings.get("enabled") and has_access),
        },
        "available_credits": group_count,
        "records": group_records,
        "group_join": {
            "available_credits": group_count,
            "records": group_records,
        },
        "account_open": {
            "available_credits": account_open_count,
            "records": account_open_records,
        },
    }


def _invite_link_value(invite_link_obj) -> str:
    for field in ("invite_link", "link"):
        value = getattr(invite_link_obj, field, None)
        if value:
            return str(value)
    return str(invite_link_obj or "").strip()


async def _create_targeted_invite_link(chat_id: int, invitee_tg: int, expire_hours: int) -> tuple[str, datetime, str]:
    expires_at = datetime.utcnow() + timedelta(hours=max(int(expire_hours or 24), 1))
    link_name = f"emby-invite-{invitee_tg}-{int(time())}"
    try:
        invite_link_obj = await bot.create_chat_invite_link(
            chat_id=int(chat_id),
            name=link_name,
            expire_date=expires_at,
            creates_join_request=True,
        )
    except TypeError as exc:
        raise RuntimeError("当前 Pyrogram 版本不支持定向入群申请链接，请升级 Pyrogram。") from exc
    invite_link = _invite_link_value(invite_link_obj)
    if not invite_link:
        raise RuntimeError("Telegram 未返回邀请链接")
    return invite_link, expires_at, link_name


async def _safe_revoke_invite_link(chat_id: int, invite_link: str) -> None:
    if not invite_link:
        return
    try:
        await bot.revoke_chat_invite_link(chat_id=int(chat_id), invite_link=invite_link)
    except Exception as exc:
        LOGGER.warning(f"miniapp revoke invite link failed chat={chat_id}: {exc}")


async def _send_invite_link_to_invitee(invitee_tg: int, inviter_name: str, invite_link: str, expire_hours: int) -> None:
    text = (
        f"你收到来自 {inviter_name} 的 Emby 群组邀请。\n\n"
        f"邀请链接：{invite_link}\n\n"
        f"该链接仅供当前 Telegram 账号使用，约 {expire_hours} 小时内有效，入群后会自动失效。"
    )
    await bot.send_message(chat_id=int(invitee_tg), text=text)


async def _send_account_open_notice(invitee_tg: int, inviter_name: str, days: int) -> None:
    text = (
        f"你收到来自 {inviter_name} 的 Emby 开号资格。\n\n"
        f"注册天数：{int(days)} 天\n\n"
        "请私聊机器人发送 /start，然后点击“注册”完成开通。"
    )
    await bot.send_message(chat_id=int(invitee_tg), text=text)


def is_admin_user_id(user_id: int) -> bool:
    normalized_admins = set()
    for item in admins:
        try:
            normalized_admins.add(int(item))
        except (TypeError, ValueError):
            continue

    try:
        return int(user_id) == int(owner) or int(user_id) in normalized_admins
    except (TypeError, ValueError):
        return False


def verify_init_data(init_data: str) -> dict:
    parsed = dict(parse_qsl(init_data, keep_blank_values=True))
    their_hash = parsed.pop("hash", None)

    if not their_hash:
        raise HTTPException(status_code=400, detail="缺少小程序签名参数")

    data_check_string = "\n".join(f"{key}={value}" for key, value in sorted(parsed.items()))
    secret_key = hmac.new(b"WebAppData", bot_token.encode("utf-8"), sha256).digest()
    our_hash = hmac.new(secret_key, data_check_string.encode("utf-8"), sha256).hexdigest()

    if not hmac.compare_digest(our_hash, their_hash):
        raise HTTPException(status_code=403, detail="小程序初始化数据校验失败")

    auth_date = int(parsed.get("auth_date", "0"))
    if auth_date and int(time()) - auth_date > api_config.webapp_auth_max_age:
        raise HTTPException(status_code=401, detail="小程序初始化数据已过期，请重新进入页面")

    user_data = parsed.get("user")
    if not user_data:
        raise HTTPException(status_code=400, detail="缺少小程序用户信息")

    parsed["user"] = json.loads(user_data)
    matched_block = find_bot_access_block(
        tg=parsed["user"].get("id"),
        username=parsed["user"].get("username"),
    )
    if matched_block is not None:
        raise HTTPException(status_code=403, detail="当前 Telegram 账号已被禁止使用 Bot")
    return parsed


@router.post("/bootstrap")
async def bootstrap(payload: MiniAppInitRequest):
    verified = await run_in_threadpool(verify_init_data, payload.init_data)
    telegram_user = verified["user"]
    account, plugins = await asyncio.gather(
        run_in_threadpool(sql_get_emby, telegram_user["id"]),
        run_in_threadpool(list_miniapp_plugins),
    )
    is_admin = is_admin_user_id(telegram_user["id"])
    plugins = [
        plugin
        for plugin in plugins
        if plugin.get("enabled") and plugin.get("loaded") and plugin.get("web_registered")
    ]
    bottom_nav = [
        {
            "id": "home",
            "label": "主页",
            "path": "/miniapp",
            "icon": "🏠",
        }
    ]

    for plugin in plugins:
        plugin_visible = bool(config.plugin_nav.get(plugin["id"], plugin.get("bottom_nav_default", False)))
        if plugin.get("miniapp_path") and plugin_visible:
            bottom_nav.append(
                {
                    "id": plugin["id"],
                    "label": plugin.get("miniapp_label") or plugin["name"],
                    "path": plugin["miniapp_path"],
                    "icon": plugin.get("miniapp_icon") or "✨",
                }
            )

    return {
        "code": 200,
        "data": {
            "telegram_user": telegram_user,
            "account": None if account is None else serialize_emby_user(account),
            "invite": _public_invite_bundle(int(telegram_user["id"]), account),
            "permissions": {
                "is_admin": is_admin,
                "admin_url": "/admin" if is_admin else None,
            },
            "meta": {
                "brand": ranks.logo,
                "currency": pivkeyu,
                "plugins": plugins,
                "bottom_nav": bottom_nav,
            },
        },
    }


@router.post("/invites/create")
async def create_user_invite(payload: MiniAppInviteCreateRequest):
    verified = await run_in_threadpool(verify_init_data, payload.init_data)
    telegram_user = verified["user"]
    user_id = int(telegram_user["id"])
    invitee_tg = int(payload.invitee_tg)
    account = await run_in_threadpool(sql_get_emby, user_id)
    settings = get_invite_settings()

    if not settings.get("enabled"):
        raise HTTPException(status_code=403, detail="邀请功能当前未开启")
    if not has_viewing_access(account):
        raise HTTPException(status_code=403, detail="只有拥有 Emby 观影资格的用户才能获取入群资格")
    if available_invite_credit_count(user_id, credit_type=INVITE_CREDIT_TYPE_GROUP) <= 0:
        raise HTTPException(status_code=400, detail="你当前没有可用的入群资格")
    target_chat_id = settings.get("target_chat_id")
    if not target_chat_id:
        raise HTTPException(status_code=400, detail="管理员尚未配置邀请目标群组")

    invite_link = ""
    record = None
    try:
        invite_link, expires_at, link_name = await _create_targeted_invite_link(
            int(target_chat_id),
            invitee_tg,
            int(settings.get("expire_hours") or 24),
        )
        record = create_invite_record(
            inviter_tg=user_id,
            invitee_tg=invitee_tg,
            target_chat_id=int(target_chat_id),
            invite_link=invite_link,
            link_name=link_name,
            expires_at=expires_at,
            created_by_tg=user_id,
            note=payload.note or "",
        )
        inviter_name = telegram_user.get("first_name") or telegram_user.get("username") or str(user_id)
        await _send_invite_link_to_invitee(
            invitee_tg,
            inviter_name,
            invite_link,
            int(settings.get("expire_hours") or 24),
        )
    except ValueError as exc:
        await _safe_revoke_invite_link(int(target_chat_id), invite_link)
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        await _safe_revoke_invite_link(int(target_chat_id), invite_link)
        if record:
            cancel_pending_invite_record(record["id"], reason="私聊发送邀请链接失败，已自动撤销")
        LOGGER.warning(f"create user invite failed inviter={user_id} invitee={invitee_tg}: {exc}")
        raise HTTPException(status_code=500, detail="邀请链接生成或发送失败，请确认被邀请人已私聊启动过机器人") from exc

    return {
        "code": 200,
        "data": {
            "record": _public_invite_record(record),
            "invite": _public_invite_bundle(user_id, account),
        },
    }


@router.post("/invites/account-open/create")
async def create_account_open_invite(payload: MiniAppInviteCreateRequest):
    verified = await run_in_threadpool(verify_init_data, payload.init_data)
    telegram_user = verified["user"]
    user_id = int(telegram_user["id"])
    invitee_tg = int(payload.invitee_tg)
    account = await run_in_threadpool(sql_get_emby, user_id)
    settings = get_invite_settings()

    if not settings.get("enabled"):
        raise HTTPException(status_code=403, detail="邀请功能当前未开启")
    if not has_viewing_access(account):
        raise HTTPException(status_code=403, detail="只有拥有 Emby 观影资格的用户才能获取开号资格")
    if available_invite_credit_count(user_id, credit_type=INVITE_CREDIT_TYPE_ACCOUNT_OPEN) <= 0:
        raise HTTPException(status_code=400, detail="你当前没有可用的开号资格")

    try:
        record = create_account_open_invite_record(
            inviter_tg=user_id,
            invitee_tg=invitee_tg,
            created_by_tg=user_id,
            note=payload.note or "",
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        LOGGER.warning(f"create account open invite failed inviter={user_id} invitee={invitee_tg}: {exc}")
        raise HTTPException(status_code=500, detail="开号资格发放失败，请稍后重试") from exc

    inviter_name = telegram_user.get("first_name") or telegram_user.get("username") or str(user_id)
    try:
        await _send_account_open_notice(invitee_tg, inviter_name, int(record.get("invite_days") or 0))
    except Exception as exc:
        LOGGER.warning(f"send account open notice failed inviter={user_id} invitee={invitee_tg}: {exc}")

    return {
        "code": 200,
        "data": {
            "record": _public_invite_record(record),
            "invite": _public_invite_bundle(user_id, account),
        },
    }

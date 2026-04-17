from __future__ import annotations

import hmac
import json
from hashlib import sha256
from time import time
from urllib.parse import parse_qsl

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from bot import admins, api as api_config, bot_token, config, owner, pivkeyu, ranks
from bot.plugins import list_plugins
from bot.sql_helper.sql_bot_access import find_bot_access_block
from bot.sql_helper.sql_emby import sql_get_emby
from bot.web.presenters import serialize_emby_user

router = APIRouter(prefix="/miniapp-api", tags=["小程序"])


class MiniAppInitRequest(BaseModel):
    init_data: str


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
    verified = verify_init_data(payload.init_data)
    telegram_user = verified["user"]
    account = sql_get_emby(telegram_user["id"])
    is_admin = is_admin_user_id(telegram_user["id"])
    plugins = [plugin for plugin in list_plugins() if plugin.get("enabled")]
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

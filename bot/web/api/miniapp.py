from __future__ import annotations

import hmac
import json
from hashlib import sha256
from time import time
from urllib.parse import parse_qsl

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from bot import api as api_config, bot_token, pivkeyu, ranks
from bot.plugins import list_plugins
from bot.sql_helper.sql_emby import sql_get_emby

router = APIRouter(prefix="/miniapp-api", tags=["Mini App"])


class MiniAppInitRequest(BaseModel):
    init_data: str


def verify_init_data(init_data: str) -> dict:
    parsed = dict(parse_qsl(init_data, keep_blank_values=True))
    their_hash = parsed.pop("hash", None)

    if not their_hash:
        raise HTTPException(status_code=400, detail="Missing Telegram hash")

    data_check_string = "\n".join(f"{key}={value}" for key, value in sorted(parsed.items()))
    secret_key = hmac.new(b"WebAppData", bot_token.encode("utf-8"), sha256).digest()
    our_hash = hmac.new(secret_key, data_check_string.encode("utf-8"), sha256).hexdigest()

    if not hmac.compare_digest(our_hash, their_hash):
        raise HTTPException(status_code=403, detail="Invalid Telegram init data")

    auth_date = int(parsed.get("auth_date", "0"))
    if auth_date and int(time()) - auth_date > api_config.webapp_auth_max_age:
        raise HTTPException(status_code=401, detail="Telegram init data expired")

    user_data = parsed.get("user")
    if not user_data:
        raise HTTPException(status_code=400, detail="Missing Telegram user payload")

    parsed["user"] = json.loads(user_data)
    return parsed


@router.post("/bootstrap")
async def bootstrap(payload: MiniAppInitRequest):
    verified = verify_init_data(payload.init_data)
    telegram_user = verified["user"]
    account = sql_get_emby(telegram_user["id"])

    return {
        "code": 200,
        "data": {
            "telegram_user": telegram_user,
            "account": None
            if account is None
            else {
                "tg": account.tg,
                "name": account.name,
                "embyid": account.embyid,
                "lv": account.lv,
                "iv": account.iv,
                "us": account.us,
                "ex": account.ex.isoformat() if account.ex else None,
            },
            "meta": {
                "brand": ranks.logo,
                "currency": pivkeyu,
                "plugins": list_plugins(),
            },
        },
    }

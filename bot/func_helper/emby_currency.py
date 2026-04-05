from __future__ import annotations

from math import floor

from bot.sql_helper.sql_emby import Emby, sql_get_emby, sql_update_emby
from bot.sql_helper.sql_xiuxian import get_profile, get_xiuxian_settings, upsert_profile


def get_emby_balance(tg: int) -> int:
    user = sql_get_emby(tg)
    return 0 if user is None else int(user.iv or 0)


def add_emby_balance(tg: int, amount: int) -> int:
    user = sql_get_emby(tg)
    if user is None:
        raise ValueError("用户不存在")

    new_balance = int(user.iv or 0) + int(amount)
    if new_balance < 0:
        raise ValueError("余额不足")

    if not sql_update_emby(Emby.tg == tg, iv=new_balance):
        raise RuntimeError("更新 Emby 货币失败")

    return new_balance


def subtract_emby_balance(tg: int, amount: int) -> int:
    return add_emby_balance(tg, -int(amount))


def get_exchange_settings() -> dict:
    settings = get_xiuxian_settings()
    return {
        "rate": max(int(settings.get("coin_exchange_rate", 100) or 100), 1),
        "fee_percent": max(int(settings.get("exchange_fee_percent", 1) or 0), 0),
        "min_coin_exchange": max(int(settings.get("min_coin_exchange", 1) or 1), 1),
    }


def preview_coin_to_stone(coin_amount: int) -> dict:
    settings = get_exchange_settings()
    gross_stone = coin_amount * settings["rate"]
    fee = gross_stone * settings["fee_percent"] / 100
    net_stone = floor(max(gross_stone - fee, 0))
    return {
        "direction": "coin_to_stone",
        "gross": gross_stone,
        "fee": fee,
        "net": net_stone,
        "settings": settings,
    }


def preview_stone_to_coin(stone_amount: int) -> dict:
    settings = get_exchange_settings()
    gross_coin = stone_amount / settings["rate"]
    fee = gross_coin * settings["fee_percent"] / 100
    net_coin = floor(max(gross_coin - fee, 0))
    return {
        "direction": "stone_to_coin",
        "gross": gross_coin,
        "fee": fee,
        "net": net_coin,
        "settings": settings,
    }


def convert_coin_to_stone(tg: int, coin_amount: int) -> dict:
    amount = max(int(coin_amount), 0)
    if amount <= 0:
        raise ValueError("兑换数量必须大于 0")

    preview = preview_coin_to_stone(amount)
    if preview["net"] <= 0:
        raise ValueError("当前比例下可兑换的灵石不足 1")

    subtract_emby_balance(tg, amount)
    profile = get_profile(tg, create=True)
    updated = upsert_profile(tg, spiritual_stone=int(profile.spiritual_stone or 0) + int(preview["net"]))
    return {
        "spent_coin": amount,
        "received_stone": preview["net"],
        "emby_balance": get_emby_balance(tg),
        "stone_balance": updated.spiritual_stone,
        "fee": preview["fee"],
        "rate": preview["settings"]["rate"],
    }


def convert_stone_to_coin(tg: int, stone_amount: int) -> dict:
    amount = max(int(stone_amount), 0)
    if amount <= 0:
        raise ValueError("兑换数量必须大于 0")

    profile = get_profile(tg, create=False)
    if profile is None or int(profile.spiritual_stone or 0) < amount:
        raise ValueError("灵石不足")

    preview = preview_stone_to_coin(amount)
    if amount < preview["settings"]["rate"]:
        raise ValueError(f"最低需要 {preview['settings']['rate']} 灵石才能兑换 1 片刻碎片")
    if preview["net"] < preview["settings"]["min_coin_exchange"]:
        raise ValueError(f"最低需要兑换到 {preview['settings']['min_coin_exchange']} 片刻碎片")

    upsert_profile(tg, spiritual_stone=int(profile.spiritual_stone or 0) - amount)
    new_coin_balance = add_emby_balance(tg, int(preview["net"]))
    updated_profile = get_profile(tg, create=False)
    return {
        "spent_stone": amount,
        "received_coin": preview["net"],
        "emby_balance": new_coin_balance,
        "stone_balance": 0 if updated_profile is None else updated_profile.spiritual_stone,
        "fee": preview["fee"],
        "rate": preview["settings"]["rate"],
    }

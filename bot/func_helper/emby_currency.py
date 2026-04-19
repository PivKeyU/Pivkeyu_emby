from __future__ import annotations

from math import floor

from bot.sql_helper import Session
from bot.sql_helper.sql_emby import Emby, sql_get_emby
from bot.sql_helper.sql_xiuxian import (
    XiuxianProfile,
    apply_spiritual_stone_delta,
    assert_currency_operation_allowed,
    get_xiuxian_settings,
)


def get_emby_balance(tg: int) -> int:
    user = sql_get_emby(tg)
    return 0 if user is None else int(user.iv or 0)


def add_emby_balance(tg: int, amount: int) -> int:
    delta = int(amount)
    with Session() as session:
        user = session.query(Emby).filter(Emby.tg == tg).with_for_update().first()
        if user is None:
            raise ValueError("Emby 账号不存在")
        new_balance = int(user.iv or 0) + delta
        if new_balance < 0:
            raise ValueError("片刻碎片不足")
        user.iv = new_balance
        session.commit()
        return new_balance


def subtract_emby_balance(tg: int, amount: int) -> int:
    return add_emby_balance(tg, -int(amount))


def get_exchange_settings() -> dict:
    settings = get_xiuxian_settings()
    return {
        "enabled": bool(settings.get("coin_stone_exchange_enabled", True)),
        "rate": max(int(settings.get("coin_exchange_rate", 100) or 100), 1),
        "fee_percent": max(int(settings.get("exchange_fee_percent", 1) or 0), 0),
        "min_coin_exchange": max(int(settings.get("min_coin_exchange", 1) or 1), 1),
    }


def _fee_amount(gross_amount: int, fee_percent: int) -> int:
    return floor(max(int(gross_amount or 0), 0) * max(int(fee_percent or 0), 0) / 100)


def preview_coin_to_stone(coin_amount: int) -> dict:
    settings = get_exchange_settings()
    gross_stone = max(int(coin_amount or 0), 0) * settings["rate"]
    fee = _fee_amount(gross_stone, settings["fee_percent"])
    net_stone = max(gross_stone - fee, 0)
    return {
        "direction": "coin_to_stone",
        "gross": gross_stone,
        "fee": fee,
        "net": net_stone,
        "settings": settings,
    }


def preview_stone_to_coin(stone_amount: int) -> dict:
    settings = get_exchange_settings()
    gross_coin = floor(max(int(stone_amount or 0), 0) / settings["rate"])
    spent_stone = gross_coin * settings["rate"]
    fee = _fee_amount(gross_coin, settings["fee_percent"])
    net_coin = max(gross_coin - fee, 0)
    return {
        "direction": "stone_to_coin",
        "gross": gross_coin,
        "spent_stone": spent_stone,
        "fee": fee,
        "net": net_coin,
        "settings": settings,
    }


def convert_coin_to_stone(tg: int, coin_amount: int) -> dict:
    amount = max(int(coin_amount), 0)
    if amount <= 0:
        raise ValueError("兑换数量必须大于 0")

    preview = preview_coin_to_stone(amount)
    if not preview["settings"].get("enabled", True):
        raise ValueError("灵石互兑功能当前未开启。")
    if preview["gross"] <= 0 or preview["net"] <= 0:
        raise ValueError("当前比例和手续费下可兑换的灵石不足 1")

    with Session() as session:
        profile = session.query(XiuxianProfile).filter(XiuxianProfile.tg == tg).with_for_update().first()
        if profile is None or not profile.consented:
            raise ValueError("你还没有踏入仙途")
        assert_currency_operation_allowed(tg, "兑换灵石", session=session, profile=profile)
        user = session.query(Emby).filter(Emby.tg == tg).with_for_update().first()
        if user is None:
            raise ValueError("Emby 账号不存在")
        if int(user.iv or 0) < amount:
            raise ValueError("片刻碎片不足")

        user.iv = int(user.iv or 0) - amount
        apply_spiritual_stone_delta(
            session,
            tg,
            int(preview["net"]),
            action_text="兑换灵石",
            enforce_currency_lock=False,
            allow_dead=False,
            apply_tribute=False,
        )
        session.commit()
        new_coin_balance = int(user.iv or 0)
        stone_balance = int(profile.spiritual_stone or 0)
    return {
        "spent_coin": amount,
        "received_stone": preview["net"],
        "gross_stone": preview["gross"],
        "emby_balance": new_coin_balance,
        "stone_balance": stone_balance,
        "fee": preview["fee"],
        "rate": preview["settings"]["rate"],
    }


def convert_stone_to_coin(tg: int, stone_amount: int) -> dict:
    amount = max(int(stone_amount), 0)
    if amount <= 0:
        raise ValueError("兑换数量必须大于 0")

    preview = preview_stone_to_coin(amount)
    if not preview["settings"].get("enabled", True):
        raise ValueError("灵石互兑功能当前未开启。")
    minimum_stone = max(preview["settings"]["rate"], preview["settings"]["min_coin_exchange"])
    if preview["spent_stone"] < minimum_stone:
        raise ValueError(f"最低需要 {minimum_stone} 灵石才能兑换片刻碎片")
    if preview["gross"] <= 0 or preview["net"] <= 0:
        raise ValueError("当前比例和手续费下可兑换的片刻碎片不足 1")

    with Session() as session:
        profile = session.query(XiuxianProfile).filter(XiuxianProfile.tg == tg).with_for_update().first()
        if profile is None or not profile.consented:
            raise ValueError("你还没有踏入仙途")
        assert_currency_operation_allowed(tg, "兑换片刻碎片", session=session, profile=profile)
        if int(profile.spiritual_stone or 0) < int(preview["spent_stone"]):
            raise ValueError("灵石不足")
        user = session.query(Emby).filter(Emby.tg == tg).with_for_update().first()
        if user is None:
            raise ValueError("Emby 账号不存在")

        apply_spiritual_stone_delta(
            session,
            tg,
            -int(preview["spent_stone"]),
            action_text="兑换片刻碎片",
            enforce_currency_lock=False,
            allow_dead=False,
            apply_tribute=False,
        )
        user.iv = int(user.iv or 0) + int(preview["net"])
        session.commit()
        new_coin_balance = int(user.iv or 0)
        stone_balance = int(profile.spiritual_stone or 0)
    return {
        "spent_stone": preview["spent_stone"],
        "received_coin": preview["net"],
        "gross_coin": preview["gross"],
        "emby_balance": new_coin_balance,
        "stone_balance": stone_balance,
        "fee": preview["fee"],
        "rate": preview["settings"]["rate"],
    }

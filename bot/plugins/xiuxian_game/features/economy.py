from __future__ import annotations

from typing import Any

from bot.sql_helper import Session
from bot.sql_helper.sql_xiuxian import (
    XiuxianProfile,
    apply_spiritual_stone_delta,
    assert_currency_operation_allowed,
    assert_profile_alive,
    create_journal,
    get_profile,
    serialize_profile,
)
from bot.plugins.xiuxian_game.achievement_service import record_gift_metrics
from bot.plugins.xiuxian_game.features.retreat import ensure_not_in_retreat


def gift_spirit_stone(sender_tg: int, target_tg: int, amount: int) -> dict[str, Any]:
    if int(sender_tg) == int(target_tg):
        raise ValueError("不能给自己赠送灵石")
    amount = max(int(amount or 0), 0)
    if amount <= 0:
        raise ValueError("赠送灵石数量必须大于 0")

    ensure_not_in_retreat(sender_tg)

    with Session() as session:
        sender = session.query(XiuxianProfile).filter(XiuxianProfile.tg == sender_tg).with_for_update().first()
        receiver = session.query(XiuxianProfile).filter(XiuxianProfile.tg == target_tg).with_for_update().first()
        if sender is None or receiver is None or not sender.consented or not receiver.consented:
            raise ValueError("双方都需要已踏入仙途")
        assert_profile_alive(sender, "赠送灵石")
        assert_profile_alive(receiver, "接收灵石")
        assert_currency_operation_allowed(sender_tg, "赠送灵石", session=session, profile=sender)
        assert_currency_operation_allowed(target_tg, "接收灵石", session=session, profile=receiver)
        apply_spiritual_stone_delta(
            session,
            sender_tg,
            -amount,
            action_text="赠送灵石",
            allow_dead=False,
            apply_tribute=False,
        )
        apply_spiritual_stone_delta(
            session,
            target_tg,
            amount,
            action_text="接收灵石",
            allow_dead=False,
            apply_tribute=True,
        )
        session.commit()

    create_journal(sender_tg, "gift", "赠送灵石", f"向 TG {target_tg} 赠送了 {amount} 灵石")
    create_journal(target_tg, "gift", "收到灵石", f"收到 TG {sender_tg} 赠送的 {amount} 灵石")
    return {
        "amount": amount,
        "sender": serialize_profile(get_profile(sender_tg, create=False)),
        "receiver": serialize_profile(get_profile(target_tg, create=False)),
        "achievement_unlocks": record_gift_metrics(sender_tg, amount),
    }

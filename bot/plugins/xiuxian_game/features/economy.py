from __future__ import annotations

from typing import Any

from bot.sql_helper import Session
from bot.sql_helper.sql_xiuxian import (
    XiuxianArtifactInventory,
    XiuxianEquippedArtifact,
    XiuxianMaterialInventory,
    XiuxianPillInventory,
    XiuxianProfile,
    XiuxianTalismanInventory,
    apply_spiritual_stone_delta,
    assert_currency_operation_allowed,
    assert_profile_alive,
    create_journal,
    get_artifact,
    get_material,
    get_pill,
    get_profile,
    get_talisman,
    serialize_artifact,
    serialize_material,
    serialize_pill,
    serialize_profile,
    serialize_talisman,
    utcnow,
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


def _inventory_item_payload(item_kind: str, item_ref_id: int) -> dict[str, Any] | None:
    if item_kind == "artifact":
        return {"artifact": serialize_artifact(get_artifact(item_ref_id))}
    if item_kind == "pill":
        return {"pill": serialize_pill(get_pill(item_ref_id))}
    if item_kind == "talisman":
        return {"talisman": serialize_talisman(get_talisman(item_ref_id))}
    if item_kind == "material":
        return {"material": serialize_material(get_material(item_ref_id))}
    return None


def gift_inventory_item(
    sender_tg: int,
    target_tg: int,
    item_kind: str,
    item_ref_id: int,
    quantity: int = 1,
) -> dict[str, Any]:
    if int(sender_tg) == int(target_tg):
        raise ValueError("不能给自己赠送物品")
    item_kind = str(item_kind or "").strip()
    item_ref_id = int(item_ref_id or 0)
    quantity = max(int(quantity or 0), 0)
    if item_kind not in {"artifact", "pill", "talisman", "material"}:
        raise ValueError("当前只支持赠送法宝、符箓、丹药和材料")
    if item_ref_id <= 0 or quantity <= 0:
        raise ValueError("赠送物品参数不正确")

    ensure_not_in_retreat(sender_tg)

    with Session() as session:
        sender = session.query(XiuxianProfile).filter(XiuxianProfile.tg == sender_tg).with_for_update().first()
        receiver = session.query(XiuxianProfile).filter(XiuxianProfile.tg == target_tg).with_for_update().first()
        if sender is None or receiver is None or not sender.consented or not receiver.consented:
            raise ValueError("双方都需要已踏入仙途")
        assert_profile_alive(sender, "赠送物品")
        assert_profile_alive(receiver, "接收物品")
        assert_currency_operation_allowed(sender_tg, "赠送物品", session=session, profile=sender)
        assert_currency_operation_allowed(target_tg, "接收物品", session=session, profile=receiver)

        receiver_row = None
        sender_remaining = 0
        receiver_quantity = 0
        if item_kind == "artifact":
            sender_row = (
                session.query(XiuxianArtifactInventory)
                .filter(XiuxianArtifactInventory.tg == sender_tg, XiuxianArtifactInventory.artifact_id == item_ref_id)
                .with_for_update()
                .first()
            )
            if sender_row is None:
                raise ValueError("你的背包里没有这件法宝")
            bound_quantity = max(min(int(sender_row.bound_quantity or 0), int(sender_row.quantity or 0)), 0)
            equipped_count = int(
                session.query(XiuxianEquippedArtifact)
                .filter(XiuxianEquippedArtifact.tg == sender_tg, XiuxianEquippedArtifact.artifact_id == item_ref_id)
                .count()
                or 0
            )
            available_quantity = int(sender_row.quantity or 0) - bound_quantity - equipped_count
            if available_quantity < quantity:
                raise ValueError("可赠送的法宝数量不足，已绑定或已装备的法宝不能赠送")
            sender_row.quantity = max(int(sender_row.quantity or 0) - quantity, 0)
            sender_row.bound_quantity = max(min(bound_quantity, int(sender_row.quantity or 0)), 0)
            sender_row.updated_at = utcnow()
            sender_remaining = int(sender_row.quantity or 0)
            if sender_row.quantity <= 0:
                session.delete(sender_row)
            receiver_row = (
                session.query(XiuxianArtifactInventory)
                .filter(XiuxianArtifactInventory.tg == target_tg, XiuxianArtifactInventory.artifact_id == item_ref_id)
                .with_for_update()
                .first()
            )
            if receiver_row is None:
                receiver_row = XiuxianArtifactInventory(tg=target_tg, artifact_id=item_ref_id, quantity=0, bound_quantity=0)
                session.add(receiver_row)
            receiver_row.quantity = int(receiver_row.quantity or 0) + quantity
            receiver_row.bound_quantity = max(min(int(receiver_row.bound_quantity or 0), int(receiver_row.quantity or 0)), 0)
            receiver_row.updated_at = utcnow()
            receiver_quantity = int(receiver_row.quantity or 0)
        elif item_kind == "talisman":
            sender_row = (
                session.query(XiuxianTalismanInventory)
                .filter(XiuxianTalismanInventory.tg == sender_tg, XiuxianTalismanInventory.talisman_id == item_ref_id)
                .with_for_update()
                .first()
            )
            if sender_row is None:
                raise ValueError("你的背包里没有这张符箓")
            bound_quantity = max(min(int(sender_row.bound_quantity or 0), int(sender_row.quantity or 0)), 0)
            available_quantity = int(sender_row.quantity or 0) - bound_quantity
            if available_quantity < quantity:
                raise ValueError("可赠送的符箓数量不足，已绑定的符箓不能赠送")
            sender_row.quantity = max(int(sender_row.quantity or 0) - quantity, 0)
            sender_row.bound_quantity = max(min(bound_quantity, int(sender_row.quantity or 0)), 0)
            sender_row.updated_at = utcnow()
            sender_remaining = int(sender_row.quantity or 0)
            if sender_row.quantity <= 0:
                session.delete(sender_row)
            receiver_row = (
                session.query(XiuxianTalismanInventory)
                .filter(XiuxianTalismanInventory.tg == target_tg, XiuxianTalismanInventory.talisman_id == item_ref_id)
                .with_for_update()
                .first()
            )
            if receiver_row is None:
                receiver_row = XiuxianTalismanInventory(tg=target_tg, talisman_id=item_ref_id, quantity=0, bound_quantity=0)
                session.add(receiver_row)
            receiver_row.quantity = int(receiver_row.quantity or 0) + quantity
            receiver_row.bound_quantity = max(min(int(receiver_row.bound_quantity or 0), int(receiver_row.quantity or 0)), 0)
            receiver_row.updated_at = utcnow()
            receiver_quantity = int(receiver_row.quantity or 0)
        elif item_kind == "pill":
            sender_row = (
                session.query(XiuxianPillInventory)
                .filter(XiuxianPillInventory.tg == sender_tg, XiuxianPillInventory.pill_id == item_ref_id)
                .with_for_update()
                .first()
            )
            if sender_row is None or int(sender_row.quantity or 0) < quantity:
                raise ValueError("可赠送的丹药数量不足")
            sender_row.quantity = max(int(sender_row.quantity or 0) - quantity, 0)
            sender_row.updated_at = utcnow()
            sender_remaining = int(sender_row.quantity or 0)
            if sender_row.quantity <= 0:
                session.delete(sender_row)
            receiver_row = (
                session.query(XiuxianPillInventory)
                .filter(XiuxianPillInventory.tg == target_tg, XiuxianPillInventory.pill_id == item_ref_id)
                .with_for_update()
                .first()
            )
            if receiver_row is None:
                receiver_row = XiuxianPillInventory(tg=target_tg, pill_id=item_ref_id, quantity=0)
                session.add(receiver_row)
            receiver_row.quantity = int(receiver_row.quantity or 0) + quantity
            receiver_row.updated_at = utcnow()
            receiver_quantity = int(receiver_row.quantity or 0)
        else:
            sender_row = (
                session.query(XiuxianMaterialInventory)
                .filter(XiuxianMaterialInventory.tg == sender_tg, XiuxianMaterialInventory.material_id == item_ref_id)
                .with_for_update()
                .first()
            )
            if sender_row is None or int(sender_row.quantity or 0) < quantity:
                raise ValueError("可赠送的材料数量不足")
            sender_row.quantity = max(int(sender_row.quantity or 0) - quantity, 0)
            sender_row.updated_at = utcnow()
            sender_remaining = int(sender_row.quantity or 0)
            if sender_row.quantity <= 0:
                session.delete(sender_row)
            receiver_row = (
                session.query(XiuxianMaterialInventory)
                .filter(XiuxianMaterialInventory.tg == target_tg, XiuxianMaterialInventory.material_id == item_ref_id)
                .with_for_update()
                .first()
            )
            if receiver_row is None:
                receiver_row = XiuxianMaterialInventory(tg=target_tg, material_id=item_ref_id, quantity=0)
                session.add(receiver_row)
            receiver_row.quantity = int(receiver_row.quantity or 0) + quantity
            receiver_row.updated_at = utcnow()
            receiver_quantity = int(receiver_row.quantity or 0)

        sender.updated_at = utcnow()
        receiver.updated_at = utcnow()
        session.commit()

    item_payload = _inventory_item_payload(item_kind, item_ref_id)
    item_name = (
        item_payload.get("artifact", {}).get("name")
        or item_payload.get("pill", {}).get("name")
        or item_payload.get("talisman", {}).get("name")
        or item_payload.get("material", {}).get("name")
        or f"{item_kind}#{item_ref_id}"
    )
    create_journal(sender_tg, "gift_item", "赠送物品", f"向 TG {target_tg} 赠送了 {quantity} 个【{item_name}】")
    create_journal(target_tg, "gift_item", "收到物品", f"收到 TG {sender_tg} 赠送的 {quantity} 个【{item_name}】")
    return {
        "item_kind": item_kind,
        "item_ref_id": item_ref_id,
        "quantity": quantity,
        "item": item_payload,
        "sender_remaining": sender_remaining,
        "receiver_quantity": receiver_quantity,
        "sender": serialize_profile(get_profile(sender_tg, create=False)),
        "receiver": serialize_profile(get_profile(target_tg, create=False)),
    }

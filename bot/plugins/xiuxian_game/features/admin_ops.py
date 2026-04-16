from __future__ import annotations

from typing import Any


def _legacy_service():
    from bot.plugins.xiuxian_game import service as legacy_service

    return legacy_service


def update_xiuxian_settings(payload: dict[str, Any]) -> dict[str, Any]:
    return _legacy_service().update_xiuxian_settings(payload)


def admin_patch_player(tg: int, **fields) -> dict[str, Any] | None:
    return _legacy_service().admin_patch_player(tg, **fields)


def build_admin_player_detail(tg: int) -> dict[str, Any] | None:
    return _legacy_service().build_admin_player_detail(tg)


def admin_grant_player_resource(
    tg: int,
    item_kind: str,
    item_ref_id: int,
    quantity: int,
    *,
    equip: bool = False,
) -> dict[str, Any]:
    return _legacy_service().admin_grant_player_resource(
        tg,
        item_kind,
        item_ref_id,
        quantity,
        equip=equip,
    )


def admin_set_player_inventory(
    tg: int,
    item_kind: str,
    item_ref_id: int,
    quantity: int,
    *,
    bound_quantity: int | None = None,
) -> dict[str, Any]:
    return _legacy_service().admin_set_player_inventory(
        tg,
        item_kind,
        item_ref_id,
        quantity,
        bound_quantity=bound_quantity,
    )


def admin_revoke_player_resource(tg: int, item_kind: str, item_ref_id: int) -> dict[str, Any]:
    return _legacy_service().admin_revoke_player_resource(tg, item_kind, item_ref_id)


def admin_set_player_selection(tg: int, selection_kind: str, item_ref_id: int | None = None) -> dict[str, Any]:
    return _legacy_service().admin_set_player_selection(tg, selection_kind, item_ref_id=item_ref_id)


def admin_seed_demo_assets(tg: int) -> dict[str, Any]:
    return _legacy_service().admin_seed_demo_assets(tg)


def admin_migrate_all_profile_realms(preview_limit: int = 20) -> dict[str, Any]:
    return _legacy_service().admin_migrate_all_profile_realms(preview_limit=preview_limit)


def admin_clear_all_xiuxian_data() -> dict[str, Any]:
    return _legacy_service().admin_clear_all_xiuxian_data()

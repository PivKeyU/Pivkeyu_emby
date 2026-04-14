from __future__ import annotations


def _legacy_service():
    from bot.plugins.xiuxian_game import service as legacy_service

    return legacy_service


def equip_artifact_for_user(tg: int, artifact_id: int) -> dict:
    return _legacy_service().equip_artifact_for_user(tg, artifact_id)


def bind_artifact_for_user(tg: int, artifact_id: int) -> dict:
    return _legacy_service().bind_artifact_for_user(tg, artifact_id)


def unbind_artifact_for_user(tg: int, artifact_id: int) -> dict:
    return _legacy_service().unbind_artifact_for_user(tg, artifact_id)


def activate_talisman_for_user(tg: int, talisman_id: int) -> dict:
    return _legacy_service().activate_talisman_for_user(tg, talisman_id)


def bind_talisman_for_user(tg: int, talisman_id: int) -> dict:
    return _legacy_service().bind_talisman_for_user(tg, talisman_id)


def unbind_talisman_for_user(tg: int, talisman_id: int) -> dict:
    return _legacy_service().unbind_talisman_for_user(tg, talisman_id)


def activate_technique_for_user(tg: int, technique_id: int) -> dict:
    return _legacy_service().activate_technique_for_user(tg, technique_id)


def set_current_title_for_user(tg: int, title_id: int | None) -> dict:
    return _legacy_service().set_current_title_for_user(tg, title_id)


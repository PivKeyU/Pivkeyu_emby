from __future__ import annotations

from typing import Any


def _legacy_world_service():
    from bot.plugins.xiuxian_game import world_service as legacy_world_service

    return legacy_world_service


def build_world_bundle(tg: int) -> dict[str, Any]:
    return _legacy_world_service().build_world_bundle(tg)

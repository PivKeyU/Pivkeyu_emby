from __future__ import annotations

from typing import Any

from bot.plugins.xiuxian_game.features.farm import build_farm_bundle
from bot.plugins.xiuxian_game.features.fishing import build_fishing_bundle


def _legacy_world_service():
    from bot.plugins.xiuxian_game import world_service as legacy_world_service

    return legacy_world_service


def build_world_bundle(tg: int) -> dict[str, Any]:
    bundle = _legacy_world_service().build_world_bundle(tg)
    bundle["farm"] = build_farm_bundle(tg)
    bundle["fishing"] = build_fishing_bundle(tg)
    return bundle

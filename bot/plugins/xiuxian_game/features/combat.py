from __future__ import annotations

from typing import Any


def _legacy_service():
    from bot.plugins.xiuxian_game import service as legacy_service

    return legacy_service


def build_leaderboard(kind: str, page: int = 1, page_size: int = 20) -> dict[str, Any]:
    return _legacy_service().build_leaderboard(kind, page=page, page_size=page_size)


def format_leaderboard_text(result: dict[str, Any]) -> str:
    return _legacy_service().format_leaderboard_text(result)


def compute_duel_odds(challenger_tg: int, defender_tg: int, **kwargs: Any) -> dict[str, Any]:
    return _legacy_service().compute_duel_odds(challenger_tg, defender_tg, **kwargs)


def assert_duel_stake_affordable(challenger_profile: dict[str, Any], defender_profile: dict[str, Any], stake: int) -> None:
    return _legacy_service().assert_duel_stake_affordable(challenger_profile, defender_profile, stake)


def resolve_duel(challenger_tg: int, defender_tg: int, stake: int = 0, **kwargs: Any) -> dict[str, Any]:
    return _legacy_service().resolve_duel(challenger_tg, defender_tg, stake=stake, **kwargs)


def format_duel_settlement_text(result: dict[str, Any], bet_settlement: dict[str, Any] | None = None, page: int = 1, page_size: int = 10) -> str:
    return _legacy_service().format_duel_settlement_text(result, bet_settlement=bet_settlement, page=page, page_size=page_size)


def generate_duel_preview_text(duel: dict[str, Any], stake: int = 0, **kwargs: Any) -> str:
    return _legacy_service().generate_duel_preview_text(duel, stake=stake, **kwargs)

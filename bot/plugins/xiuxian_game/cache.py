from __future__ import annotations

import os
from collections.abc import Callable
from typing import Any

from bot.func_helper import redis_cache


SETTINGS_TTL = max(int(os.getenv("PIVKEYU_REDIS_XIUXIAN_SETTINGS_TTL", "300") or 300), 1)
CATALOG_TTL = max(int(os.getenv("PIVKEYU_REDIS_XIUXIAN_CATALOG_TTL", "300") or 300), 1)
USER_VIEW_TTL = max(int(os.getenv("PIVKEYU_REDIS_XIUXIAN_USER_VIEW_TTL", "30") or 30), 1)


def _normalize_parts(parts: tuple[Any, ...]) -> tuple[str, ...]:
    return tuple(str(part).strip() for part in parts if part is not None and str(part).strip())


def _version_key(*parts: Any) -> str:
    return redis_cache.build_key("xiuxian", "version", *_normalize_parts(parts))


def _cache_key(*parts: Any) -> str:
    return redis_cache.build_key("xiuxian", "cache", *_normalize_parts(parts))


def _version_token(*parts: Any) -> str:
    if not redis_cache.redis_enabled():
        return "1"
    return str(max(redis_cache.get_int(_version_key(*parts), 1), 1))


def load_versioned_json(
    *,
    version_parts: tuple[Any, ...],
    cache_parts: tuple[Any, ...],
    ttl: int,
    loader: Callable[[], Any],
) -> Any:
    if not redis_cache.redis_enabled():
        return loader()

    token = _version_token(*version_parts)
    cache_key = _cache_key(*cache_parts, f"v{token}")
    cached, payload = redis_cache.get_json(cache_key)
    if cached:
        return payload

    payload = loader()
    redis_cache.set_json(cache_key, payload, ttl)
    return payload


def load_multi_versioned_json(
    *,
    version_part_groups: tuple[tuple[Any, ...], ...],
    cache_parts: tuple[Any, ...],
    ttl: int,
    loader: Callable[[], Any],
) -> Any:
    if not redis_cache.redis_enabled():
        return loader()

    resolved_cache_parts = list(cache_parts)
    for parts in version_part_groups:
        normalized = _normalize_parts(parts)
        if not normalized:
            continue
        resolved_cache_parts.extend(("ver", *normalized, f"v{_version_token(*normalized)}"))

    cache_key = _cache_key(*resolved_cache_parts)
    cached, payload = redis_cache.get_json(cache_key)
    if cached:
        return payload

    payload = loader()
    redis_cache.set_json(cache_key, payload, ttl)
    return payload


def bump_settings_version() -> int:
    return redis_cache.increment(_version_key("settings"))


def bump_catalog_versions(*names: str) -> int:
    bumped = 0
    seen: set[str] = set()
    for name in names:
        normalized = str(name or "").strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        redis_cache.increment(_version_key("catalog", normalized))
        bumped += 1
    return bumped


def bump_profile_versions(*tgs: int) -> int:
    bumped = 0
    seen: set[int] = set()
    for tg in tgs:
        value = int(tg or 0)
        if value <= 0 or value in seen:
            continue
        seen.add(value)
        redis_cache.increment(_version_key("profile", value))
        bumped += 1
    return bumped


def bump_user_view_versions(*tgs: int) -> int:
    bumped = 0
    seen: set[int] = set()
    for tg in tgs:
        value = int(tg or 0)
        if value <= 0 or value in seen:
            continue
        seen.add(value)
        redis_cache.increment(_version_key("user-view", value))
        bumped += 1
    return bumped

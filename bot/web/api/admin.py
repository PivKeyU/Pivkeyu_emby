from __future__ import annotations

import os
import shutil
import threading
import time
from datetime import datetime
from time import monotonic
from sys import argv, executable
from typing import Any

from fastapi import APIRouter, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy import func
from starlette.background import BackgroundTask

from bot import LOGGER, bot, config, save_config
from bot.func_helper.utils import cr_link_one, rn_link_one
from bot.plugins import PluginImportError, import_plugin_archive, list_plugins, sync_plugin_runtime_state
from bot.scheduler.auto_update import serialize_auto_update_state, update_auto_update_settings
from bot.sql_helper import Session
from bot.sql_helper.sql_bot_access import (
    BotAccessBlock,
    find_bot_access_block,
    find_existing_bot_access_block,
    invalidate_bot_access_cache,
    normalize_bot_access_username,
    serialize_bot_access_block,
)
from bot.sql_helper.sql_code import Code, CodeRedeem
from bot.sql_helper.sql_emby import Emby
from bot.web.migration_bundle import MigrationBundleError, create_migration_bundle, restore_migration_bundle
from bot.web.presenters import get_level_meta, serialize_emby_user

router = APIRouter()

_TELEGRAM_IDENTITY_CACHE_TTL = 300.0
_telegram_identity_cache: dict[int, tuple[float, dict[str, str]]] = {}


class AdminUserPatch(BaseModel):
    embyid: str | None = None
    name: str | None = None
    pwd: str | None = None
    pwd2: str | None = None
    lv: str | None = Field(default=None, pattern="^[abcd]$")
    cr: datetime | None = None
    ex: datetime | None = None
    us: int | None = None
    iv: int | None = None
    ch: datetime | None = None


class AdminPluginPatch(BaseModel):
    enabled: bool | None = None
    bottom_nav_visible: bool | None = None


class AdminAutoUpdatePatch(BaseModel):
    status: bool | None = None
    git_repo: str | None = None
    docker_image: str | None = None
    container_name: str | None = None
    compose_service: str | None = None
    check_interval_minutes: int | None = Field(default=None, ge=5, le=1440)


class AdminCodeCreatePayload(BaseModel):
    days: int = Field(..., gt=0, le=3650)
    count: int = Field(..., gt=0, le=500)
    method: str = Field(default="code")
    type: str = Field(default="F")
    usage_limit: int = Field(default=1, gt=0, le=100)
    suffix_mode: str = Field(default="random")
    suffix_text: str | None = None


class AdminCodeDeletePayload(BaseModel):
    codes: list[str] = Field(default_factory=list)


class AdminBotAccessBlockCreatePayload(BaseModel):
    tg: int | None = Field(default=None, ge=1)
    username: str | None = Field(default=None, max_length=255)
    note: str | None = Field(default=None, max_length=255)


def _telegram_identity_payload(user: Any) -> dict[str, str]:
    first_name = str(getattr(user, "first_name", "") or "").strip()
    last_name = str(getattr(user, "last_name", "") or "").strip()
    username = str(getattr(user, "username", "") or "").strip().lstrip("@")
    display_name = " ".join(part for part in [first_name, last_name] if part).strip()
    payload: dict[str, str] = {}
    if display_name:
        payload["display_name"] = display_name
    if username:
        payload["username"] = username
    return payload


def _telegram_display_label(tg: int, identity: dict[str, str] | None) -> str:
    identity = identity or {}
    if identity.get("display_name"):
        return identity["display_name"]
    if identity.get("username"):
        return f"@{identity['username']}"
    return f"TG {tg}"


def _serialize_admin_user(user: Emby, identity: dict[str, str] | None = None) -> dict[str, Any]:
    payload = serialize_emby_user(user)
    identity = identity or {}
    matched_block = find_bot_access_block(tg=int(user.tg), username=identity.get("username"))
    payload["tg_display_name"] = identity.get("display_name")
    payload["tg_username"] = identity.get("username")
    payload["tg_display_label"] = _telegram_display_label(int(user.tg), identity)
    payload["bot_access_blocked"] = matched_block is not None
    payload["bot_access_block"] = matched_block
    return payload


def _cached_telegram_identity(tg: int) -> dict[str, str] | None:
    cached = _telegram_identity_cache.get(int(tg))
    if not cached:
        return None
    cached_at, payload = cached
    if monotonic() - cached_at > _TELEGRAM_IDENTITY_CACHE_TTL:
        _telegram_identity_cache.pop(int(tg), None)
        return None
    return dict(payload)


def _store_telegram_identity(tg: int, identity: dict[str, str]) -> None:
    _telegram_identity_cache[int(tg)] = (monotonic(), dict(identity))


def _chunked(values: list[int], size: int) -> list[list[int]]:
    return [values[index:index + size] for index in range(0, len(values), size)]


async def _fetch_telegram_identity_map(tgs: list[int]) -> dict[int, dict[str, str]]:
    identities: dict[int, dict[str, str]] = {}
    missing: list[int] = []

    for tg in {int(value) for value in tgs if value is not None}:
        cached = _cached_telegram_identity(tg)
        if cached is None:
            missing.append(tg)
        else:
            identities[tg] = cached

    for chunk in _chunked(missing, 100):
        try:
            response = await bot.get_users(chunk if len(chunk) > 1 else chunk[0])
            users = response if isinstance(response, list) else [response]
            found: set[int] = set()
            for user in users:
                tg = int(user.id)
                identity = _telegram_identity_payload(user)
                _store_telegram_identity(tg, identity)
                identities[tg] = identity
                found.add(tg)
            for tg in chunk:
                if tg not in found:
                    _store_telegram_identity(tg, {})
                    identities[tg] = {}
        except Exception as exc:
            LOGGER.warning(f"admin telegram batch lookup failed: {exc}")
            for tg in chunk:
                try:
                    user = await bot.get_users(int(tg))
                    identity = _telegram_identity_payload(user)
                except Exception as inner_exc:
                    LOGGER.warning(f"admin telegram lookup failed for {tg}: {inner_exc}")
                    identity = {}
                _store_telegram_identity(tg, identity)
                identities[tg] = identity

    return identities


def _telegram_identity_matches(identity: dict[str, str] | None, keyword: str) -> bool:
    if not keyword:
        return False
    identity = identity or {}
    normalized = keyword.strip().lower()
    username = identity.get("username", "").lower()
    display_name = identity.get("display_name", "").lower()
    return (
        normalized in display_name
        or normalized in username
        or normalized.lstrip("@") in username
    )


def _resolve_admin_actor_id(request: Request) -> int | None:
    admin_user = getattr(request.state, "admin_user", None) or {}
    admin_id = admin_user.get("id")
    try:
        return int(admin_id) if admin_id is not None else None
    except (TypeError, ValueError):
        return None


def _restart_current_process() -> None:
    service_name = os.getenv("PIVKEYU_RESTART_SERVICE", "").strip()
    if service_name and os.path.exists("/bin/systemctl"):
        os.execl("/bin/systemctl", "systemctl", "restart", service_name)
    os.execl(executable, executable, *argv)


def _restart_after_delay(seconds: float = 1.0) -> None:
    time.sleep(max(float(seconds), 0.1))
    _restart_current_process()


def _schedule_restart_after_delay(seconds: float = 4.0) -> None:
    # 让导入响应先完整返回，避免移动端/WebView把正常导入误判成网络失败。
    worker = threading.Thread(target=_restart_after_delay, args=(seconds,), daemon=True)
    worker.start()


def _serialize_code_actor(
    tg: int | None,
    identity_map: dict[int, dict[str, str]],
    emby_map: dict[int, Emby],
) -> dict[str, Any] | None:
    if tg is None:
        return None

    tg = int(tg)
    identity = identity_map.get(tg) or {}
    emby_user = emby_map.get(tg)
    level_meta = get_level_meta(getattr(emby_user, "lv", None)) if emby_user is not None else None
    return {
        "tg": tg,
        "tg_display_name": identity.get("display_name"),
        "tg_username": identity.get("username"),
        "tg_display_label": _telegram_display_label(tg, identity),
        "emby_name": getattr(emby_user, "name", None),
        "embyid": getattr(emby_user, "embyid", None),
        "lv": getattr(emby_user, "lv", None),
        "lv_text": level_meta["text"] if level_meta else None,
        "lv_tone": level_meta["tone"] if level_meta else None,
        "iv": getattr(emby_user, "iv", None),
        "us": getattr(emby_user, "us", None),
        "ex": emby_user.ex.isoformat() if emby_user and emby_user.ex else None,
    }


def _code_kind(code_value: str) -> str:
    if "Renew_" in str(code_value or ""):
        return "renew"
    if "Register_" in str(code_value or ""):
        return "register"
    return "unknown"


def _code_kind_text(kind: str) -> str:
    return {
        "register": "注册码",
        "renew": "续期码",
    }.get(kind, "未知类型")


def _normalize_bot_access_payload(payload: AdminBotAccessBlockCreatePayload) -> dict[str, Any]:
    tg = int(payload.tg) if payload.tg is not None else None
    username = normalize_bot_access_username(payload.username)
    note = str(payload.note or "").strip() or None

    if tg is None and username is None:
        raise HTTPException(status_code=400, detail="TGID 和 TG 用户名至少需要填写一项")

    return {
        "tg": tg,
        "username": username,
        "note": note,
    }


def _serialize_code_record(
    row: Code,
    redeem_rows: list[CodeRedeem],
    identity_map: dict[int, dict[str, str]],
    emby_map: dict[int, Emby],
) -> dict[str, Any]:
    use_limit = max(int(row.use_limit or 1), 1)
    use_count = max(int(row.use_count or 0), 0)
    remaining = max(use_limit - use_count, 0)
    kind = _code_kind(row.code)

    redeemers = [
        {
            "code": redeem.code,
            "use_index": redeem.use_index,
            "redeemed_at": redeem.redeemed_at.isoformat() if redeem.redeemed_at else None,
            "actor": _serialize_code_actor(redeem.user_id, identity_map, emby_map),
        }
        for redeem in redeem_rows
    ]

    return {
        "code": row.code,
        "kind": kind,
        "kind_text": _code_kind_text(kind),
        "days": int(row.us or 0),
        "use_limit": use_limit,
        "use_count": use_count,
        "remaining_uses": remaining,
        "is_exhausted": remaining <= 0,
        "status": "unused" if use_count == 0 else "used",
        "status_text": "未使用" if use_count == 0 else "已使用",
        "usedtime": row.usedtime.isoformat() if row.usedtime else None,
        "latest_redeemer": _serialize_code_actor(row.used, identity_map, emby_map),
        "creator": _serialize_code_actor(row.tg, identity_map, emby_map),
        "redeemers": redeemers,
        "redeemer_count": len(redeemers),
    }


def _normalize_code_create_payload(payload: AdminCodeCreatePayload) -> dict[str, Any]:
    method = str(payload.method or "").strip().lower()
    code_type = str(payload.type or "").strip().upper()
    suffix_mode = str(payload.suffix_mode or "").strip().lower()
    suffix_text = payload.suffix_text.strip() if payload.suffix_text else None

    if method not in {"code", "link"}:
        raise HTTPException(status_code=400, detail="模式只能是 code 或 link")
    if code_type not in {"F", "T"}:
        raise HTTPException(status_code=400, detail="类型只能是 F 或 T")
    if suffix_mode not in {"random", "fixed"}:
        raise HTTPException(status_code=400, detail="后缀模式只能是 random 或 fixed")
    if suffix_mode == "fixed" and not suffix_text:
        raise HTTPException(status_code=400, detail="固定后缀模式必须提供后缀文本")

    return {
        "days": int(payload.days),
        "count": int(payload.count),
        "method": method,
        "type": code_type,
        "usage_limit": int(payload.usage_limit),
        "suffix_mode": suffix_mode,
        "suffix_text": suffix_text,
    }


def _parse_generated_items(raw_output: str, method: str) -> list[dict[str, str | None]]:
    items: list[dict[str, str | None]] = []
    for line in (raw_output or "").splitlines():
        value = line.strip()
        if not value:
            continue

        if method == "link":
            code = value.split("start=", 1)[1] if "start=" in value else value
            items.append({"code": code, "display": value, "link": value})
        else:
            code = value.strip("`")
            items.append({"code": code, "display": code, "link": None})
    return items


@router.get("/summary")
async def summary():
    with Session() as session:
        total_users = session.query(func.count(Emby.tg)).scalar() or 0
        active_accounts = (
            session.query(func.count(Emby.tg)).filter(Emby.embyid.isnot(None)).scalar() or 0
        )
        banned_users = session.query(func.count(Emby.tg)).filter(Emby.lv == "c").scalar() or 0
        total_currency = session.query(func.coalesce(func.sum(Emby.iv), 0)).scalar() or 0

    return {
        "code": 200,
        "data": {
            "total_users": total_users,
            "active_accounts": active_accounts,
            "banned_users": banned_users,
            "total_currency": int(total_currency),
            "auto_update": serialize_auto_update_state(),
        },
    }


@router.get("/system/auto-update")
async def get_auto_update():
    return {"code": 200, "data": serialize_auto_update_state()}


@router.patch("/system/auto-update")
async def patch_auto_update(payload: AdminAutoUpdatePatch):
    data = update_auto_update_settings(payload.model_dump(exclude_unset=True))
    return {"code": 200, "data": data}


@router.get("/system/migration/export")
async def export_migration_bundle():
    exported = create_migration_bundle()
    return FileResponse(
        exported["archive_path"],
        media_type="application/zip",
        filename=exported["filename"],
        background=BackgroundTask(shutil.rmtree, exported["temp_root"], ignore_errors=True),
    )


@router.post("/system/migration/import")
async def import_migration_bundle_api(
    file: UploadFile = File(...),
    restore_config_file: bool = Form(False),
    restart_after_import: bool = Form(True),
):
    try:
        await file.seek(0)
        imported = restore_migration_bundle(file.file, restore_config_file=restore_config_file)
    except MigrationBundleError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        LOGGER.exception("migration bundle import failed")
        raise HTTPException(status_code=500, detail="迁移压缩包导入失败，请检查日志。") from exc
    finally:
        await file.close()

    if restart_after_import:
        _schedule_restart_after_delay(4.0)

    return {
        "code": 200,
        "data": {
            **imported,
            "restart_scheduled": bool(restart_after_import),
            "source_filename": file.filename or "migration.zip",
        },
    }


@router.get("/users")
async def list_users(
    q: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
):
    keyword = (q or "").strip()

    with Session() as session:
        query = session.query(Emby).order_by(Emby.tg.desc())
        all_users = query.all()

    users = all_users
    total = len(users)

    if keyword:
        identity_map = await _fetch_telegram_identity_map([user.tg for user in all_users])
        tg_users = [user for user in all_users if _telegram_identity_matches(identity_map.get(int(user.tg)), keyword)]

        if tg_users:
            users = tg_users
            total = len(users)
        else:
            if keyword.isdigit():
                users = [user for user in all_users if int(user.tg) == int(keyword)]
                total = len(users)
            else:
                users = []
                total = 0

            if not users:
                db_users = [
                    user for user in all_users
                    if keyword.lower() in str(user.name or "").lower()
                    or keyword.lower() in str(user.embyid or "").lower()
                ]
                if db_users:
                    users = db_users
                    total = len(users)
            else:
                total = len(users)

    start = (page - 1) * page_size
    page_users = users[start:start + page_size]
    identity_map = await _fetch_telegram_identity_map([user.tg for user in page_users])

    return {
        "code": 200,
        "data": {
            "items": [_serialize_admin_user(user, identity_map.get(int(user.tg))) for user in page_users],
            "page": page,
            "page_size": page_size,
            "total": total,
        },
    }


@router.get("/users/{tg}")
async def get_user(tg: int):
    with Session() as session:
        user = session.query(Emby).filter(Emby.tg == tg).first()
        if user is None:
            raise HTTPException(status_code=404, detail="未找到对应用户")
    identity_map = await _fetch_telegram_identity_map([tg])
    return {"code": 200, "data": _serialize_admin_user(user, identity_map.get(int(tg)))}


@router.patch("/users/{tg}")
async def update_user(tg: int, payload: AdminUserPatch):
    changes = payload.model_dump(exclude_unset=True)
    if not changes:
        return {"code": 200, "data": {"updated": False, "reason": "no_changes"}}

    with Session() as session:
        user = session.query(Emby).filter(Emby.tg == tg).first()
        if user is None:
            raise HTTPException(status_code=404, detail="未找到对应用户")

        for key, value in changes.items():
            setattr(user, key, value)

        session.commit()
        session.refresh(user)
    identity_map = await _fetch_telegram_identity_map([tg])
    return {"code": 200, "data": _serialize_admin_user(user, identity_map.get(int(tg)))}


@router.get("/bot-access-blocks")
async def list_bot_access_blocks():
    with Session() as session:
        rows = (
            session.query(BotAccessBlock)
            .order_by(BotAccessBlock.created_at.desc(), BotAccessBlock.id.desc())
            .all()
        )

    return {
        "code": 200,
        "data": [serialize_bot_access_block(row) for row in rows],
    }


@router.post("/bot-access-blocks")
async def create_bot_access_block(payload: AdminBotAccessBlockCreatePayload):
    normalized = _normalize_bot_access_payload(payload)
    existing = find_existing_bot_access_block(tg=normalized["tg"], username=normalized["username"])
    if existing is not None:
        target = serialize_bot_access_block(existing).get("target_text") or f"规则 {existing.id}"
        raise HTTPException(status_code=409, detail=f"{target} 已存在于 Bot 黑名单中")

    with Session() as session:
        try:
            row = BotAccessBlock(
                tg=normalized["tg"],
                username=normalized["username"],
                note=normalized["note"],
            )
            session.add(row)
            session.commit()
            session.refresh(row)
        except Exception as exc:
            session.rollback()
            LOGGER.warning(f"create bot access block failed: {exc}")
            raise HTTPException(status_code=500, detail="创建 Bot 黑名单规则失败") from exc

    invalidate_bot_access_cache()
    return {"code": 200, "data": serialize_bot_access_block(row)}


@router.delete("/bot-access-blocks/{block_id}")
async def delete_bot_access_block(block_id: int):
    with Session() as session:
        row = session.query(BotAccessBlock).filter(BotAccessBlock.id == block_id).first()
        if row is None:
            raise HTTPException(status_code=404, detail="未找到对应黑名单规则")

        payload = serialize_bot_access_block(row)
        try:
            session.delete(row)
            session.commit()
        except Exception as exc:
            session.rollback()
            LOGGER.warning(f"delete bot access block failed: {exc}")
            raise HTTPException(status_code=500, detail="删除 Bot 黑名单规则失败") from exc

    invalidate_bot_access_cache()
    return {"code": 200, "data": {"deleted": True, "item": payload}}


@router.get("/codes")
async def list_codes(
    status: str = Query(default="all"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
):
    normalized_status = str(status or "all").strip().lower()
    if normalized_status not in {"all", "unused", "used"}:
        raise HTTPException(status_code=400, detail="status 只能是 all、unused 或 used")

    with Session() as session:
        all_total = session.query(func.count(Code.code)).scalar() or 0
        unused_total = (
            session.query(func.count(Code.code))
            .filter(func.coalesce(Code.use_count, 0) == 0)
            .scalar()
            or 0
        )
        used_total = (
            session.query(func.count(Code.code))
            .filter(func.coalesce(Code.use_count, 0) > 0)
            .scalar()
            or 0
        )
        exhausted_total = (
            session.query(func.count(Code.code))
            .filter(func.coalesce(Code.use_count, 0) >= func.coalesce(Code.use_limit, 1))
            .scalar()
            or 0
        )

        query = session.query(Code)
        if normalized_status == "unused":
            query = query.filter(func.coalesce(Code.use_count, 0) == 0)
        elif normalized_status == "used":
            query = query.filter(func.coalesce(Code.use_count, 0) > 0)

        total = query.count()
        total_pages = max(1, (total + page_size - 1) // page_size)
        page = max(1, min(page, total_pages))
        page_rows = (
            query.order_by(Code.usedtime.desc(), Code.code.asc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )

        codes = [row.code for row in page_rows]
        redeem_rows = []
        if codes:
            redeem_rows = (
                session.query(CodeRedeem)
                .filter(CodeRedeem.code.in_(codes))
                .order_by(CodeRedeem.redeemed_at.desc(), CodeRedeem.id.desc())
                .all()
            )

        tg_ids = {
            int(value)
            for value in [*(row.tg for row in page_rows), *(row.used for row in page_rows)]
            if value is not None
        }
        for redeem in redeem_rows:
            if redeem.user_id is not None:
                tg_ids.add(int(redeem.user_id))

        emby_rows = session.query(Emby).filter(Emby.tg.in_(tg_ids)).all() if tg_ids else []

    redeem_map: dict[str, list[CodeRedeem]] = {}
    for redeem in redeem_rows:
        redeem_map.setdefault(redeem.code, []).append(redeem)

    emby_map = {int(row.tg): row for row in emby_rows}
    identity_map = await _fetch_telegram_identity_map(list(tg_ids))
    items = [
        _serialize_code_record(row, redeem_map.get(row.code, []), identity_map, emby_map)
        for row in page_rows
    ]

    return {
        "code": 200,
        "data": {
            "items": items,
            "page": page,
            "page_size": page_size,
            "total": total,
            "summary": {
                "all": int(all_total),
                "unused": int(unused_total),
                "used": int(used_total),
                "exhausted": int(exhausted_total),
            },
        },
    }


@router.post("/codes")
async def create_codes(payload: AdminCodeCreatePayload, request: Request):
    normalized = _normalize_code_create_payload(payload)
    admin_id = _resolve_admin_actor_id(request)
    if admin_id is None:
        raise HTTPException(status_code=400, detail="无法识别当前管理员身份")

    generator = cr_link_one if normalized["type"] == "F" else rn_link_one
    generated_output = await generator(
        admin_id,
        str(normalized["days"]),
        normalized["count"],
        normalized["days"],
        normalized["method"],
        usage_limit=normalized["usage_limit"],
        suffix_mode=normalized["suffix_mode"],
        suffix_text=normalized["suffix_text"],
    )
    if generated_output is None:
        raise HTTPException(status_code=500, detail="数据库写入失败，请稍后重试")

    items = _parse_generated_items(generated_output, normalized["method"])
    return {
        "code": 200,
        "data": {
            "count": normalized["count"],
            "days": normalized["days"],
            "method": normalized["method"],
            "type": normalized["type"],
            "type_text": "注册码" if normalized["type"] == "F" else "续期码",
            "usage_limit": normalized["usage_limit"],
            "suffix_mode": normalized["suffix_mode"],
            "suffix_text": normalized["suffix_text"],
            "items": items,
            "output": generated_output,
        },
    }


@router.post("/codes/delete")
async def delete_codes(payload: AdminCodeDeletePayload):
    codes = [str(code).strip() for code in payload.codes if str(code).strip()]
    if not codes:
        raise HTTPException(status_code=400, detail="至少需要提供一个注册码")
    if len(codes) > 1000:
        raise HTTPException(status_code=400, detail="单次最多删除 1000 个注册码")

    unique_codes = list(dict.fromkeys(codes))
    with Session() as session:
        try:
            redeem_deleted = (
                session.query(CodeRedeem)
                .filter(CodeRedeem.code.in_(unique_codes))
                .delete(synchronize_session=False)
            )
            code_deleted = (
                session.query(Code)
                .filter(Code.code.in_(unique_codes))
                .delete(synchronize_session=False)
            )
            session.commit()
        except Exception as exc:
            session.rollback()
            LOGGER.warning(f"admin code batch delete failed: {exc}")
            raise HTTPException(status_code=500, detail="批量删除注册码失败") from exc

    return {
        "code": 200,
        "data": {
            "requested": len(unique_codes),
            "deleted": int(code_deleted),
            "redeem_deleted": int(redeem_deleted),
        },
    }


@router.get("/plugins")
async def plugins():
    items = []
    for plugin in list_plugins():
        visible = bool(config.plugin_nav.get(plugin["id"], plugin.get("bottom_nav_default", False)))
        items.append(
            {
                **plugin,
                "bottom_nav_visible": visible,
            }
        )
    return {"code": 200, "data": items}


@router.patch("/plugins/{plugin_id}")
async def patch_plugin(plugin_id: str, payload: AdminPluginPatch, request: Request):
    plugins = {plugin["id"]: plugin for plugin in list_plugins()}
    if plugin_id not in plugins:
        raise HTTPException(status_code=404, detail="未找到对应插件")
    if payload.enabled is None and payload.bottom_nav_visible is None:
        raise HTTPException(status_code=400, detail="至少需要提供 enabled 或 bottom_nav_visible 之一")

    plugin = plugins[plugin_id]
    if payload.enabled is not None:
        if payload.enabled == plugin.get("manifest_enabled", True):
            config.plugin_enabled.pop(plugin_id, None)
        else:
            config.plugin_enabled[plugin_id] = payload.enabled
        if payload.enabled is False and payload.bottom_nav_visible is None:
            config.plugin_nav[plugin_id] = False

    if payload.bottom_nav_visible is not None:
        config.plugin_nav[plugin_id] = payload.bottom_nav_visible

    save_config()
    runtime_plugin = sync_plugin_runtime_state(plugin_id, request.app)
    visible = bool(config.plugin_nav.get(plugin_id, runtime_plugin.get("bottom_nav_default", False)))
    return {
        "code": 200,
        "data": {
            **runtime_plugin,
            "bottom_nav_visible": visible,
        },
    }


@router.post("/plugins/import")
async def import_plugin(
    request: Request,
    file: UploadFile = File(...),
    enabled: bool = Form(True),
    replace_existing: bool = Form(False),
):
    try:
        imported = import_plugin_archive(
            await file.read(),
            file.filename or "plugin.zip",
            replace_existing=replace_existing,
        )
    except PluginImportError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    finally:
        await file.close()

    plugin_id = imported["plugin_id"]
    if enabled == imported.get("manifest_enabled", True):
        config.plugin_enabled.pop(plugin_id, None)
    else:
        config.plugin_enabled[plugin_id] = enabled
    if not enabled:
        config.plugin_nav[plugin_id] = False

    save_config()
    runtime_plugin = sync_plugin_runtime_state(plugin_id, request.app)
    visible = bool(config.plugin_nav.get(plugin_id, runtime_plugin.get("bottom_nav_default", False)))
    return {
        "code": 200,
        "data": {
            **runtime_plugin,
            "bottom_nav_visible": visible,
            "imported": True,
            "replaced": imported["replaced"],
            "backup_path": imported["backup_path"],
            "directory": imported["directory"],
            "source_filename": imported["source_filename"],
        },
    }

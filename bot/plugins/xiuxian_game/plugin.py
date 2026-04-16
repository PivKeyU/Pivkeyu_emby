from __future__ import annotations

import asyncio
import json
import re
import time
import traceback
from datetime import datetime, timedelta, timezone
from io import BytesIO
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlsplit
from uuid import uuid4

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pyrogram import enums, filters
from pyrogram.enums import ChatMemberStatus
from pyrogram.types import BotCommand, InlineKeyboardButton, InlineKeyboardMarkup

from bot import LOGGER, admin_p, api as api_config, bot, config, group, owner, owner_p, prefixes, user_p
from bot.func_helper.msg_utils import callAnswer
from bot.plugins import list_plugins
from bot.sql_helper import Session
from bot.plugins.xiuxian_game.api_models import (
    AchievementPayload,
    AchievementProgressPayload,
    ActivateTalismanPayload,
    ActivateTechniquePayload,
    AdminBootstrapPayload,
    AdminSettingPayload,
    AdminTaskPayload,
    ArtifactBindingPayload,
    ArtifactPayload,
    ArtifactSetPayload,
    BreakthroughPayload,
    ConsumePillPayload,
    CommissionClaimPayload,
    CraftPayload,
    EncounterDispatchPayload,
    EncounterPayload,
    EquipArtifactPayload,
    ErrorLogQueryPayload,
    ExchangePayload,
    ExploreClaimPayload,
    ExploreStartPayload,
    GiftPayload,
    GrantPayload,
    InitDataPayload,
    ItemGiftPayload,
    LeaderboardPayload,
    MaterialPayload,
    OfficialShopPatchPayload,
    OfficialShopPayload,
    PersonalAuctionPayload,
    PersonalShopPayload,
    PillPayload,
    PlayerLookupPayload,
    PlayerInventoryPayload,
    PlayerPatchPayload,
    PlayerResourceGrantPayload,
    PlayerRevokePayload,
    PlayerSelectionPayload,
    PurchasePayload,
    RecipePayload,
    RedEnvelopePayload,
    RetreatPayload,
    ScenePayload,
    SectJoinPayload,
    SectPayload,
    SectRoleAssignPayload,
    ShopCancelPayload,
    TalismanBindingPayload,
    TalismanPayload,
    TaskClaimPayload,
    TaskCancelPayload,
    TechniquePayload,
    TitleEquipPayload,
    TitleGrantPayload,
    TitleGroupSyncPayload,
    TitlePayload,
    UploadPermissionPayload,
    UserTaskPayload,
)
from bot.plugins.xiuxian_game.features.admin_ops import (
    admin_clear_all_xiuxian_data,
    admin_grant_player_resource,
    admin_migrate_all_profile_realms,
    admin_patch_player,
    admin_revoke_player_resource,
    admin_seed_demo_assets,
    admin_set_player_inventory,
    admin_set_player_selection,
    build_admin_player_detail,
    update_xiuxian_settings,
)
from bot.plugins.xiuxian_game.features.combat import (
    assert_duel_stake_affordable,
    build_leaderboard,
    compute_duel_odds,
    format_duel_settlement_text,
    format_leaderboard_text,
    generate_duel_preview_text,
    resolve_duel,
)
from bot.plugins.xiuxian_game.features.crafting import (
    build_recipe_catalog,
    craft_recipe_for_user,
    create_recipe_with_ingredients,
    patch_recipe_with_ingredients,
)
from bot.plugins.xiuxian_game.features.economy import gift_inventory_item, gift_spirit_stone
from bot.plugins.xiuxian_game.features.encounters import (
    claim_group_encounter,
    create_encounter_template,
    delete_encounter_template,
    list_encounter_templates,
    mark_group_encounter_message,
    maybe_spawn_group_encounter,
    patch_encounter_template,
    render_group_encounter_success_text,
    render_group_encounter_text,
    spawn_group_encounter,
)
from bot.plugins.xiuxian_game.features.exploration import (
    claim_exploration_for_user,
    create_scene_with_drops,
    patch_scene_with_drops,
    start_exploration_for_user,
)
from bot.plugins.xiuxian_game.features.growth import (
    claim_spirit_stone_commission,
    breakthrough_for_user,
    create_foundation_pill_for_user_if_missing,
    ensure_seed_data,
    format_root,
    init_path_for_user,
    maybe_gain_cultivation_from_chat,
    practice_for_user,
    serialize_full_profile,
)
from bot.plugins.xiuxian_game.features.inventory import (
    activate_talisman_for_user,
    activate_technique_for_user,
    bind_artifact_for_user,
    bind_talisman_for_user,
    equip_artifact_for_user,
    set_current_title_for_user,
    unbind_artifact_for_user,
    unbind_talisman_for_user,
)
from bot.plugins.xiuxian_game.features.pills import consume_pill_for_user
from bot.plugins.xiuxian_game.features.retreat import finish_retreat_for_user, start_retreat_for_user
from bot.plugins.xiuxian_game.features.sects import (
    claim_sect_salary_for_user,
    create_sect_with_roles,
    join_sect_for_user,
    leave_sect_for_user,
    set_user_sect_role,
)
from bot.plugins.xiuxian_game.features.shop import (
    broadcast_shop_copy,
    cancel_personal_auction_listing,
    create_personal_auction_listing,
    convert_emby_coin_to_stone,
    convert_stone_to_emby_coin,
    create_official_shop_listing,
    create_personal_shop_listing,
    finalize_auction_listing,
    generate_shop_name,
    grant_item_to_user,
    list_public_shop_items,
    patch_auction_listing,
    patch_shop_listing,
    place_auction_bid,
    purchase_shop_item,
    search_xiuxian_players,
)
from bot.plugins.xiuxian_game.features.social import (
    cancel_duel_bet_pool,
    claim_red_envelope_for_user,
    create_duel_bet_pool_for_duel,
    create_red_envelope_for_user,
    format_duel_bet_board,
    place_duel_bet,
    rob_player,
    settle_duel_bet_pool,
    update_duel_bet_pool_message,
)
from bot.plugins.xiuxian_game.features.tasks import (
    cancel_task_for_user,
    claim_task_for_user,
    create_bounty_task,
    mark_task_group_message,
    resolve_quiz_answer,
)
from bot.plugins.xiuxian_game.features.ui import (
    build_plugin_url,
    duel_keyboard,
    leaderboard_keyboard,
    xiuxian_confirm_keyboard,
    xiuxian_profile_keyboard,
)
from bot.plugins.xiuxian_game.features.world_bundle import build_world_bundle
from bot.ranks_helper.ranks_draw import RanksDraw
from bot.scheduler.bot_commands import BotCommands
from bot.sql_helper.sql_xiuxian import (
    DEFAULT_SETTINGS,
    cancel_personal_shop_item,
    create_achievement,
    create_artifact,
    create_artifact_set,
    create_error_log,
    create_journal,
    create_material,
    create_pill,
    create_talisman,
    create_title,
    delete_artifact,
    delete_artifact_set,
    delete_achievement,
    delete_material,
    delete_pill,
    delete_recipe,
    delete_scene,
    delete_sect,
    delete_technique,
    delete_title,
    delete_talisman,
    delete_task,
    create_technique,
    get_emby_account,
    get_xiuxian_settings,
    grant_image_upload_permission,
    has_image_upload_permission,
    list_artifacts,
    list_materials,
    list_achievements,
    list_artifact_sets,
    list_auction_items,
    list_error_logs,
    list_pill_type_options,
    list_image_upload_permissions,
    list_pills,
    list_titles,
    list_recent_journals,
    list_recipes,
    list_recipe_ingredients,
    list_scene_drops,
    list_scenes,
    list_shop_items,
    list_sect_roles,
    list_sects,
    list_talismans,
    list_tasks,
    list_techniques,
    grant_title_to_user,
    mark_user_achievement_notification,
    patch_achievement,
    patch_artifact,
    patch_artifact_set,
    patch_material,
    patch_pill,
    patch_sect,
    patch_talisman,
    patch_technique,
    patch_title,
    replace_sect_roles,
    revoke_image_upload_permission,
    serialize_profile,
)
from bot.plugins.xiuxian_game.achievement_service import (
    ACHIEVEMENT_METRIC_PRESETS,
    format_reward_summary,
    record_achievement_progress,
)
from bot.web.api.miniapp import is_admin_user_id, verify_init_data


PLAIN_TEXT_MODE = enums.ParseMode.DISABLED
RICH_TEXT_MODE = enums.ParseMode.MARKDOWN


PLUGIN_ROOT = Path(__file__).resolve().parent
STATIC_DIR = PLUGIN_ROOT / "static"
DATA_DIR = PLUGIN_ROOT.parent.parent.parent / "data"
UPLOAD_DIR = DATA_DIR / "xiuxian_uploads"
PLUGIN_MANIFEST = json.loads((PLUGIN_ROOT / "plugin.json").read_text(encoding="utf-8"))
PLUGIN_VERSION = str(PLUGIN_MANIFEST.get("version") or "0.1.0")
PLUGIN_NAME = str(PLUGIN_MANIFEST.get("name") or "修仙玩法")
MAX_UPLOAD_BYTES = 8 * 1024 * 1024
ALLOWED_IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
ALLOWED_IMAGE_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
MARKDOWN_ESCAPE_PATTERN = re.compile(r"([_*\[`])")
SHANGHAI_TZ = timezone(timedelta(hours=8))
DUEL_MESSAGE_REFRESH_CACHE: dict[int, float] = {}
DUEL_SETTLEMENT_CACHE: dict[int, dict[str, Any]] = {}
PENDING_DUEL_INVITES: dict[tuple[int, int], dict[str, Any]] = {}
MESSAGE_AUTO_DELETE_TASKS: dict[tuple[int, int], asyncio.Task] = {}
AUCTION_FINALIZE_TASKS: dict[int, asyncio.Task] = {}
COMMAND_DISPATCH_CACHE: dict[tuple[int, int, str], float] = {}
DUEL_SETTLEMENT_PAGE_SIZE = 10
STATIC_ASSET_PATTERN = re.compile(r'(/plugins/xiuxian/static/([A-Za-z0-9_.-]+\.(?:css|js)))')
XIUXIAN_BOT_COMMANDS = (
    BotCommand("xiuxian", f"修仙玩法 v{PLUGIN_VERSION} [私聊]"),
    BotCommand("xiuxian_me", "展示修仙名帖 [群聊]"),
    BotCommand("xiuxian_rank", "查看修仙排行榜 [群聊]"),
    BotCommand("train", "群内吐纳修炼 [群聊]"),
    BotCommand("work", "群内承接灵石委托 [群聊]"),
    BotCommand("salary", "群内领取宗门俸禄 [群聊]"),
    BotCommand("duel", "回复目标发起斗法 [群聊]"),
    BotCommand("deathduel", "回复目标发起生死斗 [群聊]"),
    BotCommand("servitudeduel", "回复目标发起奴役斗 [群聊]"),
    BotCommand("seek", "回复目标探查对方信息 [群聊]"),
    BotCommand("rob", "回复目标发起抢劫 [群聊]"),
    BotCommand("gift", "赠送灵石给其他玩家"),
)
GIFT_INLINE_AMOUNT_PATTERN = re.compile(r"^[\\/!\\.](?:gift)(?:@[A-Za-z0-9_]+)?(\d+)\s*$", re.IGNORECASE)
COMMISSION_COMMAND_ALIASES = {
    "work": "work",
    "打工": "work",
    "仙坊": "work",
    "仙坊打工": "work",
    "spirit_field": "spirit_field",
    "灵田": "spirit_field",
    "灵田照料": "spirit_field",
    "照料灵田": "spirit_field",
    "beast_hunt": "beast_hunt",
    "灵兽": "beast_hunt",
    "代捕灵兽": "beast_hunt",
    "caravan_guard": "caravan_guard",
    "商队": "caravan_guard",
    "护送": "caravan_guard",
    "护送商队": "caravan_guard",
    "formation_maintenance": "formation_maintenance",
    "阵法": "formation_maintenance",
    "检修护山阵": "formation_maintenance",
    "sword_repair": "sword_repair",
    "修剑": "sword_repair",
    "修补灵剑": "sword_repair",
    "rift_patrol": "rift_patrol",
    "裂隙": "rift_patrol",
    "前哨": "rift_patrol",
    "镇守裂隙前哨": "rift_patrol",
}
DUEL_COMMAND_MODES = {
    "duel": "standard",
    "deathduel": "death",
    "lifedeathduel": "death",
    "servitudeduel": "master",
    "masterduel": "master",
    "slaveduel": "master",
}


def _ensure_xiuxian_bot_commands() -> None:
    for command_list in (user_p, admin_p, owner_p):
        existing = {item.command for item in command_list}
        for command in XIUXIAN_BOT_COMMANDS:
            if command.command not in existing:
                command_list.append(command)
                existing.add(command.command)


def _schedule_command_refresh(bot_instance) -> None:
    try:
        loop = asyncio.get_event_loop()
        loop.call_later(5, lambda: loop.create_task(BotCommands.set_commands(client=bot_instance)))
    except Exception as exc:
        LOGGER.debug(f"xiuxian command refresh skipped: {exc}")


def _register_command_dispatch(message, command_name: str, *, ttl_seconds: int = 30) -> bool:
    chat_id = getattr(getattr(message, "chat", None), "id", None)
    message_id = getattr(message, "id", None)
    if chat_id is None or message_id is None:
        return True

    now = time.monotonic()
    expire_before = now - max(int(ttl_seconds), 1)
    stale_keys = [key for key, seen_at in COMMAND_DISPATCH_CACHE.items() if seen_at < expire_before]
    for key in stale_keys:
        COMMAND_DISPATCH_CACHE.pop(key, None)

    cache_key = (int(chat_id), int(message_id), str(command_name or "").strip().lower())
    if cache_key in COMMAND_DISPATCH_CACHE:
        return False

    COMMAND_DISPATCH_CACHE[cache_key] = now
    return True


def _xiuxian_basic_guide_text(consented: bool) -> str:
    lines = [
        f"《{PLUGIN_NAME}》当前版本：v{PLUGIN_VERSION}",
        "基础玩法：",
        "1. 私聊发送 /xiuxian 入道，抽取灵根并建立角色档案。",
        "2. 通过吐纳、闭关、丹药、功法与法宝持续提升修为和战力。",
        "3. 用探索、任务、宗门、坊市和红包获取资源，逐步扩展养成路线。",
        "4. 群内可使用 /duel、/rob、/gift 与其他道友互动。",
        "5. 完整的背包、炼制、宗门与商店功能请从修仙面板进入。",
    ]
    if not consented:
        lines.append("现在还未入道，点击下方按钮即可正式踏上仙途。")
    return "\n".join(lines)


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


async def _refresh_profile_identity_from_telegram(tg: int) -> dict[str, str] | None:
    try:
        telegram_user = await bot.get_users(int(tg))
    except Exception as exc:
        LOGGER.warning(f"xiuxian admin failed to refresh telegram profile {tg}: {exc}")
        return None

    payload = _telegram_identity_payload(telegram_user)
    if not payload:
        return None

    from bot.sql_helper.sql_xiuxian import upsert_profile

    upsert_profile(int(tg), **payload)
    return payload


def _merge_profile_identity(profile: dict[str, Any], identity: dict[str, str] | None) -> dict[str, Any]:
    if not identity:
        return profile

    merged = dict(profile)
    if identity.get("display_name"):
        merged["display_name"] = identity["display_name"]
    if identity.get("username"):
        merged["username"] = identity["username"]

    if merged.get("display_name"):
        merged["display_label"] = merged["display_name"]
    elif merged.get("username"):
        merged["display_label"] = f"@{merged['username']}"
    elif merged.get("tg"):
        merged["display_label"] = f"TG {merged['tg']}"
    return merged


async def _admin_player_bundle_payload(tg: int) -> dict[str, Any]:
    bundle = build_admin_player_detail(tg)
    if bundle is None:
        raise HTTPException(status_code=404, detail="Player not found")
    identity = await _refresh_profile_identity_from_telegram(tg)
    bundle["profile"] = _merge_profile_identity(bundle.get("profile") or {}, identity)
    bundle["emby_account"] = get_emby_account(tg)
    return bundle


def _verify_user_from_init_data(init_data: str) -> dict[str, Any]:
    verified = verify_init_data(init_data)
    user = verified["user"]
    display_name = " ".join(part for part in [user.get("first_name"), user.get("last_name")] if part).strip()
    upsert_fields = {}
    if display_name:
        upsert_fields["display_name"] = display_name
    if user.get("username"):
        upsert_fields["username"] = str(user["username"]).lstrip("@")
    if upsert_fields:
        from bot.sql_helper.sql_xiuxian import upsert_profile

        upsert_profile(int(user["id"]), **upsert_fields)
    return user


def _verify_admin_credential(token: str | None, init_data: str | None) -> dict[str, Any]:
    expected_token = api_config.admin_token or ""
    if token and token == expected_token:
        return {"id": owner, "auth": "token"}

    if init_data:
        telegram_user = _verify_user_from_init_data(init_data)
        if is_admin_user_id(telegram_user["id"]):
            telegram_user["auth"] = "telegram"
            return telegram_user
        raise HTTPException(status_code=403, detail="当前 Telegram 账号没有后台权限")

    raise HTTPException(status_code=401, detail="缺少后台登录凭证")


def _operation_name_from_request(request: Request) -> str:
    path = str(request.url.path or "").strip()
    if not path:
        return "未知操作"
    parts = [part for part in path.split("/") if part]
    if len(parts) >= 2 and parts[-1].isdigit():
        parts = parts[:-1]
    if not parts:
        return path
    if len(parts) >= 2:
        return "/".join(parts[-2:])
    return parts[-1]


def _extract_init_data_from_body_bytes(content_type: str, body: bytes) -> str | None:
    if not body:
        return None
    if "application/json" in content_type:
        try:
            payload = json.loads(body.decode("utf-8"))
        except Exception:
            return None
        return str(payload.get("init_data") or "").strip() or None
    if "application/x-www-form-urlencoded" in content_type:
        parsed = parse_qs(body.decode("utf-8", errors="ignore"), keep_blank_values=True)
        values = parsed.get("init_data")
        if values:
            return str(values[0] or "").strip() or None
    return None


def _actor_from_request(request: Request) -> dict[str, Any]:
    scope = "admin" if "/admin-api/" in str(request.url.path or "") else "user"
    init_data = getattr(request.state, "xiuxian_init_data", None)
    if not init_data:
        init_data = request.headers.get("x-telegram-init-data")
    if not init_data:
        return {"scope": scope}
    try:
        actor = verify_init_data(init_data)
    except Exception:
        return {"scope": scope}
    return {
        "scope": scope,
        "tg": int(actor.get("id") or 0) or None,
        "username": str(actor.get("username") or "").strip() or None,
        "display_name": str(actor.get("first_name") or actor.get("last_name") or "").strip() or None,
    }


def _record_request_error(request: Request, exc: Exception, *, status_code: int, level: str) -> None:
    try:
        actor = _actor_from_request(request)
        detail = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))[:12000]
        create_error_log(
            tg=actor.get("tg"),
            username=actor.get("username"),
            display_name=actor.get("display_name"),
            scope=actor.get("scope") or "user",
            level=level,
            operation=_operation_name_from_request(request),
            method=request.method,
            path=str(request.url.path or "")[:255] or None,
            status_code=status_code,
            message=str(exc) or exc.__class__.__name__,
            detail=detail,
        )
    except Exception as log_exc:
        LOGGER.warning(f"xiuxian error log persist failed: {log_exc}")


def _can_user_upload_images(user_id: int) -> tuple[bool, str]:
    if is_admin_user_id(user_id):
        return True, ""

    settings = get_xiuxian_settings()
    if bool(settings.get("allow_non_admin_image_upload", False)):
        return True, ""

    if has_image_upload_permission(user_id):
        return True, ""

    return False, "当前未开放普通用户上传图片，请联系主人开启总开关或单独授权。"


def _sanitize_upload_folder(folder: str | None) -> str:
    raw = (folder or "misc").strip().replace("\\", "/")
    parts = []
    for part in raw.split("/"):
        cleaned = "".join(ch for ch in part.lower() if ch.isalnum() or ch in {"-", "_"})
        if cleaned:
            parts.append(cleaned)
    return "/".join(parts[:3]) or "misc"


def _public_url_root(base_url: str | None = None) -> str:
    if api_config.public_url:
        return str(api_config.public_url).rstrip("/")
    return str(base_url or "").rstrip("/")


def _resolve_group_image_source(image_url: str | None) -> str | Path | None:
    if not image_url:
        return None
    image_url = str(image_url).strip()
    if not image_url:
        return None
    upload_path = image_url
    if image_url.startswith("http://") or image_url.startswith("https://"):
        parsed = urlsplit(image_url)
        upload_path = parsed.path or image_url
        if not upload_path.startswith("/plugins/xiuxian/uploads/"):
            return image_url
    if upload_path.startswith("/plugins/xiuxian/uploads/"):
        relative_path = upload_path.removeprefix("/plugins/xiuxian/uploads/").strip("/")
        local_path = UPLOAD_DIR.joinpath(*[part for part in relative_path.split("/") if part])
        if local_path.exists():
            return str(local_path)
        public_root = _public_url_root()
        if public_root:
            return f"{public_root}{upload_path}"
    return image_url


async def _save_uploaded_image(file: UploadFile, folder: str, base_url: str | None = None) -> dict[str, Any]:
    suffix = Path(file.filename or "").suffix.lower()
    content_type = (file.content_type or "").lower()
    if suffix not in ALLOWED_IMAGE_SUFFIXES and content_type not in ALLOWED_IMAGE_CONTENT_TYPES:
        raise HTTPException(status_code=400, detail="仅支持 jpg、png、webp、gif 图片格式")

    if suffix not in ALLOWED_IMAGE_SUFFIXES:
        mapping = {
            "image/jpeg": ".jpg",
            "image/png": ".png",
            "image/webp": ".webp",
            "image/gif": ".gif",
        }
        suffix = mapping.get(content_type, ".jpg")

    payload = await file.read()
    if not payload:
        raise HTTPException(status_code=400, detail="上传的图片不能为空")
    if len(payload) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=400, detail="图片大小不能超过 8MB")

    subdir = _sanitize_upload_folder(folder)
    target_dir = UPLOAD_DIR / subdir
    target_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{uuid4().hex}{suffix}"
    target = target_dir / filename
    target.write_bytes(payload)
    relative = Path(subdir) / filename
    relative_url = f"/plugins/xiuxian/uploads/{relative.as_posix()}"
    public_url = _public_url_root(base_url)
    return {
        "name": filename,
        "size": len(payload),
        "url": f"{public_url}{relative_url}" if public_url else relative_url,
        "relative_url": relative_url,
    }


def _format_profile_text(payload: dict[str, Any]) -> str:
    profile = payload["profile"]
    root_text = format_root(profile)
    effective_stats = payload.get("effective_stats") or {}
    equipped_artifacts = payload.get("equipped_artifacts") or []
    equip_limit = int(payload.get("settings", {}).get("artifact_equip_limit", 1) or 1)
    artifact_name = "、".join(item["name"] for item in equipped_artifacts) if equipped_artifacts else "暂无已装备法宝"
    talisman_name = payload["active_talisman"]["name"] if payload.get("active_talisman") else "暂无待生效符箓"
    technique_name = payload["current_technique"]["name"] if payload.get("current_technique") else "暂无参悟功法"
    title_name = payload["current_title"]["name"] if payload.get("current_title") else "未佩戴称号"
    progress = payload.get("progress", {})
    threshold = progress.get("threshold", 0)
    remaining_text = progress.get("remaining", 0)
    combat_power = int(payload.get("combat_power") or 0)
    return (
        f"**修仙总览**\n"
        f"灵根：{_md_escape(root_text)}\n"
        f"灵根品质：{_md_escape(profile.get('root_quality') or '灵根未定')}\n"
        f"境界：`{profile['realm_stage']}{profile['realm_layer']}层`\n"
        f"修为：`{profile['cultivation']} / {threshold}`\n"
        f"距离下一层：`{remaining_text}`\n"
        f"灵石：`{profile['spiritual_stone']}`\n"
        f"丹毒：`{profile['dan_poison']}/100`\n"
        f"根骨 / 悟性 / 神识 / 机缘：`{effective_stats.get('bone', profile.get('bone', 0))} / {effective_stats.get('comprehension', profile.get('comprehension', 0))} / {effective_stats.get('divine_sense', profile.get('divine_sense', 0))} / {effective_stats.get('fortune', profile.get('fortune', 0))}`\n"
        f"气血 / 真元 / 身法：`{effective_stats.get('qi_blood', profile.get('qi_blood', 0))} / {effective_stats.get('true_yuan', profile.get('true_yuan', 0))} / {effective_stats.get('body_movement', profile.get('body_movement', 0))}`\n"
        f"攻击 / 防御 / 战力：`{effective_stats.get('attack_power', profile.get('attack_power', 0))} / {effective_stats.get('defense_power', profile.get('defense_power', 0))} / {combat_power}`\n"
        f"法宝：{_md_escape(artifact_name)} `({len(equipped_artifacts)}/{equip_limit})`\n"
        f"符箓：{_md_escape(talisman_name)}\n"
        f"功法：{_md_escape(technique_name)}\n"
        f"称号：{_md_escape(title_name)}"
    )


def _md_escape(value: Any) -> str:
    return MARKDOWN_ESCAPE_PATTERN.sub(r"\\\1", str(value or ""))


def _format_group_profile_showcase(payload: dict[str, Any], fallback_name: str | None = None) -> str:
    profile = payload["profile"]
    effective_stats = payload.get("effective_stats") or {}
    progress = payload.get("progress") or {}
    equipped_artifacts = payload.get("equipped_artifacts") or []
    active_talisman = payload.get("active_talisman") or {}
    current_technique = payload.get("current_technique") or {}
    current_title = payload.get("current_title") or {}
    display_name = (
        profile.get("display_name_with_title")
        or profile.get("display_label")
        or profile.get("display_name")
        or fallback_name
        or f"TG {profile['tg']}"
    )
    artifact_lines = [f"· {item['name']}" for item in equipped_artifacts[:3]]
    if len(equipped_artifacts) > 3:
        artifact_lines.append(f"· 其余 {len(equipped_artifacts) - 3} 件")
    if not artifact_lines:
        artifact_lines.append("· 暂无已装备法宝")
    retreat_text = "闭关中" if payload.get("capabilities", {}).get("is_in_retreat") else "自在行走"
    if profile.get("retreat_end_at") and payload.get("capabilities", {}).get("is_in_retreat"):
        retreat_end_at = _parse_shanghai_datetime(profile.get("retreat_end_at"))
        retreat_display = retreat_end_at.strftime("%m-%d %H:%M") if retreat_end_at else str(profile.get("retreat_end_at"))
        retreat_text = f"闭关中，预计 {retreat_display} 出关"
    return "\n".join(
        [
            "🌌 **修仙名帖**",
            f"👤 道友：{_md_escape(display_name)}",
            f"🌱 灵根：{_md_escape(format_root(profile))}",
            f"🏯 境界：{_md_escape(str(profile['realm_stage']) + str(profile['realm_layer']) + '层')}",
            f"📈 修为：`{profile['cultivation']} / {progress.get('threshold', 0)}`（还差 `{progress.get('remaining', 0)}`）",
            f"💎 灵石：`{profile['spiritual_stone']}` ｜ ☠️ 丹毒：`{profile['dan_poison']}/100`",
            f"🏷️ 称号：{_md_escape(current_title.get('name') or '未佩戴称号')}",
            (
                "⚔️ 战斗："
                f"`攻 {effective_stats.get('attack_power', profile.get('attack_power', 0))}` ｜ "
                f"`防 {effective_stats.get('defense_power', profile.get('defense_power', 0))}` ｜ "
                f"`战力 {payload.get('combat_power', 0)}`"
            ),
            (
                "🧭 资质："
                f"`根骨 {effective_stats.get('bone', profile.get('bone', 0))}` ｜ "
                f"`悟性 {effective_stats.get('comprehension', profile.get('comprehension', 0))}` ｜ "
                f"`神识 {effective_stats.get('divine_sense', profile.get('divine_sense', 0))}` ｜ "
                f"`机缘 {effective_stats.get('fortune', profile.get('fortune', 0))}`"
            ),
            "🛡️ 法宝：",
            *[_md_escape(line) for line in artifact_lines],
            f"🧿 符箓：{_md_escape(active_talisman.get('name') or '暂无待生效符箓')}",
            f"📜 功法：{_md_escape(current_technique.get('name') or '暂无参悟功法')}",
            f"🕰️ 状态：{_md_escape(retreat_text)}",
        ]
    )


def _build_bottom_nav() -> list[dict[str, str]]:
    items = [
        {
            "id": "home",
            "label": "主页",
            "path": "/miniapp",
            "icon": "⌂",
        }
    ]

    for plugin in list_plugins():
        if not plugin.get("enabled"):
            continue
        plugin_visible = bool(config.plugin_nav.get(plugin["id"], plugin.get("bottom_nav_default", False)))
        if not plugin.get("miniapp_path") or not plugin_visible:
            continue

        items.append(
            {
                "id": plugin["id"],
                "label": plugin.get("miniapp_label") or plugin["name"],
                "path": plugin["miniapp_path"],
                "icon": plugin.get("miniapp_icon") or "◇",
            }
        )

    return items


def _main_group_chat_id() -> int | None:
    if not group:
        return None
    return int(group[0])


def _admin_panel_url() -> str:
    return build_plugin_url("/plugins/xiuxian/admin") or "/plugins/xiuxian/admin"


async def _is_group_admin(client, chat_id: int, user_id: int) -> bool:
    try:
        member = await client.get_chat_member(chat_id, user_id)
    except Exception as exc:
        LOGGER.warning(f"xiuxian group admin check failed chat={chat_id} user={user_id}: {exc}")
        return False
    return member.status in {ChatMemberStatus.OWNER, ChatMemberStatus.ADMINISTRATOR}


async def _can_manage_upload_permissions(client, msg) -> bool:
    if msg.from_user is None:
        return False
    if is_admin_user_id(msg.from_user.id):
        return True
    chat = getattr(msg, "chat", None)
    if chat is None:
        return False
    try:
        chat_id = int(chat.id)
    except (TypeError, ValueError):
        return False
    return chat_id < 0 and await _is_group_admin(client, chat_id, msg.from_user.id)


async def _require_message_user(message, *, action_text: str) -> Any | None:
    user = getattr(message, "from_user", None)
    if user is not None:
        return user
    if getattr(message, "sender_chat", None) is not None:
        await _reply_text(
            message,
            f"当前消息来自匿名管理员或频道身份，机器人拿不到真实 TG 账号，无法{action_text}。请关闭匿名发送后重试。",
            quote=True,
        )
    else:
        await _reply_text(message, f"当前无法识别你的 TG 身份，暂时不能{action_text}。", quote=True)
    return None


def _remember_journal(tg: int, action_type: str, title: str, detail: str | None = None) -> None:
    try:
        create_journal(tg, action_type, title, detail)
    except Exception as exc:
        LOGGER.warning(f"xiuxian journal write failed: {exc}")


def _achievement_private_text(unlock: dict[str, Any]) -> str:
    achievement = unlock.get("achievement") or {}
    reward_summary = unlock.get("reward_summary") or format_reward_summary(achievement.get("reward_config"))
    metric_label = unlock.get("metric_label") or achievement.get("metric_key") or "进度"
    metric_value = int(unlock.get("metric_value") or 0)
    return "\n".join(
        [
            "🏅 **成就达成**",
            f"你获得了 **{_md_escape(achievement.get('name') or '未知成就')}**",
            f"📖 说明：{_md_escape(achievement.get('description') or '达成指定目标。')}",
            f"📈 进度：{_md_escape(metric_label)} `已达到 {metric_value}/{achievement.get('target_value') or 0}`",
            f"🎁 奖励：{_md_escape(reward_summary)}",
        ]
    )


def _achievement_group_text(unlock: dict[str, Any]) -> str:
    achievement = unlock.get("achievement") or {}
    reward_summary = unlock.get("reward_summary") or format_reward_summary(achievement.get("reward_config"))
    display_name = unlock.get("display_name") or f"TG {unlock.get('tg')}"
    return "\n".join(
        [
            "📣 **成就喜报**",
            f"恭喜 {_md_escape(display_name)} 达成 **{_md_escape(achievement.get('name') or '未知成就')}**",
            f"🎁 奖励：{_md_escape(reward_summary)}",
        ]
    )


async def _notify_achievement_unlocks(unlocks: list[dict[str, Any]] | None) -> None:
    if not unlocks:
        return
    group_chat_id = _main_group_chat_id()
    for unlock in unlocks:
        achievement = unlock.get("achievement") or {}
        achievement_id = int(achievement.get("id") or unlock.get("achievement_id") or 0)
        tg = int(unlock.get("tg") or 0)
        if achievement_id <= 0 or tg <= 0:
            continue
        if achievement.get("notify_private") and not unlock.get("private_notified_at"):
            try:
                await _send_message(
                    bot,
                    tg,
                    _achievement_private_text(unlock),
                    persistent=True,
                    parse_mode=RICH_TEXT_MODE,
                )
                mark_user_achievement_notification(tg, achievement_id, "private")
            except Exception as exc:
                LOGGER.warning(f"xiuxian achievement private notify failed tg={tg} achievement={achievement_id}: {exc}")
        if group_chat_id and achievement.get("notify_group") and not unlock.get("group_notified_at"):
            try:
                await _send_message(
                    bot,
                    group_chat_id,
                    _achievement_group_text(unlock),
                    parse_mode=RICH_TEXT_MODE,
                )
                mark_user_achievement_notification(tg, achievement_id, "group")
            except Exception as exc:
                LOGGER.warning(f"xiuxian achievement group notify failed tg={tg} achievement={achievement_id}: {exc}")


def _full_bundle(tg: int) -> dict[str, Any]:
    Session.remove()
    bundle = serialize_full_profile(tg)
    world_bundle = build_world_bundle(tg)
    bundle.update({key: value for key, value in world_bundle.items() if key != "settings"})
    can_upload_images, upload_reason = _can_user_upload_images(tg)
    bundle.setdefault("capabilities", {})
    bundle["capabilities"]["can_upload_images"] = can_upload_images
    bundle["capabilities"]["upload_image_reason"] = upload_reason
    bundle.setdefault("settings", {})
    bundle["settings"].update(world_bundle.get("settings", {}))
    bundle["settings"]["allow_non_admin_image_upload"] = bool(
        get_xiuxian_settings().get("allow_non_admin_image_upload", False)
    )
    bundle["capabilities"]["is_admin"] = bool(is_admin_user_id(tg))
    bundle["capabilities"]["admin_panel_url"] = _admin_panel_url() if is_admin_user_id(tg) else None
    return bundle


def _message_auto_delete_seconds() -> int:
    raw = get_xiuxian_settings().get(
        "message_auto_delete_seconds",
        DEFAULT_SETTINGS.get("message_auto_delete_seconds", 180),
    )
    try:
        return max(int(raw or 0), 0)
    except (TypeError, ValueError):
        return int(DEFAULT_SETTINGS.get("message_auto_delete_seconds", 180))


async def _delete_message_after_delay(message, key: tuple[int, int], delay: int) -> None:
    try:
        await asyncio.sleep(delay)
        await message.delete()
    except asyncio.CancelledError:
        raise
    except Exception as exc:
        LOGGER.debug(f"xiuxian auto delete skipped chat={key[0]} message={key[1]}: {exc}")
    finally:
        task = MESSAGE_AUTO_DELETE_TASKS.get(key)
        if task is asyncio.current_task():
            MESSAGE_AUTO_DELETE_TASKS.pop(key, None)


def _apply_message_auto_delete(message, *, persistent: bool = False, seconds: int | None = None):
    if message is None:
        return None
    chat = getattr(message, "chat", None)
    message_id = getattr(message, "id", None)
    chat_id = getattr(chat, "id", None)
    if chat_id is None or message_id is None:
        return message
    key = (int(chat_id), int(message_id))
    existing = MESSAGE_AUTO_DELETE_TASKS.pop(key, None)
    if existing is not None:
        existing.cancel()
    delay = max(int(seconds if seconds is not None else _message_auto_delete_seconds()), 0)
    if persistent or delay <= 0:
        return message
    MESSAGE_AUTO_DELETE_TASKS[key] = asyncio.create_task(_delete_message_after_delay(message, key, delay))
    return message


async def _reply_text(message, text: str, *, persistent: bool = False, auto_delete_seconds: int | None = None, **kwargs):
    sent = await message.reply_text(text, **kwargs)
    return _apply_message_auto_delete(sent, persistent=persistent, seconds=auto_delete_seconds)


async def _delete_user_command_message(message) -> None:
    if message is None:
        return
    try:
        await message.delete()
    except Exception as exc:
        chat_id = getattr(getattr(message, "chat", None), "id", None)
        message_id = getattr(message, "id", None)
        LOGGER.debug(f"xiuxian command delete skipped chat={chat_id} message={message_id}: {exc}")


async def _send_message(client, chat_id: int, text: str, *, persistent: bool = False, auto_delete_seconds: int | None = None, **kwargs):
    sent = await client.send_message(chat_id, text, **kwargs)
    return _apply_message_auto_delete(sent, persistent=persistent, seconds=auto_delete_seconds)


async def _send_photo(client, chat_id: int, photo, *, persistent: bool = False, auto_delete_seconds: int | None = None, **kwargs):
    sent = await client.send_photo(chat_id, photo, **kwargs)
    return _apply_message_auto_delete(sent, persistent=persistent, seconds=auto_delete_seconds)


async def _edit_text(message, text: str, *, persistent: bool = False, auto_delete_seconds: int | None = None, **kwargs):
    edited = await message.edit_text(text, **kwargs)
    return _apply_message_auto_delete(edited, persistent=persistent, seconds=auto_delete_seconds)


async def _edit_caption(message, caption: str, *, persistent: bool = False, auto_delete_seconds: int | None = None, **kwargs):
    edited = await message.edit_caption(caption, **kwargs)
    return _apply_message_auto_delete(edited, persistent=persistent, seconds=auto_delete_seconds)


async def _edit_message_text(
    client,
    chat_id: int,
    message_id: int,
    text: str,
    *,
    persistent: bool = False,
    auto_delete_seconds: int | None = None,
    **kwargs,
):
    edited = await client.edit_message_text(chat_id, message_id, text, **kwargs)
    return _apply_message_auto_delete(edited, persistent=persistent, seconds=auto_delete_seconds)


def _duel_settlement_total_pages(bet_settlement: dict[str, Any] | None) -> int:
    rows = list((bet_settlement or {}).get("entries") or [])
    return max((len(rows) + DUEL_SETTLEMENT_PAGE_SIZE - 1) // DUEL_SETTLEMENT_PAGE_SIZE, 1)


def _effective_divine_sense(payload: dict[str, Any]) -> int:
    profile = payload.get("profile") or {}
    effective_stats = payload.get("effective_stats") or {}
    return int(effective_stats.get("divine_sense", profile.get("divine_sense", 0)) or 0)


def _duel_profile_label(profile: dict[str, Any] | None) -> str:
    profile = profile or {}
    return (
        str(profile.get("display_name_with_title") or "").strip()
        or str(profile.get("display_label") or "").strip()
        or str(profile.get("display_name") or "").strip()
        or (f"@{profile['username']}" if str(profile.get("username") or "").strip() else f"TG {profile.get('tg', 0)}")
    )


def _duel_side_label(side: str | None) -> str:
    return "挑战者" if side == "challenger" else "应战者"


def _gift_group_broadcast_text(sender_name: str, receiver: dict[str, Any], amount: int) -> str:
    receiver_label = (
        str(receiver.get("display_name_with_title") or "").strip()
        or str(receiver.get("display_label") or "").strip()
        or str(receiver.get("display_name") or "").strip()
        or (f"@{receiver['username']}" if str(receiver.get("username") or "").strip() else f"TG {receiver.get('tg', 0)}")
    )
    return "\n".join(
        [
            "🎁 **灵石赠礼**",
            f"{_md_escape(sender_name)} 向 {_md_escape(receiver_label)} 赠出了 `{int(amount or 0)}` 灵石。",
            "一份机缘已经当众完成交接。",
        ]
    )


def _format_attribute_growth_text(changes: list[dict[str, Any]] | None, *, prefix: str = "小幅成长") -> str:
    rows = []
    for item in changes or []:
        label = str(item.get("label") or item.get("key") or "属性").strip()
        value = int(item.get("value") or 0)
        if value <= 0:
            continue
        rows.append(f"{label}+{value}")
    if not rows:
        return ""
    return f"{prefix}：{'、'.join(rows)}"


def _normalize_commission_command_key(raw: str | None) -> str | None:
    token = str(raw or "").strip()
    if not token:
        return None
    normalized = token.lower()
    return COMMISSION_COMMAND_ALIASES.get(normalized) or COMMISSION_COMMAND_ALIASES.get(token)


def _select_group_commission(bundle: dict[str, Any], requested_key: str | None = None) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    commissions = list(bundle.get("commissions") or [])
    if requested_key:
        for item in commissions:
            if str(item.get("key") or "").strip() == requested_key:
                return item, commissions
        return None, commissions
    available = [item for item in commissions if item.get("available")]
    available.sort(
        key=lambda item: (
            int(item.get("reward_stone_max") or 0),
            int(item.get("reward_cultivation_max") or 0),
            int(item.get("min_realm_layer") or 0),
        ),
        reverse=True,
    )
    return (available[0] if available else None), commissions


def _commission_selection_error(bundle: dict[str, Any], requested_key: str | None = None) -> str:
    selected, commissions = _select_group_commission(bundle, requested_key=requested_key)
    if selected and selected.get("available"):
        return ""
    if requested_key:
        for item in commissions:
            if str(item.get("key") or "").strip() == requested_key:
                reason = str(item.get("reason") or "").strip() or "当前暂不可承接。"
                return f"{item.get('name') or '该委托'} 暂不可承接：{reason}"
        return "未找到对应的灵石委托。可用示例：/work、/work 灵田、/work 修剑。"
    locked_rows = commissions[:3]
    if not locked_rows:
        return "当前没有可承接的灵石委托。"
    preview = "；".join(
        f"{item.get('name') or item.get('key')}: {str(item.get('reason') or '暂不可承接').strip()}"
        for item in locked_rows
    )
    return f"当前没有可承接的灵石委托。{preview}"


def _minimal_player_lookup_payload(result: dict[str, Any], self_tg: int) -> dict[str, Any]:
    rows = []
    skipped_self = 0
    for item in result.get("items") or []:
        tg_value = int(item.get("tg") or 0)
        if tg_value <= 0:
            continue
        if tg_value == int(self_tg):
            skipped_self += 1
            continue
        username = str(item.get("username") or "").strip().lstrip("@")
        display_name = str(item.get("display_name") or "").strip()
        display_label = display_name or (f"@{username}" if username else f"TG {tg_value}")
        rows.append(
            {
                "tg": tg_value,
                "display_label": display_label,
                "username": username or None,
                "hint": f"@{username}" if username else f"TG {tg_value}",
            }
        )
    total = max(int(result.get("total") or len(rows)) - skipped_self, 0)
    return {
        "items": rows,
        "page": int(result.get("page") or 1),
        "page_size": int(result.get("page_size") or len(rows) or 1),
        "total": total,
    }


def _resolve_gift_target_and_amount(msg, inline_amount: int | None = None) -> tuple[int, int]:
    reply_user = getattr(getattr(msg, "reply_to_message", None), "from_user", None)
    args = [str(item).strip() for item in (msg.command or [])[1:] if str(item or "").strip()]
    if inline_amount is not None:
        if reply_user is None:
            raise ValueError("请先回复收礼道友，再使用 /gift100 或 /gift 100。")
        if getattr(reply_user, "is_bot", False):
            raise ValueError("不能给机器人赠送灵石。")
        return int(reply_user.id), int(inline_amount)
    if reply_user is not None and len(args) == 1:
        if getattr(reply_user, "is_bot", False):
            raise ValueError("不能给机器人赠送灵石。")
        return int(reply_user.id), int(args[0])
    if len(args) >= 2:
        return int(args[0]), int(args[1])
    raise ValueError("用法：回复目标后发送 /gift <灵石数量>；或使用 /gift <TGID> <灵石数量>")


def _build_duel_result_private_message(result: dict[str, Any], recipient_tg: int) -> str:
    challenger = (result.get("challenger") or {}).get("profile") or {}
    defender = (result.get("defender") or {}).get("profile") or {}
    is_challenger = int(recipient_tg) == int(challenger.get("tg") or 0)
    recipient = challenger if is_challenger else defender
    opponent = defender if is_challenger else challenger
    won = int(result.get("winner_tg") or 0) == int(recipient_tg)
    lines = [
        "⚔️ **斗法结果通知**",
        f"对手：{_md_escape(_duel_profile_label(opponent))}",
        f"结果：**{'胜出' if won else '落败'}**",
        f"🧾 {_md_escape(str(result.get('summary') or '本场斗法已完成结算。'))}",
    ]

    stake = int(result.get("stake") or 0)
    if stake > 0:
        lines.append(f"{'💰' if won else '💸'} 赌斗结果：{'赢得' if won else '输掉'} `{stake}` 灵石")

    plunder_amount = int(result.get("plunder_amount") or 0)
    if plunder_amount > 0:
        lines.append(f"🪙 额外灵石：{'掠夺' if won else '被掠夺'} `{plunder_amount}` 灵石")

    artifact_payload = ((result.get("artifact_plunder") or {}).get("artifact") or {})
    if artifact_payload:
        artifact_name = artifact_payload.get("name", "未知法宝")
        lines.append(f"🗡️ 法宝结果：{'夺得' if won else '被夺走'} `{_md_escape(artifact_name)}`")

    lines.append(f"📦 当前灵石：`{int(recipient.get('spiritual_stone') or 0)}`")
    return "\n".join(lines)


def _build_duel_bet_private_message(result: dict[str, Any], entry: dict[str, Any]) -> str:
    challenger = (result.get("challenger") or {}).get("profile") or {}
    defender = (result.get("defender") or {}).get("profile") or {}
    winner_tg = int(result.get("winner_tg") or 0)
    winner_profile = challenger if int(challenger.get("tg") or 0) == winner_tg else defender
    won = str(entry.get("result") or "") == "win"
    lines = [
        "🎯 **斗法押注结算**",
        f"对局：{_md_escape(_duel_profile_label(challenger))} vs {_md_escape(_duel_profile_label(defender))}",
        f"胜者：{_md_escape(_duel_profile_label(winner_profile))}",
        f"你押：{_md_escape(_duel_side_label(str(entry.get('side') or '')))}",
        f"下注：`{int(entry.get('bet_amount') or 0)}` 灵石",
        f"结果：**{'押中' if won else '押错'}**",
    ]
    if won:
        lines.append(f"💰 返还：`{int(entry.get('amount') or 0)}` 灵石")
        lines.append(f"📈 净赚：`{int(entry.get('net_profit') or 0)}` 灵石")
    else:
        lines.append(f"📉 净亏：`{abs(int(entry.get('net_profit') or 0))}` 灵石")
    return "\n".join(lines)


async def _notify_duel_participants(result: dict[str, Any]) -> None:
    challenger = (result.get("challenger") or {}).get("profile") or {}
    defender = (result.get("defender") or {}).get("profile") or {}
    for profile in (challenger, defender):
        target_tg = int(profile.get("tg") or 0)
        if target_tg <= 0:
            continue
        try:
            await _send_message(
                bot,
                target_tg,
                _build_duel_result_private_message(result, target_tg),
                persistent=True,
                parse_mode=RICH_TEXT_MODE,
            )
        except Exception as exc:
            LOGGER.warning(f"xiuxian duel participant notify failed tg={target_tg}: {exc}")


async def _notify_duel_bettors(result: dict[str, Any], bet_settlement: dict[str, Any] | None) -> None:
    for entry in list((bet_settlement or {}).get("entries") or []):
        target_tg = int(entry.get("tg") or 0)
        if target_tg <= 0:
            continue
        try:
            await _send_message(
                bot,
                target_tg,
                _build_duel_bet_private_message(result, entry),
                persistent=True,
                parse_mode=RICH_TEXT_MODE,
            )
        except Exception as exc:
            LOGGER.warning(f"xiuxian duel bettor notify failed tg={target_tg}: {exc}")


def _duel_bet_keyboard(pool_id: int) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton("押挑战者 10", callback_data=f"xiuxian:bet:{pool_id}:challenger:10"),
            InlineKeyboardButton("押应战者 10", callback_data=f"xiuxian:bet:{pool_id}:defender:10"),
        ],
        [
            InlineKeyboardButton("押挑战者 50", callback_data=f"xiuxian:bet:{pool_id}:challenger:50"),
            InlineKeyboardButton("押应战者 50", callback_data=f"xiuxian:bet:{pool_id}:defender:50"),
        ],
        [
            InlineKeyboardButton("押挑战者 100", callback_data=f"xiuxian:bet:{pool_id}:challenger:100"),
            InlineKeyboardButton("押应战者 100", callback_data=f"xiuxian:bet:{pool_id}:defender:100"),
        ],
    ]
    return InlineKeyboardMarkup(rows)


def _duel_settlement_keyboard(pool_id: int, page: int, total_pages: int) -> InlineKeyboardMarkup | None:
    if total_pages <= 1:
        return None
    rows = [[]]
    if page > 1:
        rows[0].append(InlineKeyboardButton("上一页", callback_data=f"xiuxian:settlement:{pool_id}:{page - 1}"))
    rows[0].append(InlineKeyboardButton(f"{page}/{total_pages}", callback_data=f"xiuxian:settlement:{pool_id}:{page}"))
    if page < total_pages:
        rows[0].append(InlineKeyboardButton("下一页", callback_data=f"xiuxian:settlement:{pool_id}:{page + 1}"))
    return InlineKeyboardMarkup(rows)


def _red_envelope_keyboard(envelope_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("领取红包", callback_data=f"xiuxian:red:{envelope_id}")]]
    )


def _encounter_keyboard(instance_id: int, button_text: str | None = None) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton(button_text or "争抢机缘", callback_data=f"xiuxian:encounter:{instance_id}")]]
    )


def _auction_time_text(value: str | None) -> str:
    dt = _parse_shanghai_datetime(value)
    if dt is None:
        return str(value or "未设置")
    return dt.strftime("%m-%d %H:%M")


def _auction_group_text(auction: dict[str, Any]) -> str:
    auction = auction or {}
    seller_name = str(auction.get("owner_display_name") or "").strip() or f"TG {auction.get('owner_tg', 0)}"
    item_name = str(auction.get("item_name") or "未知拍品")
    item_kind = str(auction.get("item_kind_label") or auction.get("item_kind") or "拍品")
    quantity = max(int(auction.get("quantity") or 0), 0)
    opening_price = int(auction.get("opening_price_stone") or 0)
    current_price = int(auction.get("current_display_price_stone") or opening_price)
    increment = max(int(auction.get("bid_increment_stone") or 0), 1)
    buyout = int(auction.get("buyout_price_stone") or 0)
    fee_percent = max(int(auction.get("fee_percent") or 0), 0)
    bid_count = max(int(auction.get("bid_count") or 0), 0)
    leader_name = str(auction.get("highest_bidder_display_name") or "").strip()
    winner_name = str(auction.get("winner_display_name") or "").strip()
    end_text = _auction_time_text(auction.get("end_at"))
    status = str(auction.get("status") or "active")

    if status == "sold":
        final_price = int(auction.get("final_price_stone") or current_price)
        fee_amount = int(auction.get("fee_amount_stone") or 0)
        seller_income = int(auction.get("seller_income_stone") or 0)
        winner_label = winner_name or f"TG {auction.get('winner_tg', 0)}"
        return "\n".join(
            [
                "🏺 **拍卖已结束**",
                f"📦 拍品：**{_md_escape(item_name)}** × `{quantity}`",
                f"👤 卖家：{_md_escape(seller_name)}",
                f"🏆 得主：{_md_escape(winner_label)}",
                f"💰 成交价：`{final_price}` 灵石",
                f"🧾 手续费：`{fee_amount}` 灵石（{fee_percent}%）",
                f"📥 卖家入账：`{seller_income}` 灵石",
            ]
        )

    if status == "expired":
        return "\n".join(
            [
                "⌛ **拍卖已流拍**",
                f"📦 拍品：**{_md_escape(item_name)}** × `{quantity}`",
                f"👤 卖家：{_md_escape(seller_name)}",
                "本场无人出价，拍品已原路退回卖家。",
            ]
        )

    if status == "cancelled":
        return "\n".join(
            [
                "⚠️ **拍卖已取消**",
                f"📦 拍品：**{_md_escape(item_name)}** × `{quantity}`",
                f"👤 卖家：{_md_escape(seller_name)}",
                "拍品与竞拍灵石均已按规则退回。",
            ]
        )

    leader_line = f"👑 当前领先：{_md_escape(leader_name)} `({current_price} 灵石)`" if leader_name else "👑 当前领先：暂无"
    buyout_line = f"⚡ 一口价：`{buyout}` 灵石" if buyout > 0 else "⚡ 一口价：未设置"
    return "\n".join(
        [
            "🏺 **群内拍卖**",
            f"📦 拍品：**{_md_escape(item_name)}** × `{quantity}`",
            f"📚 类型：{_md_escape(item_kind)}",
            f"👤 卖家：{_md_escape(seller_name)}",
            f"💰 起拍价：`{opening_price}` 灵石",
            f"📈 当前价格：`{current_price}` 灵石",
            f"🔺 每次加价：`{increment}` 灵石",
            buyout_line,
            f"🧾 成交手续费：`{fee_percent}%`",
            f"🕒 结束时间：`{end_text}`",
            f"🪧 出价次数：`{bid_count}`",
            leader_line,
            "",
            "点下方按钮即可出价，系统会自动刷新竞拍面板。",
        ]
    )


def _auction_bid_button_text(auction: dict[str, Any]) -> str:
    next_bid_price = int(auction.get("next_bid_price_stone") or auction.get("opening_price_stone") or 0)
    if int(auction.get("bid_count") or 0) <= 0:
        return f"出价 {next_bid_price} 灵石"
    return f"加价到 {next_bid_price} 灵石"


def _auction_keyboard(auction: dict[str, Any]) -> InlineKeyboardMarkup | None:
    auction = auction or {}
    if str(auction.get("status") or "active") != "active":
        return None

    rows = [[InlineKeyboardButton(_auction_bid_button_text(auction), callback_data=f"xiuxian:auction:bid:{auction['id']}")]]
    buyout_price = int(auction.get("buyout_price_stone") or 0)
    current_price = int(auction.get("current_display_price_stone") or 0)
    if buyout_price > 0 and current_price < buyout_price:
        rows.append([InlineKeyboardButton(f"一口价 {buyout_price} 灵石", callback_data=f"xiuxian:auction:buyout:{auction['id']}")])
    return InlineKeyboardMarkup(rows)


async def _refresh_auction_group_message(auction: dict[str, Any]) -> None:
    auction = auction or {}
    chat_id = int(auction.get("group_chat_id") or 0)
    message_id = int(auction.get("group_message_id") or 0)
    if not chat_id or not message_id:
        return
    try:
        await _edit_message_text(
            bot,
            chat_id,
            message_id,
            _auction_group_text(auction),
            reply_markup=_auction_keyboard(auction),
            parse_mode=RICH_TEXT_MODE,
            persistent=True,
        )
    except Exception as exc:
        LOGGER.warning(f"xiuxian auction message refresh failed auction={auction.get('id')} chat={chat_id}: {exc}")


async def _pin_auction_group_message(chat_id: int, message_id: int) -> str | None:
    try:
        await bot.pin_chat_message(chat_id=chat_id, message_id=message_id, disable_notification=True)
    except Exception as exc:
        LOGGER.warning(f"xiuxian auction pin failed chat={chat_id} message={message_id}: {exc}")
        return "拍卖消息已推送到群里，但置顶失败，请检查机器人是否具备置顶权限。"
    return None


async def _unpin_auction_group_message(auction: dict[str, Any]) -> None:
    auction = auction or {}
    chat_id = int(auction.get("group_chat_id") or 0)
    message_id = int(auction.get("group_message_id") or 0)
    if not chat_id or not message_id:
        return
    try:
        await bot.unpin_chat_message(chat_id=chat_id, message_id=message_id)
    except Exception as exc:
        LOGGER.warning(f"xiuxian auction unpin failed auction={auction.get('id')} chat={chat_id}: {exc}")


def _drop_auction_finalize_task(auction_id: int) -> None:
    task = AUCTION_FINALIZE_TASKS.pop(int(auction_id), None)
    if task is not None and not task.done():
        task.cancel()


async def _finalize_auction_flow(result: dict[str, Any] | None) -> None:
    if not result:
        return
    auction = result.get("auction") or {}
    if not auction:
        return
    _drop_auction_finalize_task(int(auction.get("id") or 0))
    await _refresh_auction_group_message(auction)
    await _unpin_auction_group_message(auction)

    outcome = str(result.get("result") or "")
    chat_id = int(auction.get("group_chat_id") or _main_group_chat_id() or 0)
    winner_tg = int(result.get("winner_tg") or 0)
    seller_tg = int(result.get("seller_tg") or 0)
    item_name = str(auction.get("item_name") or "未知拍品")

    if outcome == "sold":
        winner_name = str(result.get("winner_display_name") or auction.get("winner_display_name") or "").strip() or f"TG {winner_tg}"
        final_price = int(auction.get("final_price_stone") or result.get("final_price_stone") or 0)
        seller_income = int(result.get("seller_income_stone") or auction.get("seller_income_stone") or 0)
        fee_amount = int(result.get("fee_amount_stone") or auction.get("fee_amount_stone") or 0)
        if chat_id:
            await _send_message(
                bot,
                chat_id,
                "\n".join(
                    [
                        "🎉 **拍卖成交**",
                        f"恭喜 {_md_escape(winner_name)} 以 `{final_price}` 灵石拍得 **{_md_escape(item_name)}**。",
                        f"🧾 手续费：`{fee_amount}` 灵石",
                        f"📥 卖家入账：`{seller_income}` 灵石",
                    ]
                ),
                parse_mode=RICH_TEXT_MODE,
                persistent=True,
            )
        if winner_tg > 0:
            try:
                await _send_message(
                    bot,
                    winner_tg,
                    f"🎉 恭喜你拍得【{item_name}】，成交价 {final_price} 灵石。",
                    persistent=True,
                )
            except Exception as exc:
                LOGGER.warning(f"xiuxian auction winner notify failed tg={winner_tg}: {exc}")
        if seller_tg > 0:
            try:
                await _send_message(
                    bot,
                    seller_tg,
                    f"💰 你的拍卖【{item_name}】已成交，到账 {seller_income} 灵石，手续费 {fee_amount} 灵石。",
                    persistent=True,
                )
            except Exception as exc:
                LOGGER.warning(f"xiuxian auction seller notify failed tg={seller_tg}: {exc}")
        return

    if outcome == "expired" and seller_tg > 0:
        try:
            await _send_message(bot, seller_tg, f"⌛ 你的拍卖【{item_name}】已流拍，拍品已退回背包。", persistent=True)
        except Exception as exc:
            LOGGER.warning(f"xiuxian auction expire notify failed tg={seller_tg}: {exc}")


def _queue_auction_finalize_task(auction: dict[str, Any] | None) -> None:
    auction = auction or {}
    auction_id = int(auction.get("id") or 0)
    if auction_id <= 0 or str(auction.get("status") or "") != "active":
        return
    existing = AUCTION_FINALIZE_TASKS.get(auction_id)
    if existing is not None and not existing.done():
        return
    end_at = _parse_shanghai_datetime(auction.get("end_at"))
    if end_at is None:
        return

    loop = asyncio.get_event_loop()

    async def runner() -> None:
        try:
            remaining = max((end_at - datetime.now(SHANGHAI_TZ)).total_seconds(), 0)
            if remaining > 0:
                await asyncio.sleep(remaining)
            result = finalize_auction_listing(auction_id, force=True)
            if result and str(result.get("result") or "") not in {"noop", ""}:
                await _finalize_auction_flow(result)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            LOGGER.warning(f"xiuxian auction finalize task failed auction={auction_id}: {exc}")
        finally:
            task = AUCTION_FINALIZE_TASKS.get(auction_id)
            if task is asyncio.current_task():
                AUCTION_FINALIZE_TASKS.pop(auction_id, None)

    AUCTION_FINALIZE_TASKS[auction_id] = loop.create_task(runner())


def _schedule_active_auction_finalize_tasks() -> None:
    for auction in list_auction_items(status="active"):
        _queue_auction_finalize_task(auction)


async def _push_auction_to_group(auction: dict[str, Any]) -> tuple[dict[str, Any], str | None]:
    chat_id = int(auction.get("group_chat_id") or _main_group_chat_id() or 0)
    if not chat_id:
        raise ValueError("未配置修仙群组，无法推送拍卖消息。")
    sent = await _send_message(
        bot,
        chat_id,
        _auction_group_text(auction),
        reply_markup=_auction_keyboard(auction),
        parse_mode=RICH_TEXT_MODE,
        persistent=True,
    )
    updated = patch_auction_listing(int(auction["id"]), group_chat_id=chat_id, group_message_id=sent.id) or {
        **auction,
        "group_chat_id": chat_id,
        "group_message_id": sent.id,
    }
    pin_warning = await _pin_auction_group_message(chat_id, sent.id)
    _queue_auction_finalize_task(updated)
    return updated, pin_warning


def _quiz_task_text(task: dict[str, Any]) -> str:
    reward_parts = []
    if int(task.get("reward_stone") or 0):
        reward_parts.append(f"{task['reward_stone']} 灵石")
    if task.get("reward_item_kind") and task.get("reward_item_quantity"):
        reward_parts.append(f"{task['reward_item_quantity']} 个 {task.get('reward_item_kind_label') or task['reward_item_kind']}")
    reward_text = "、".join(reward_parts) or "暂未设置奖励"
    return (
        f"🧩 **答题悬赏**\n"
        f"📌 类型：{_md_escape(task.get('task_scope_label') or '官方任务')} ｜ 标题：**{_md_escape(task['title'])}**\n"
        f"📝 {_md_escape(task.get('description') or '请完成任务后领取奖励。')}\n\n"
        f"❓ 题目：{_md_escape(task.get('question_text') or '请直接在群里回复正确答案。')}\n"
        f"🎁 奖励：{_md_escape(reward_text)}\n"
        "🥇 首位答对的道友即可完成任务并领取奖励。"
    )


def _task_required_text(task: dict[str, Any]) -> str:
    if not task.get("required_item_kind") or not int(task.get("required_item_quantity") or 0):
        return ""
    item = task.get("required_item") or {}
    item_name = item.get("name") or task.get("required_item_kind_label") or task.get("required_item_kind") or "物品"
    return f"提交需求：{int(task.get('required_item_quantity') or 0)} 个 {item_name}"


def _task_group_text(task: dict[str, Any]) -> str:
    if task.get("task_type") == "quiz":
        return _quiz_task_text(task)

    reward_parts = []
    if int(task.get("reward_stone") or 0):
        reward_parts.append(f"{task['reward_stone']} 灵石")
    if task.get("reward_item_kind") and task.get("reward_item_quantity"):
        reward_parts.append(f"{task['reward_item_quantity']} 个 {task.get('reward_item_kind_label') or task['reward_item_kind']}")
    reward_text = "、".join(reward_parts) or "暂未设置奖励"
    required_text = _task_required_text(task)
    required_line = f"{required_text}\n" if required_text else ""
    return (
        f"📜 **悬赏委托**\n"
        f"📌 类型：{_md_escape(task.get('task_scope_label') or '任务')} ｜ 标题：**{_md_escape(task['title'])}**\n"
        f"📝 {_md_escape(task.get('description') or '请前往修仙面板领取或完成任务。')}\n\n"
        f"{_md_escape(required_line) if required_line else ''}"
        f"🎁 奖励：{_md_escape(reward_text)}\n"
        "🧭 道友们可前往修仙面板查看详情。"
    )


def _split_photo_caption(text: str, limit: int = 1024) -> tuple[str, str]:
    content = str(text or "").strip()
    if len(content) <= limit:
        return content, ""
    candidate = content[:limit]
    cut = -1
    for marker in ("\n\n", "\n", "。", "，", " "):
        pos = candidate.rfind(marker)
        if pos >= int(limit * 0.6):
            cut = pos + len(marker)
            break
    if cut <= 0:
        cut = limit
    head = content[:cut].rstrip()
    tail = content[cut:].lstrip()
    return head, tail


async def _build_red_envelope_generated_cover(envelope: dict[str, Any]) -> BytesIO | None:
    sender_name = "道友"
    sender_photo = None
    creator_tg = int(envelope.get("creator_tg") or 0)
    if creator_tg:
        try:
            telegram_user = await bot.get_users(creator_tg)
            identity = _telegram_identity_payload(telegram_user)
            sender_name = identity.get("display_name") or identity.get("username") or sender_name
            photo = getattr(telegram_user, "photo", None)
            file_id = getattr(photo, "big_file_id", None)
            if file_id:
                sender_photo = await bot.download_media(file_id, in_memory=True)
        except Exception as exc:
            LOGGER.warning(f"xiuxian red envelope cover fallback failed tg={creator_tg}: {exc}")
    try:
        cover = await RanksDraw.hb_test_draw(
            max(int(envelope.get("amount_total") or 0), 1),
            max(int(envelope.get("count_total") or 1), 1),
            user_pic=sender_photo,
            first_name=(sender_name or "道友")[:12],
        )
    except Exception as exc:
        LOGGER.warning(f"xiuxian red envelope generated cover failed envelope={envelope.get('id')}: {exc}")
        return None
    if isinstance(cover, BytesIO):
        cover.name = "xiuxian_red_envelope.png"
        cover.seek(0)
    return cover if isinstance(cover, BytesIO) else None


async def _red_envelope_notice_photo(envelope: dict[str, Any]) -> str | Path | BytesIO | None:
    image_source = _resolve_group_image_source(envelope.get("image_url"))
    if image_source:
        return image_source
    return await _build_red_envelope_generated_cover(envelope)


def _red_envelope_notice_text(envelope: dict[str, Any], claims: list[dict[str, Any]] | None = None) -> str:
    lines = [
        "🧧 **灵石红包**",
        f"🖼️ 封面：{_md_escape(envelope.get('cover_text') or '福运临门')}",
        f"🎛️ 模式：{_md_escape(envelope.get('mode_label') or envelope.get('mode'))}",
        f"💎 总额：`{envelope.get('amount_total')}` 灵石 / `{envelope.get('count_total')}` 个红包",
    ]
    target_tg = int(envelope.get("target_tg") or 0)
    if target_tg:
        lines.append(f"🎯 专属对象：`TG {target_tg}`")
    if claims is None:
        lines.append("👇 道友们请点击下方按钮领取红包。")
        return "\n".join(lines)
    lines.append(f"📦 剩余：`{envelope.get('remaining_amount')}` 灵石 / `{envelope.get('remaining_count')}` 个红包")
    if claims:
        claim_lines = []
        for row in claims[-5:]:
            claimant_name = row.get("name") or f"TG {row['tg']}"
            claim_lines.append(f"• {_md_escape(claimant_name)}：`{row['amount']}` 灵石")
        lines.append("📜 最近领取记录：")
        lines.extend(claim_lines)
    else:
        lines.append("📜 最近领取记录：暂无")
    return "\n".join(lines)


async def _push_quiz_task(task: dict[str, Any]) -> dict[str, Any] | None:
    chat_id = int(task.get("group_chat_id") or _main_group_chat_id() or 0)
    if not chat_id:
        return None
    text = _task_group_text(task)
    image_source = _resolve_group_image_source(task.get("image_url"))
    if image_source:
        caption, overflow = _split_photo_caption(text)
        try:
            sent = await _send_photo(
                bot,
                chat_id,
                image_source,
                caption=caption or None,
                parse_mode=RICH_TEXT_MODE,
                persistent=True,
            )
        except Exception as exc:
            LOGGER.warning(f"xiuxian task photo push fallback task={task.get('id')} chat={chat_id}: {exc}")
            sent = await _send_photo(bot, chat_id, image_source, persistent=True)
            overflow = text
        if overflow:
            await _send_message(
                bot,
                chat_id,
                overflow,
                reply_to_message_id=sent.id,
                parse_mode=RICH_TEXT_MODE,
                persistent=True,
            )
    else:
        sent = await _send_message(bot, chat_id, text, parse_mode=RICH_TEXT_MODE, persistent=True)
    return mark_task_group_message(task["id"], chat_id, sent.id)


async def _push_task_to_group(task: dict[str, Any]) -> dict[str, Any] | None:
    return await _push_quiz_task(task)


async def _safe_push_task_to_group(task: dict[str, Any]) -> tuple[dict[str, Any], str | None]:
    try:
        pushed_task = await _push_task_to_group(task)
        return pushed_task or task, None
    except Exception as exc:
        LOGGER.warning(f"xiuxian task push failed task={task.get('id')} chat={task.get('group_chat_id')}: {exc}")
        return task, "任务已创建，但群内推送失败。Telegram 当前可能波动，请稍后重试。"


async def _push_red_envelope_notice(envelope: dict[str, Any]) -> None:
    chat_id = int(envelope.get("group_chat_id") or _main_group_chat_id() or 0)
    if not chat_id:
        return
    text = _red_envelope_notice_text(envelope)
    photo = await _red_envelope_notice_photo(envelope)
    if photo:
        caption, overflow = _split_photo_caption(text)
        try:
            sent = await _send_photo(
                bot,
                chat_id,
                photo,
                caption=caption or None,
                reply_markup=_red_envelope_keyboard(envelope["id"]),
                parse_mode=RICH_TEXT_MODE,
                persistent=True,
            )
        except Exception as exc:
            LOGGER.warning(f"xiuxian red envelope photo push fallback envelope={envelope.get('id')} chat={chat_id}: {exc}")
            sent = await _send_message(
                bot,
                chat_id,
                text,
                reply_markup=_red_envelope_keyboard(envelope["id"]),
                parse_mode=RICH_TEXT_MODE,
                persistent=True,
            )
        else:
            if overflow:
                await _send_message(
                    bot,
                    chat_id,
                    overflow,
                    reply_to_message_id=sent.id,
                    parse_mode=RICH_TEXT_MODE,
                    persistent=True,
                )
    else:
        sent = await _send_message(
            bot,
            chat_id,
            text,
            reply_markup=_red_envelope_keyboard(envelope["id"]),
            parse_mode=RICH_TEXT_MODE,
            persistent=True,
        )
    LOGGER.info(f"xiuxian red envelope sent to group {chat_id}, message={sent.id}")


async def _push_group_encounter_notice(payload: dict[str, Any]) -> dict[str, Any] | None:
    template = payload.get("template") or {}
    instance = payload.get("instance") or {}
    chat_id = int(instance.get("group_chat_id") or _main_group_chat_id() or 0)
    if not chat_id:
        return None
    text = render_group_encounter_text(template, instance)
    image_source = _resolve_group_image_source(template.get("image_url"))
    if image_source:
        caption, overflow = _split_photo_caption(text)
        try:
            sent = await _send_photo(
                bot,
                chat_id,
                image_source,
                caption=caption or None,
                reply_markup=_encounter_keyboard(instance["id"], instance.get("button_text")),
                parse_mode=RICH_TEXT_MODE,
                persistent=True,
            )
        except Exception as exc:
            LOGGER.warning(f"xiuxian encounter photo push fallback id={instance.get('id')} chat={chat_id}: {exc}")
            sent = await _send_photo(bot, chat_id, image_source, persistent=True)
            overflow = text
        if overflow:
            await _send_message(
                bot,
                chat_id,
                overflow,
                reply_to_message_id=sent.id,
                reply_markup=_encounter_keyboard(instance["id"], instance.get("button_text")),
                parse_mode=RICH_TEXT_MODE,
                persistent=True,
            )
    else:
        sent = await _send_message(
            bot,
            chat_id,
            text,
            reply_markup=_encounter_keyboard(instance["id"], instance.get("button_text")),
            parse_mode=RICH_TEXT_MODE,
            persistent=True,
        )
    return mark_group_encounter_message(int(instance["id"]), int(sent.id))


async def _maybe_broadcast_craft(actor_tg: int, result: dict[str, Any]) -> None:
    if not result.get("should_broadcast"):
        return
    chat_id = _main_group_chat_id()
    if not chat_id:
        return
    item_name = ((result.get("result_item") or {}).get("name")) or "未知物品"
    actor_profile = (serialize_full_profile(actor_tg) or {}).get("profile") or {}
    await _send_message(
        bot,
        chat_id,
        "\n".join(
            [
                "🌠 **天地异象**",
                f"🧑‍🏭 {_md_escape(_duel_profile_label(actor_profile))} 成功炼成高品质物品",
                f"🎁 成品：**{_md_escape(item_name)}**",
            ]
        ),
        parse_mode=RICH_TEXT_MODE,
    )


def _admin_world_snapshot() -> dict[str, Any]:
    sects = list_sects()
    for sect in sects:
        sect["roles"] = list_sect_roles(sect["id"])
    recipes = build_recipe_catalog()
    scenes = list_scenes()
    for scene in scenes:
        scene["drops"] = list_scene_drops(scene["id"])
    return {
        "sects": sects,
        "materials": list_materials(),
        "recipes": recipes,
        "scenes": scenes,
        "encounters": list_encounter_templates(),
        "tasks": list_tasks(),
        "auctions": list_auction_items(include_inactive=True, limit=100),
        "techniques": list_techniques(),
        "titles": list_titles(),
        "achievements": list_achievements(),
        "artifact_sets": list_artifact_sets(),
        "achievement_metric_presets": ACHIEVEMENT_METRIC_PRESETS,
        "upload_permissions": list_image_upload_permissions(),
        "error_logs": list_error_logs(limit=100),
    }


def _parse_shanghai_datetime(raw: str | None) -> datetime | None:
    if not raw:
        return None
    try:
        parsed = datetime.fromisoformat(str(raw))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(SHANGHAI_TZ)


def _duel_refresh_interval(remaining_seconds: int | None = None) -> int:
    if remaining_seconds is None:
        return 10
    if remaining_seconds > 180:
        return 30
    if remaining_seconds > 60:
        return 20
    if remaining_seconds > 20:
        return 10
    return 5


def _normalize_duel_mode_arg(raw: str | None) -> str:
    value = str(raw or "").strip().lower()
    aliases = {
        "": "standard",
        "standard": "standard",
        "normal": "standard",
        "master": "master",
        "slave": "master",
        "servant": "master",
        "主仆": "master",
        "death": "death",
        "dead": "death",
        "生死": "death",
    }
    return aliases.get(value, "standard")


def _duel_mode_emoji(mode: str | None) -> str:
    return {
        "standard": "⚔️",
        "master": "⛓️",
        "death": "☠️",
    }.get(_normalize_duel_mode_arg(mode), "⚔️")


def _duel_mode_label(mode: str | None) -> str:
    return {
        "standard": "斗法",
        "master": "主仆对决",
        "death": "生死斗",
    }.get(_normalize_duel_mode_arg(mode), "斗法")


def _duel_invite_timeout_seconds(settings: dict[str, Any] | None = None) -> int:
    source = settings if isinstance(settings, dict) else get_xiuxian_settings()
    raw = source.get("duel_invite_timeout_seconds", DEFAULT_SETTINGS.get("duel_invite_timeout_seconds", 90))
    return min(max(int(raw or DEFAULT_SETTINGS.get("duel_invite_timeout_seconds", 90)), 10), 1800)


def _duel_invite_key(chat_id: Any, message_id: Any) -> tuple[int, int] | None:
    if chat_id is None or message_id is None:
        return None
    return (int(chat_id), int(message_id))


def _duel_invite_message_key(message: Any) -> tuple[int, int] | None:
    return _duel_invite_key(
        getattr(getattr(message, "chat", None), "id", None),
        getattr(message, "id", None),
    )


def _duel_invite_matches(
    invite: dict[str, Any] | None,
    *,
    challenger_tg: int,
    defender_tg: int,
    duel_mode: str,
    stake: int,
    bet_minutes: int,
) -> bool:
    if not isinstance(invite, dict):
        return False
    return (
        int(invite.get("challenger_tg") or 0) == int(challenger_tg)
        and int(invite.get("defender_tg") or 0) == int(defender_tg)
        and int(invite.get("stake") or 0) == int(stake)
        and int(invite.get("bet_minutes") or 0) == int(bet_minutes)
        and _normalize_duel_mode_arg(invite.get("duel_mode")) == _normalize_duel_mode_arg(duel_mode)
    )


def _get_pending_duel_invite(
    message: Any,
    *,
    challenger_tg: int,
    defender_tg: int,
    duel_mode: str,
    stake: int,
    bet_minutes: int,
) -> tuple[tuple[int, int] | None, dict[str, Any] | None]:
    key = _duel_invite_message_key(message)
    if key is None:
        return None, None
    invite = PENDING_DUEL_INVITES.get(key)
    if not _duel_invite_matches(
        invite,
        challenger_tg=challenger_tg,
        defender_tg=defender_tg,
        duel_mode=duel_mode,
        stake=stake,
        bet_minutes=bet_minutes,
    ):
        return key, None
    return key, invite


def _cancel_pending_duel_invite_task(task: asyncio.Task | None) -> None:
    if task is None or task.done() or task is asyncio.current_task():
        return
    task.cancel()


def _pop_pending_duel_invite(key: tuple[int, int] | None) -> dict[str, Any] | None:
    if key is None:
        return None
    invite = PENDING_DUEL_INVITES.pop(key, None)
    if invite:
        _cancel_pending_duel_invite_task(invite.get("task"))
    return invite


def _format_duel_invite_footer(timeout_seconds: int, bet_minutes: int) -> str:
    return "\n".join(
        [
            "",
            f"⏳ 请应战者在 `{timeout_seconds}` 秒内作出回应，超时将自动撤销邀请。",
            f"🎲 接受后将开放 `{bet_minutes}` 分钟押注。",
            "🛑 发起者可点击下方按钮主动撤回本场邀请。",
        ]
    )


def _format_duel_invite_closed_text(mode: str, headline: str, detail_lines: list[str]) -> str:
    return "\n".join([f"{_duel_mode_emoji(mode)} **{headline}**", "", *detail_lines])


async def _expire_duel_invite(chat_id: int, message_id: int, duel_mode: str, timeout_seconds: int) -> None:
    try:
        await asyncio.sleep(max(int(timeout_seconds or 0), 1))
    except asyncio.CancelledError:
        return

    key = _duel_invite_key(chat_id, message_id)
    invite = _pop_pending_duel_invite(key)
    if invite is None:
        return

    try:
        await _edit_message_text(
            bot,
            chat_id,
            message_id,
            _format_duel_invite_closed_text(
                duel_mode,
                f"{_duel_mode_label(duel_mode)}邀请已超时撤销",
                [
                    f"对方未在 `{timeout_seconds}` 秒内应战，本场邀请已自动失效。",
                    "📭 发起者可重新发起新的挑战。",
                ],
            ),
            persistent=True,
            reply_markup=None,
            parse_mode=RICH_TEXT_MODE,
        )
    except Exception as exc:
        LOGGER.warning(f"xiuxian duel invite timeout update failed chat={chat_id} message={message_id}: {exc}")


def _register_pending_duel_invite(
    message: Any,
    *,
    challenger_tg: int,
    defender_tg: int,
    duel_mode: str,
    stake: int,
    bet_minutes: int,
    timeout_seconds: int,
) -> None:
    key = _duel_invite_message_key(message)
    if key is None:
        return
    _pop_pending_duel_invite(key)
    PENDING_DUEL_INVITES[key] = {
        "challenger_tg": int(challenger_tg),
        "defender_tg": int(defender_tg),
        "duel_mode": _normalize_duel_mode_arg(duel_mode),
        "stake": int(stake),
        "bet_minutes": int(bet_minutes),
        "timeout_seconds": int(timeout_seconds),
        "task": asyncio.create_task(
            _expire_duel_invite(
                key[0],
                key[1],
                duel_mode=_normalize_duel_mode_arg(duel_mode),
                timeout_seconds=int(timeout_seconds),
            )
        ),
    }


def _duel_log_emoji(kind: str | None) -> str:
    return {
        "opening": "🌀",
        "round": "⏱️",
        "dot": "🔥",
        "dodge": "💨",
        "shield": "🛡️",
        "state": "📊",
        "finish": "🏁",
    }.get(str(kind or "").strip(), "⚔️")


def _latest_visible_duel_statuses(result: dict[str, Any], visible_count: int) -> tuple[dict[str, Any], dict[str, Any]]:
    challenger_status: dict[str, Any] = {}
    defender_status: dict[str, Any] = {}
    battle_log = list(result.get("battle_log") or [])
    shown = min(max(int(visible_count or 0), 0), len(battle_log))
    for row in reversed(battle_log[:shown]):
        if not challenger_status and isinstance(row.get("challenger_status"), dict):
            challenger_status = dict(row.get("challenger_status") or {})
        if not defender_status and isinstance(row.get("defender_status"), dict):
            defender_status = dict(row.get("defender_status") or {})
        if challenger_status and defender_status:
            break
    return challenger_status, defender_status


def _duel_snapshot_line(label: str, snapshot: dict[str, Any], status: dict[str, Any] | None = None) -> str:
    stats = snapshot.get("stats") or {}
    status = status or {}
    qi_blood = int(status.get("hp") or stats.get("qi_blood") or 0)
    max_qi_blood = int(status.get("max_hp") or stats.get("qi_blood") or 0)
    true_yuan = int(status.get("mp") or stats.get("true_yuan") or 0)
    max_true_yuan = int(status.get("max_mp") or stats.get("true_yuan") or 0)
    effect_text = str(status.get("effects_text") or "无")
    return (
        f"{label} {_md_escape(str(snapshot.get('name') or '道友'))}"
        f" ｜ 战力 `{int(round(snapshot.get('power') or 0))}`"
        f" ｜ 气血 `{qi_blood}/{max_qi_blood}`"
        f" ｜ 真元 `{true_yuan}/{max_true_yuan}`"
        f" ｜ 状态 {_md_escape(effect_text)}"
        f" ｜ 胜率 `{float(snapshot.get('win_rate') or 0):.1f}%`"
    )


def _format_duel_stream_text(result: dict[str, Any], visible_count: int) -> str:
    challenger = (result.get("challenger") or {}).get("profile") or {}
    defender = (result.get("defender") or {}).get("profile") or {}
    challenger_snapshot = result.get("challenger_snapshot") or {}
    defender_snapshot = result.get("defender_snapshot") or {}
    battle_log = list(result.get("battle_log") or [])
    total = len(battle_log)
    shown = min(max(int(visible_count or 0), 0), total)
    challenger_status, defender_status = _latest_visible_duel_statuses(result, shown)
    lines = [
        "⚔️ **斗法直播**",
        f"对局：{_md_escape(_duel_profile_label(challenger))} vs {_md_escape(_duel_profile_label(defender))}",
        f"进度：`{shown}/{total}` 条战报",
        "战况：灵压交错，斗法台正在实时回传气机波动。",
    ]
    stake = int(result.get("stake") or 0)
    if stake > 0:
        lines.append(f"赌斗：每人 `{stake}` 灵石")
    lines.extend(
        [
            "",
            _duel_snapshot_line("🟥", challenger_snapshot, challenger_status),
            _duel_snapshot_line("🟦", defender_snapshot, defender_status),
            "",
        ]
    )
    for row in battle_log[:shown]:
        prefix = _duel_log_emoji(row.get("kind"))
        round_no = int(row.get("round") or 0)
        round_text = f"`第{round_no}回合` " if round_no > 0 and row.get("kind") != "round" else ""
        lines.append(f"{prefix} {round_text}{_md_escape(row.get('text') or '')}")
    if shown < total:
        lines.extend(["", "⏳ 场中仍有余波翻涌，法宝与符光还在互相撕扯，下一轮战报即将显化……"])
    else:
        lines.extend(["", f"🏁 **胜负已分**", _md_escape(str(result.get('summary') or '斗法结束。'))])
    return "\n".join(lines)


async def _stream_duel_battle(message, result: dict[str, Any]) -> None:
    battle_log = list(result.get("battle_log") or [])
    if not battle_log:
        return
    step = max((len(battle_log) + 5) // 6, 3)
    shown = min(step, len(battle_log))
    while True:
        try:
            await _edit_text(
                message,
                _format_duel_stream_text(result, shown),
                persistent=True,
                parse_mode=RICH_TEXT_MODE,
            )
        except Exception as exc:
            LOGGER.warning(f"xiuxian duel stream update failed: {exc}")
            return
        if shown >= len(battle_log):
            return
        await asyncio.sleep(3)
        shown = min(shown + step, len(battle_log))


async def _maybe_refresh_duel_bet_message(pool_id: int, message, remaining_seconds: int | None = None, force: bool = False) -> bool:
    now_monotonic = time.monotonic()
    interval = _duel_refresh_interval(remaining_seconds)
    last_refresh = DUEL_MESSAGE_REFRESH_CACHE.get(pool_id, 0.0)
    if not force and now_monotonic - last_refresh < interval:
        return False
    try:
        await _edit_text(
            message,
            format_duel_bet_board(pool_id),
            reply_markup=_duel_bet_keyboard(pool_id),
            persistent=True,
            parse_mode=RICH_TEXT_MODE,
        )
    except Exception:
        return False
    DUEL_MESSAGE_REFRESH_CACHE[pool_id] = now_monotonic
    return True


def register_bot(bot_instance) -> None:
    _ensure_xiuxian_bot_commands()
    _schedule_command_refresh(bot_instance)
    _schedule_active_auction_finalize_tasks()

    async def refresh_duel_bet_countdown(pool_id: int, message, bets_close_at: str | None) -> None:
        close_at = _parse_shanghai_datetime(bets_close_at)
        if close_at is None:
            return
        while True:
            remaining = max(int((close_at - datetime.now(SHANGHAI_TZ)).total_seconds()), 0)
            if remaining <= 0:
                break
            await asyncio.sleep(min(_duel_refresh_interval(remaining), remaining))
            remaining = max(int((close_at - datetime.now(SHANGHAI_TZ)).total_seconds()), 0)
            if remaining <= 0:
                break
            await _maybe_refresh_duel_bet_message(pool_id, message, remaining_seconds=remaining)

    async def finalize_duel_after_betting(
        pool_id: int,
        challenger_tg: int,
        defender_tg: int,
        stake: int,
        duel_mode: str,
        message,
        bets_close_at: str | None,
    ) -> None:
        close_at = _parse_shanghai_datetime(bets_close_at)
        if close_at is not None:
            await asyncio.sleep(max((close_at - datetime.now(SHANGHAI_TZ)).total_seconds(), 0))
        else:
            await asyncio.sleep(120)
        try:
            result = resolve_duel(challenger_tg, defender_tg, stake, duel_mode=duel_mode)
            bet_settlement = settle_duel_bet_pool(pool_id, result["winner_tg"])
            DUEL_MESSAGE_REFRESH_CACHE.pop(pool_id, None)
            total_pages = _duel_settlement_total_pages(bet_settlement)
            if total_pages > 1:
                DUEL_SETTLEMENT_CACHE[pool_id] = {
                    "result": result,
                    "bet_settlement": bet_settlement,
                }
            else:
                DUEL_SETTLEMENT_CACHE.pop(pool_id, None)
            try:
                try:
                    await _edit_text(
                        message,
                        "⏳ **赌池已封盘**\n\n斗法推演开始，战报将逐条显化……",
                        persistent=True,
                        parse_mode=RICH_TEXT_MODE,
                    )
                except Exception as exc:
                    LOGGER.warning(f"xiuxian duel stream opening update failed: {exc}")
                await _stream_duel_battle(message, result)
                await _edit_text(
                    message,
                    format_duel_settlement_text(
                        result,
                        bet_settlement,
                        page=1,
                        page_size=DUEL_SETTLEMENT_PAGE_SIZE,
                    ),
                    reply_markup=_duel_settlement_keyboard(pool_id, 1, total_pages),
                    parse_mode=RICH_TEXT_MODE,
                )
            except Exception as exc:
                LOGGER.warning(f"xiuxian duel settlement message update failed: {exc}")
            await _notify_duel_participants(result)
            await _notify_duel_bettors(result, bet_settlement)
            await _notify_achievement_unlocks(result.get("achievement_unlocks"))
        except ValueError as exc:
            DUEL_MESSAGE_REFRESH_CACHE.pop(pool_id, None)
            DUEL_SETTLEMENT_CACHE.pop(pool_id, None)
            try:
                cancel_duel_bet_pool(pool_id, str(exc))
            except Exception as refund_exc:
                LOGGER.warning(f"xiuxian duel refund failed: {refund_exc}")
            try:
                await _edit_text(
                    message,
                    f"⚠️ **赌斗已取消**\n\n{_md_escape(str(exc))}\n\n围观押注若已扣除，现已原路退回。",
                    persistent=True,
                    parse_mode=RICH_TEXT_MODE,
                )
            except Exception as message_exc:
                LOGGER.warning(f"xiuxian duel cancel message update failed: {message_exc}")
        except Exception as exc:
            DUEL_MESSAGE_REFRESH_CACHE.pop(pool_id, None)
            DUEL_SETTLEMENT_CACHE.pop(pool_id, None)
            try:
                cancel_duel_bet_pool(pool_id, str(exc))
            except Exception as refund_exc:
                LOGGER.warning(f"xiuxian duel finalize fallback refund failed: {refund_exc}")
            LOGGER.warning(f"xiuxian duel finalize failed: {exc}")
            try:
                await _edit_text(
                    message,
                    "⚠️ **赌斗结算异常**\n\n本场斗法未能正常落盘，赌池已自动撤销，已参与押注的灵石会原路退回。",
                    persistent=True,
                    parse_mode=RICH_TEXT_MODE,
                )
            except Exception as message_exc:
                LOGGER.warning(f"xiuxian duel finalize error message update failed: {message_exc}")

    @bot_instance.on_callback_query(filters.regex(r"^xiuxian:entry$"))
    async def xiuxian_entry(_, call):
        await callAnswer(call, "正在展开仙途卷轴……")
        await _edit_text(
            call.message,
            "是否愿意踏入仙途？确认后会抽取灵根，并为你建立专属修仙档案。",
            reply_markup=xiuxian_confirm_keyboard(),
        )

    @bot_instance.on_callback_query(filters.regex(r"^xiuxian:return$"))
    async def xiuxian_return(_, call):
        profile = serialize_full_profile(call.from_user.id)
        await callAnswer(call, "已回到修仙主页。")
        await _edit_text(call.message, _format_profile_text(profile), reply_markup=xiuxian_profile_keyboard(), parse_mode=RICH_TEXT_MODE)

    @bot_instance.on_callback_query(filters.regex(r"^xiuxian:confirm$"))
    async def xiuxian_confirm(_, call):
        profile = init_path_for_user(call.from_user.id)
        create_foundation_pill_for_user_if_missing(call.from_user.id)
        await callAnswer(call, "仙途已启，命格已定。")
        await _edit_text(call.message, _format_profile_text(profile), reply_markup=xiuxian_profile_keyboard(), parse_mode=RICH_TEXT_MODE)

    @bot_instance.on_callback_query(filters.regex(r"^xiuxian:train$"))
    async def xiuxian_train(_, call):
        try:
            result = practice_for_user(call.from_user.id)
            upgraded = ""
            if result["upgraded_layers"]:
                upgraded = "\n层数提升：" + "、".join(f"{layer}层" for layer in result["upgraded_layers"])
            growth_text = _format_attribute_growth_text(result.get("attribute_growth"))
            growth_line = f"\n{growth_text}" if growth_text else ""
            text = (
                f"吐纳修炼完成。\n"
                f"本次获得：修为 +{result['gain']}、灵石 +{result['stone_gain']}"
                f"{upgraded}{growth_line}\n\n"
                f"{_format_profile_text(result['profile'])}"
            )
            await callAnswer(call, "吐纳已完成。")
            await _edit_text(call.message, text, reply_markup=xiuxian_profile_keyboard(), parse_mode=RICH_TEXT_MODE)
        except Exception as exc:
            await callAnswer(call, str(exc), True)

    @bot_instance.on_callback_query(filters.regex(r"^xiuxian:break$"))
    async def xiuxian_break(_, call):
        try:
            result = breakthrough_for_user(call.from_user.id, use_pill=False)
            text = (
                f"突破掷点：{result['roll']} / 当前成功率 {result['success_rate']}%\n"
                f"{'突破成功，气机贯通。' if result['success'] else '突破失败，灵力回落。'}\n\n"
                f"{_format_profile_text(result['profile'])}"
            )
            await callAnswer(call, "突破结果已出。")
            await _edit_text(call.message, text, reply_markup=xiuxian_profile_keyboard(), parse_mode=RICH_TEXT_MODE)
        except Exception as exc:
            await callAnswer(call, str(exc), True)

    @bot_instance.on_callback_query(filters.regex(r"^xiuxian:noop$"))
    async def xiuxian_noop(_, call):
        await callAnswer(call, "这个按钮暂时还没有开放。")

    @bot_instance.on_callback_query(filters.regex(r"^xiuxian:settlement:(\d+):(\d+)$"))
    async def xiuxian_duel_settlement_callback(_, call):
        pool_id = int(call.matches[0].group(1))
        requested_page = int(call.matches[0].group(2))
        cached = DUEL_SETTLEMENT_CACHE.get(pool_id)
        if not cached:
            return await callAnswer(call, "这份结算记录已过期。", True)
        bet_settlement = cached["bet_settlement"]
        total_pages = _duel_settlement_total_pages(bet_settlement)
        page = min(max(requested_page, 1), total_pages)
        await _edit_text(
            call.message,
            format_duel_settlement_text(
                cached["result"],
                bet_settlement,
                page=page,
                page_size=DUEL_SETTLEMENT_PAGE_SIZE,
            ),
            reply_markup=_duel_settlement_keyboard(pool_id, page, total_pages),
            parse_mode=RICH_TEXT_MODE,
        )
        await callAnswer(call, f"已切换到第 {page} 页。")

    @bot_instance.on_callback_query(filters.regex(r"^xiuxian:rank:(stone|realm|artifact):(\d+)$"))
    async def xiuxian_rank_callback(_, call):
        kind, page = call.matches[0].group(1), int(call.matches[0].group(2))
        result = build_leaderboard(kind, page)
        await _edit_text(
            call.message,
            format_leaderboard_text(result),
            reply_markup=leaderboard_keyboard(result["kind"], result["page"], result["total_pages"]),
            parse_mode=RICH_TEXT_MODE,
        )
        await callAnswer(call, "排行榜已刷新。")

    @bot_instance.on_message(filters.command(["xiuxian"], prefixes) & filters.private)
    async def xiuxian_command(_, msg):
        try:
            profile = serialize_full_profile(msg.from_user.id)
            if not profile["profile"]["consented"]:
                await _reply_text(
                    msg,
                    _xiuxian_basic_guide_text(False),
                    reply_markup=xiuxian_confirm_keyboard(),
                )
                return

            await _reply_text(
                msg,
                _format_profile_text(profile) + "\n\n" + _xiuxian_basic_guide_text(True),
                reply_markup=xiuxian_profile_keyboard(),
                parse_mode=RICH_TEXT_MODE,
            )
        finally:
            await _delete_user_command_message(msg)

    @bot_instance.on_message(filters.command(["help"], prefixes))
    async def xiuxian_help_command(_, msg):
        try:
            help_text = (
                "可用命令如下：\n"
                "/start - 打开主面板与功能入口\n"
                "/help - 查看命令帮助\n"
                "/xiuxian - 打开修仙总览\n"
                "/xiuxian_me - 在群里展示自己的修仙信息\n"
                "/xiuxian_rank [stone|realm|artifact] [页码] - 查看修仙排行榜\n"
                "/train - 群里直接完成一次吐纳修炼\n"
                "/work [委托名] - 群里直接承接一项灵石委托\n"
                "/salary - 群里领取一次宗门俸禄\n"
                "/duel [赌注] - 回复某位道友发起斗法\n"
                "/deathduel [赌注] - 回复某位道友发起生死斗\n"
                "/servitudeduel [赌注] - 回复某位道友发起奴役斗\n"
                "/seek - 回复某位道友探查信息\n"
                "/rob - 回复某位道友发起抢劫\n"
                "/gift <灵石数量> - 回复某位道友直接赠石\n"
                "/gift <TGID> <灵石数量> - 旧版 TGID 赠石写法\n"
                "/allow_upload - 主人回复用户后授予上传权限\n"
                "/remove_upload - 主人回复用户后移除上传权限\n"
                f"\n{_xiuxian_basic_guide_text(True)}\n"
                "其余修仙操作、任务、探索、红包、宗门与店铺功能请直接从 Mini App 进入。"
            )
            await _reply_text(msg, help_text)
        finally:
            await _delete_user_command_message(msg)

    @bot_instance.on_message(filters.command(["xiuxian_me", "xiuxian_info"], prefixes) & filters.chat(group))
    async def xiuxian_me_command(_, msg):
        try:
            if not _register_command_dispatch(msg, "xiuxian_me"):
                LOGGER.warning(
                    f"xiuxian command duplicate skipped chat={getattr(getattr(msg, 'chat', None), 'id', None)} "
                    f"message={getattr(msg, 'id', None)} command=xiuxian_me"
                )
                return
            if msg.from_user is None:
                return
            LOGGER.info(
                f"xiuxian me command received chat={getattr(getattr(msg, 'chat', None), 'id', None)} "
                f"actor={getattr(getattr(msg, 'from_user', None), 'id', None)}"
            )
            profile = serialize_full_profile(msg.from_user.id)
            if not profile["profile"]["consented"]:
                return await _reply_text(msg, "你还没有踏入仙途，先私聊机器人点击 /xiuxian 入道。")
            fallback_name = msg.from_user.first_name or f"TG {msg.from_user.id}"
            await _reply_text(msg, _format_group_profile_showcase(profile, fallback_name), parse_mode=RICH_TEXT_MODE)
        finally:
            await _delete_user_command_message(msg)

    @bot_instance.on_message(filters.command(["xiuxian_rank"], prefixes) & filters.chat(group))
    async def xiuxian_rank_command(_, msg):
        try:
            if not _register_command_dispatch(msg, "xiuxian_rank"):
                LOGGER.warning(
                    f"xiuxian command duplicate skipped chat={getattr(getattr(msg, 'chat', None), 'id', None)} "
                    f"message={getattr(msg, 'id', None)} command=xiuxian_rank"
                )
                return
            kind_alias = {
                "stone": "stone",
                "stones": "stone",
                "stone_rank": "stone",
                "realm": "realm",
                "realms": "realm",
                "realm_rank": "realm",
                "artifact": "artifact",
                "artifacts": "artifact",
                "artifact_rank": "artifact",
            }
            kind = "stone"
            page = 1
            if len(msg.command) > 1:
                kind = kind_alias.get(str(msg.command[1]).lower(), kind_alias.get(str(msg.command[1]), "stone"))
            if len(msg.command) > 2:
                try:
                    page = max(int(msg.command[2]), 1)
                except ValueError:
                    page = 1
            result = build_leaderboard(kind, page)
            await _reply_text(
                msg,
                format_leaderboard_text(result),
                reply_markup=leaderboard_keyboard(result["kind"], result["page"], result["total_pages"]),
                parse_mode=RICH_TEXT_MODE,
            )
        finally:
            await _delete_user_command_message(msg)

    @bot_instance.on_message(filters.command(["train", "practice"], prefixes) & filters.chat(group))
    async def xiuxian_train_group_command(_, msg):
        try:
            if not _register_command_dispatch(msg, "train"):
                LOGGER.warning(
                    f"xiuxian command duplicate skipped chat={getattr(getattr(msg, 'chat', None), 'id', None)} "
                    f"message={getattr(msg, 'id', None)} command=train"
                )
                return
            actor = await _require_message_user(msg, action_text="吐纳修炼")
            if actor is None:
                return
            result = practice_for_user(actor.id)
            lines = [f"吐纳完成，修为 +{result['gain']}，灵石 +{result['stone_gain']}。"]
            if result.get("upgraded_layers"):
                lines.append("层数提升：" + "、".join(f"{layer}层" for layer in result["upgraded_layers"]))
            growth_text = _format_attribute_growth_text(result.get("attribute_growth"))
            if growth_text:
                lines.append(growth_text)
            await _reply_text(msg, "\n".join(lines), quote=True)
        except Exception as exc:
            await _reply_text(msg, str(exc) or "吐纳修炼失败，请稍后重试。", quote=True)
        finally:
            await _delete_user_command_message(msg)

    @bot_instance.on_message(filters.command(["work"], prefixes) & filters.chat(group))
    async def xiuxian_work_group_command(_, msg):
        try:
            if not _register_command_dispatch(msg, "work"):
                LOGGER.warning(
                    f"xiuxian command duplicate skipped chat={getattr(getattr(msg, 'chat', None), 'id', None)} "
                    f"message={getattr(msg, 'id', None)} command=work"
                )
                return
            actor = await _require_message_user(msg, action_text="承接灵石委托")
            if actor is None:
                return
            requested_key = _normalize_commission_command_key(msg.command[1] if len(msg.command or []) > 1 else None)
            bundle = _full_bundle(actor.id)
            selected, _ = _select_group_commission(bundle, requested_key=requested_key)
            if selected is None or not selected.get("available"):
                return await _reply_text(msg, _commission_selection_error(bundle, requested_key=requested_key), quote=True)
            result = claim_spirit_stone_commission(actor.id, str(selected.get("key") or ""))
            commission = result.get("commission") or {}
            lines = [
                f"{commission.get('name') or selected.get('name') or '灵石委托'}完成，灵石 +{commission.get('stone_gain', 0)}，修为 +{commission.get('cultivation_gain', 0)}。"
            ]
            detail = str(commission.get("detail") or "").strip()
            if detail:
                lines.append(detail)
            growth_text = _format_attribute_growth_text(commission.get("attribute_growth"))
            if growth_text:
                lines.append(growth_text)
            if result.get("upgraded_layers"):
                lines.append("层数提升：" + "、".join(f"{layer}层" for layer in result["upgraded_layers"]))
            await _reply_text(msg, "\n".join(lines), quote=True)
        except Exception as exc:
            await _reply_text(msg, str(exc) or "灵石委托结算失败，请稍后重试。", quote=True)
        finally:
            await _delete_user_command_message(msg)

    @bot_instance.on_message(filters.command(["salary"], prefixes) & filters.chat(group))
    async def xiuxian_salary_group_command(_, msg):
        try:
            if not _register_command_dispatch(msg, "salary"):
                LOGGER.warning(
                    f"xiuxian command duplicate skipped chat={getattr(getattr(msg, 'chat', None), 'id', None)} "
                    f"message={getattr(msg, 'id', None)} command=salary"
                )
                return
            actor = await _require_message_user(msg, action_text="领取宗门俸禄")
            if actor is None:
                return
            result = claim_sect_salary_for_user(actor.id)
            role = result.get("role") or {}
            role_name = str(role.get("role_name") or "宗门职位").strip()
            await _reply_text(
                msg,
                f"宗门俸禄已到账，本次领取 {result.get('salary', 0)} 灵石。当前身份：{role_name}。",
                quote=True,
            )
        except Exception as exc:
            await _reply_text(msg, str(exc) or "领取宗门俸禄失败，请稍后重试。", quote=True)
        finally:
            await _delete_user_command_message(msg)

    @bot_instance.on_message(filters.command(list(DUEL_COMMAND_MODES.keys()), prefixes) & filters.chat(group))
    async def xiuxian_duel_command(_, msg):
        try:
            command_name = str((msg.command or [""])[0]).split("@", 1)[0].strip().lower()
            command_args = [str(item) for item in (msg.command[1:] if len(msg.command or []) > 1 else [])]
            if not _register_command_dispatch(msg, command_name):
                LOGGER.warning(
                    f"xiuxian command duplicate skipped chat={getattr(getattr(msg, 'chat', None), 'id', None)} "
                    f"message={getattr(msg, 'id', None)} command={command_name}"
                )
                return
            duel_mode = DUEL_COMMAND_MODES.get(command_name)
            if duel_mode is None:
                return
            LOGGER.info(
                f"xiuxian duel command received chat={getattr(getattr(msg, 'chat', None), 'id', None)} "
                f"actor={getattr(getattr(msg, 'from_user', None), 'id', None)} "
                f"cmd={command_name} reply_to={getattr(getattr(getattr(msg, 'reply_to_message', None), 'from_user', None), 'id', None)}"
            )
            actor = await _require_message_user(msg, action_text="发起斗法")
            if actor is None:
                return
            settings = get_xiuxian_settings()
            bet_minutes = int(settings.get("duel_bet_minutes", 2) or 2)
            invite_timeout_seconds = _duel_invite_timeout_seconds(settings)
            stake = 0
            numeric_args: list[str] = []
            for arg in command_args:
                raw = str(arg or "").strip()
                if not raw:
                    continue
                if not re.fullmatch(r"-?\d+", raw):
                    if command_name == "duel":
                        return await _reply_text(
                            msg,
                            "普通斗法请使用 /duel [赌注] [下注分钟]；生死斗请用 /deathduel，奴役斗请用 /servitudeduel。",
                            quote=True,
                        )
                    return await _reply_text(msg, "赌注和下注时长必须填写整数。", quote=True)
                numeric_args.append(raw)
            if numeric_args:
                try:
                    stake = max(int(numeric_args[0]), 0)
                    if len(numeric_args) > 1:
                        bet_minutes = max(min(int(numeric_args[1]), 15), 1)
                except ValueError:
                    return await _reply_text(msg, "赌注和下注时长必须填写整数。", quote=True)
            if msg.reply_to_message is None or msg.reply_to_message.from_user is None:
                return await _reply_text(msg, "请先回复一位目标道友，再发起斗法邀请。", quote=True)
            if msg.reply_to_message.from_user.id == actor.id:
                return await _reply_text(msg, "你不能自己和自己斗法。", quote=True)

            try:
                duel = compute_duel_odds(actor.id, msg.reply_to_message.from_user.id, duel_mode=duel_mode)
                assert_duel_stake_affordable(duel["challenger"]["profile"], duel["defender"]["profile"], stake)
                preview = generate_duel_preview_text(duel, stake, duel_mode=duel_mode) + _format_duel_invite_footer(
                    invite_timeout_seconds,
                    bet_minutes,
                )
                sent = await _reply_text(
                    msg,
                    preview,
                    reply_markup=duel_keyboard(actor.id, msg.reply_to_message.from_user.id, stake, bet_minutes, duel_mode=duel_mode),
                    persistent=True,
                    parse_mode=RICH_TEXT_MODE,
                )
                _register_pending_duel_invite(
                    sent,
                    challenger_tg=actor.id,
                    defender_tg=msg.reply_to_message.from_user.id,
                    duel_mode=duel_mode,
                    stake=stake,
                    bet_minutes=bet_minutes,
                    timeout_seconds=invite_timeout_seconds,
                )
            except Exception as exc:
                await _reply_text(msg, str(exc), quote=True)
        finally:
            await _delete_user_command_message(msg)

    @bot_instance.on_callback_query(filters.regex(r"^xiuxian:duel:(accept|reject|cancel):([a-z_]+):(\d+):(\d+):(\d+):(\d+)$"))
    async def xiuxian_duel_callback(_, call):
        action = call.matches[0].group(1)
        duel_mode = _normalize_duel_mode_arg(call.matches[0].group(2))
        challenger_tg = int(call.matches[0].group(3))
        defender_tg = int(call.matches[0].group(4))
        stake = int(call.matches[0].group(5))
        bet_minutes = int(call.matches[0].group(6))

        key, invite = _get_pending_duel_invite(
            call.message,
            challenger_tg=challenger_tg,
            defender_tg=defender_tg,
            duel_mode=duel_mode,
            stake=stake,
            bet_minutes=bet_minutes,
        )
        if invite is None:
            return await callAnswer(call, "这场斗法邀请已失效或已被处理。", True)

        if action == "cancel":
            if call.from_user.id != challenger_tg:
                return await callAnswer(call, "只有发起斗法的一方才能主动撤销邀请。", True)
            _pop_pending_duel_invite(key)
            await _edit_text(
                call.message,
                _format_duel_invite_closed_text(
                    duel_mode,
                    f"{_duel_mode_label(duel_mode)}邀请已主动撤销",
                    [
                        "🛑 发起者已收回这场挑战。",
                        "📭 若仍想开战，可重新发起新的斗法邀请。",
                    ],
                ),
                persistent=True,
                reply_markup=None,
                parse_mode=RICH_TEXT_MODE,
            )
            return await callAnswer(call, "斗法邀请已撤销。")

        if call.from_user.id != defender_tg:
            return await callAnswer(call, "只有被邀请的应战者才能处理这场斗法。", True)

        if action == "reject":
            _pop_pending_duel_invite(key)
            await _edit_text(
                call.message,
                _format_duel_invite_closed_text(
                    duel_mode,
                    f"{_duel_mode_label(duel_mode)}邀请已被拒绝",
                    [
                        "🚫 应战者选择了拒绝，本场挑战到此作废。",
                        "📭 发起者可稍后重新发起新的邀请。",
                    ],
                ),
                persistent=True,
                reply_markup=None,
                parse_mode=RICH_TEXT_MODE,
            )
            return await callAnswer(call, "斗法已取消。")

        _pop_pending_duel_invite(key)
        try:
            pool = create_duel_bet_pool_for_duel(
                challenger_tg=challenger_tg,
                defender_tg=defender_tg,
                stake=stake,
                duel_mode=duel_mode,
                bet_minutes=bet_minutes,
                group_chat_id=call.message.chat.id,
                duel_message_id=call.message.id,
            )
            sent = await _edit_text(
                call.message,
                f"{_duel_mode_emoji(duel_mode)} {_duel_mode_label(duel_mode)}邀请已接受，押注通道开放 {pool.get('bet_minutes', bet_minutes)} 分钟。\n\n" + format_duel_bet_board(pool["id"]),
                reply_markup=_duel_bet_keyboard(pool["id"]),
                persistent=True,
                parse_mode=RICH_TEXT_MODE,
            )
            DUEL_MESSAGE_REFRESH_CACHE[pool["id"]] = time.monotonic()
            try:
                update_duel_bet_pool_message(pool["id"], getattr(sent, "id", call.message.id))
            except Exception as exc:
                LOGGER.warning(f"xiuxian duel bet message update failed: {exc}")
            await callAnswer(call, "斗法已开始，押注倒计时启动。")
            asyncio.create_task(refresh_duel_bet_countdown(pool["id"], sent, pool.get("bets_close_at")))
            asyncio.create_task(finalize_duel_after_betting(pool["id"], challenger_tg, defender_tg, stake, duel_mode, sent, pool.get("bets_close_at")))
        except Exception as exc:
            try:
                await _edit_text(
                    call.message,
                    f"⚠️ **{_duel_mode_label(duel_mode)}邀请已取消**\n\n{_md_escape(str(exc))}",
                    persistent=True,
                    reply_markup=None,
                    parse_mode=RICH_TEXT_MODE,
                )
            except Exception as message_exc:
                LOGGER.warning(f"xiuxian duel accept error message update failed: {message_exc}")
            await callAnswer(call, str(exc), True)

    @bot_instance.on_callback_query(filters.regex(r"^xiuxian:bet:(\d+):(challenger|defender):(\d+)$"))
    async def xiuxian_duel_bet_callback(_, call):
        pool_id = int(call.matches[0].group(1))
        side = call.matches[0].group(2)
        amount = int(call.matches[0].group(3))
        try:
            place_duel_bet(pool_id, call.from_user.id, side, amount)
            refreshed = await _maybe_refresh_duel_bet_message(pool_id, call.message)
            answer_text = f"已下注 {amount} 灵石。"
            if not refreshed:
                answer_text += " 赌池信息将稍后自动刷新。"
            await callAnswer(call, answer_text)
        except Exception as exc:
            await callAnswer(call, str(exc), True)

    @bot_instance.on_callback_query(filters.regex(r"^xiuxian:auction:(bid|buyout):(\d+)$"))
    async def xiuxian_auction_callback(_, call):
        action = str(call.matches[0].group(1) or "bid").strip().lower()
        auction_id = int(call.matches[0].group(2))
        bidder = getattr(call, "from_user", None)
        if bidder is None:
            return await callAnswer(call, "当前无法识别你的 TG 身份。", True)

        bidder_name = " ".join(
            part for part in [getattr(bidder, "first_name", None), getattr(bidder, "last_name", None)] if part
        ).strip()
        if not bidder_name:
            bidder_name = f"@{bidder.username}" if getattr(bidder, "username", None) else f"TG {bidder.id}"

        try:
            result = place_auction_bid(
                bidder.id,
                auction_id,
                bidder_name=bidder_name,
                use_buyout=action == "buyout",
            )
        except Exception as exc:
            message = str(exc) or "竞拍失败"
            if "拍卖已经结束" in message:
                finalized = finalize_auction_listing(auction_id, force=True)
                if finalized and str(finalized.get("result") or "") not in {"noop", ""}:
                    await _finalize_auction_flow(finalized)
                return await callAnswer(call, "这场拍卖已经结束，面板已尝试刷新。", True)
            return await callAnswer(call, message, True)

        auction = result.get("auction") or {}
        outcome = str(result.get("result") or "")
        if outcome == "bid":
            await _refresh_auction_group_message(auction)
            current_price = int(auction.get("current_display_price_stone") or 0)
            return await callAnswer(call, f"已出价，当前价格 {current_price} 灵石。")

        if outcome == "sold":
            await _finalize_auction_flow(result)
            return await callAnswer(call, "拍卖已成交。")

        await callAnswer(call, "拍卖状态已更新。")

    @bot_instance.on_message(filters.text & filters.group & ~filters.regex(r"^[\\/!\\.，。]"))
    async def xiuxian_group_quiz_answer(_, msg):
        if msg.from_user is None or getattr(msg.from_user, "is_bot", False):
            return
        if not getattr(msg, "text", None):
            return
        try:
            result = resolve_quiz_answer(msg.chat.id, msg.from_user.id, msg.text)
        except Exception as exc:
            LOGGER.warning(f"xiuxian quiz resolve failed: {exc}")
            return
        if not result:
            return

        task = result["task"]
        reward = result["reward"] or {}
        reward_lines = []
        if int(reward.get("reward_stone") or 0):
            reward_lines.append(f"{reward['reward_stone']} 灵石")
        if reward.get("reward_item"):
            reward_lines.append(
                f"{reward['reward_item'].get('quantity', 1)} 个{(reward['reward_item'].get('artifact') or reward['reward_item'].get('pill') or reward['reward_item'].get('talisman') or reward['reward_item'].get('material') or {}).get('name', '物品')}"
            )
        reward_text = "、".join(reward_lines) if reward_lines else "任务奖励"
        winner_name = msg.from_user.first_name or f"TG {msg.from_user.id}"
        success_text = f"答题成功，{winner_name} 已完成《{task['title']}》，奖励：{reward_text}。"
        try:
            await _reply_text(msg, success_text, quote=True, parse_mode=PLAIN_TEXT_MODE)
        except Exception as exc:
            LOGGER.warning(f"xiuxian quiz completion reply failed: {exc}")
            await _send_message(
                bot_instance,
                msg.chat.id,
                success_text,
                reply_to_message_id=msg.id,
                parse_mode=PLAIN_TEXT_MODE,
            )
        try:
            task_chat_id = int(task.get("group_chat_id") or msg.chat.id)
            if task.get("group_message_id"):
                summary = _task_group_text(task) + f"\n\n已完成：{winner_name}"
                if task.get("image_url"):
                    caption, _ = _split_photo_caption(summary)
                    await bot_instance.edit_message_caption(
                        task_chat_id,
                        int(task["group_message_id"]),
                        caption or "任务已完成",
                        parse_mode=PLAIN_TEXT_MODE,
                    )
                else:
                    await _edit_message_text(
                        bot_instance,
                        task_chat_id,
                        int(task["group_message_id"]),
                        summary,
                        parse_mode=PLAIN_TEXT_MODE,
                        persistent=True,
                    )
            else:
                await _send_message(
                    bot_instance,
                    task_chat_id,
                    f"任务《{task['title']}》已由 {winner_name} 完成。",
                    parse_mode=PLAIN_TEXT_MODE,
                )
        except Exception as exc:
            LOGGER.warning(f"xiuxian quiz task message refresh failed: {exc}")

    @bot_instance.on_message(filters.text & filters.chat(group) & ~filters.regex(r"^[\\/!\\.，。]"))
    async def xiuxian_group_encounter_trigger(_, msg):
        if msg.from_user is None or getattr(msg.from_user, "is_bot", False):
            return
        if not getattr(msg, "text", None):
            return
        text = str(msg.text or "").strip()
        if not text or text.startswith(("/", "!", ".")):
            return
        try:
            payload = maybe_spawn_group_encounter(msg.chat.id)
            if payload:
                await _push_group_encounter_notice(payload)
        except Exception as exc:
            LOGGER.warning(f"xiuxian encounter trigger failed chat={getattr(msg.chat, 'id', None)}: {exc}")

    @bot_instance.on_callback_query(filters.regex(r"^xiuxian:red:(\d+)$"))
    async def xiuxian_red_envelope_callback(_, call):
        envelope_id = int(call.matches[0].group(1))
        try:
            result = claim_red_envelope_for_user(envelope_id, call.from_user.id)
            envelope = result["envelope"]
            notice_text = _red_envelope_notice_text(envelope, result.get("claims", []))
            is_active = envelope.get("status") == "active"
            if getattr(call.message, "photo", None):
                caption, _ = _split_photo_caption(notice_text)
                await _edit_caption(
                    call.message,
                    caption or "红包状态已更新",
                    reply_markup=_red_envelope_keyboard(envelope_id) if is_active else None,
                    parse_mode=RICH_TEXT_MODE,
                    persistent=is_active,
                )
            else:
                await _edit_text(
                    call.message,
                    notice_text,
                    reply_markup=_red_envelope_keyboard(envelope_id) if is_active else None,
                    parse_mode=RICH_TEXT_MODE,
                    persistent=is_active,
                )
            await callAnswer(call, f"成功领取 {result['amount']} 灵石。")
        except Exception as exc:
            await callAnswer(call, str(exc), True)

    @bot_instance.on_callback_query(filters.regex(r"^xiuxian:encounter:(\d+)$"))
    async def xiuxian_group_encounter_callback(_, call):
        instance_id = int(call.matches[0].group(1))
        try:
            result = claim_group_encounter(instance_id, call.from_user.id)
            winner_name = call.from_user.first_name or f"TG {call.from_user.id}"
            success_text = render_group_encounter_success_text(result, winner_name)
            if getattr(call.message, "photo", None):
                caption, overflow = _split_photo_caption(success_text)
                await _edit_caption(
                    call.message,
                    caption or "奇遇已结算",
                    parse_mode=RICH_TEXT_MODE,
                    persistent=True,
                )
                if overflow:
                    await _send_message(
                        bot,
                        call.message.chat.id,
                        overflow,
                        reply_to_message_id=call.message.id,
                        parse_mode=RICH_TEXT_MODE,
                        persistent=True,
                    )
            else:
                await _edit_text(
                    call.message,
                    success_text,
                    parse_mode=RICH_TEXT_MODE,
                    persistent=True,
                )
            await callAnswer(call, "手速惊人，这桩机缘归你了。")
        except Exception as exc:
            await callAnswer(call, str(exc), True)

    @bot_instance.on_message(filters.command(["xiuxian_seed"], prefixes) & filters.private)
    async def xiuxian_seed_user(_, msg):
        try:
            if not is_admin_user_id(msg.from_user.id):
                return await _reply_text(msg, "只有主人才能使用这个演示资源指令。")
            if len(msg.command) < 2 or not msg.command[1].isdigit():
                return await _reply_text(msg, "用法：/xiuxian_seed <tg_id>")
            payload = admin_seed_demo_assets(int(msg.command[1]))
            await _reply_text(msg, f"演示资源已经发放完成。\n{_format_profile_text(payload)}", parse_mode=RICH_TEXT_MODE)
        finally:
            await _delete_user_command_message(msg)

    @bot_instance.on_message(filters.command(["allow_upload"], prefixes) & filters.reply)
    async def xiuxian_allow_upload(client, msg):
        try:
            if not await _can_manage_upload_permissions(client, msg):
                return await _reply_text(msg, "只有后台主人或本群主人才能授予上传权限。")
            target_user = getattr(getattr(msg, "reply_to_message", None), "from_user", None)
            if target_user is None or getattr(target_user, "is_bot", False):
                return await _reply_text(msg, "请先回复一位真实用户，再授予上传权限。")
            if is_admin_user_id(target_user.id):
                return await _reply_text(msg, "主人默认就拥有上传权限。")
            grant_image_upload_permission(target_user.id)
            await _reply_text(msg, f"已为 {target_user.first_name}（{target_user.id}）开启图片上传权限。")
        finally:
            await _delete_user_command_message(msg)

    @bot_instance.on_message(filters.command(["remove_upload", "delete_upload"], prefixes) & filters.reply)
    async def xiuxian_remove_upload(client, msg):
        try:
            if not await _can_manage_upload_permissions(client, msg):
                return await _reply_text(msg, "只有后台主人或本群主人才能移除上传权限。")
            target_user = getattr(getattr(msg, "reply_to_message", None), "from_user", None)
            if target_user is None or getattr(target_user, "is_bot", False):
                return await _reply_text(msg, "请先回复一位真实用户，再移除上传权限。")
            removed = revoke_image_upload_permission(target_user.id)
            if removed:
                await _reply_text(msg, f"已移除 {target_user.first_name}（{target_user.id}）的图片上传权限。")
            else:
                await _reply_text(msg, "这个用户当前没有额外的上传权限记录。")
        finally:
            await _delete_user_command_message(msg)

    async def _handle_xiuxian_gift_command(msg, inline_amount: int | None = None) -> None:
        actor = await _require_message_user(msg, action_text="赠送灵石")
        if actor is None:
            return
        try:
            target_tg, amount = _resolve_gift_target_and_amount(msg, inline_amount=inline_amount)
        except ValueError as exc:
            return await _reply_text(msg, str(exc), quote=True)
        if int(target_tg) == int(actor.id):
            return await _reply_text(msg, "不能给自己赠送灵石。", quote=True)
        try:
            result = gift_spirit_stone(actor.id, target_tg, amount)
            if int(getattr(getattr(msg, "chat", None), "id", 0) or 0) < 0:
                await _send_message(
                    bot,
                    msg.chat.id,
                    _gift_group_broadcast_text(actor.first_name or f"TG {actor.id}", result.get("receiver") or {}, amount),
                    parse_mode=RICH_TEXT_MODE,
                    persistent=True,
                )
            else:
                await _reply_text(
                    msg,
                    f"赠送成功，已向 {result['receiver'].get('display_label') or f'TG {target_tg}'} 送出 {amount} 灵石。",
                    quote=True,
                )
            await _notify_achievement_unlocks(result.get("achievement_unlocks"))
        except Exception as exc:
            await _reply_text(msg, str(exc) or "赠送灵石失败，请稍后重试。", quote=True)

    @bot_instance.on_message(filters.command(["rob"], prefixes) & filters.chat(group))
    async def xiuxian_rob_command(_, msg):
        try:
            if not _register_command_dispatch(msg, "rob"):
                LOGGER.warning(
                    f"xiuxian command duplicate skipped chat={getattr(getattr(msg, 'chat', None), 'id', None)} "
                    f"message={getattr(msg, 'id', None)} command=rob"
                )
                return
            LOGGER.info(
                f"xiuxian rob command received chat={getattr(getattr(msg, 'chat', None), 'id', None)} "
                f"actor={getattr(getattr(msg, 'from_user', None), 'id', None)} "
                f"reply_to={getattr(getattr(getattr(msg, 'reply_to_message', None), 'from_user', None), 'id', None)}"
            )
            actor = await _require_message_user(msg, action_text="发起抢劫")
            if actor is None:
                return
            if msg.reply_to_message is None or msg.reply_to_message.from_user is None:
                return await _reply_text(msg, "请先回复目标道友，再尝试发起抢劫。", quote=True)
            if msg.reply_to_message.from_user.is_bot:
                return await _reply_text(msg, "不能对机器人发起抢劫。", quote=True)
            if int(msg.reply_to_message.from_user.id) == int(actor.id):
                return await _reply_text(msg, "你不能抢劫自己。", quote=True)
            try:
                result = rob_player(actor.id, msg.reply_to_message.from_user.id)
                if result["success"]:
                    if int(result["amount"] or 0) > 0:
                        lines = [f"抢劫成功，你夺得了 {result['amount']} 灵石。"]
                    else:
                        lines = ["抢劫成功，但对方身上已没剩多少灵石。"]
                    artifact_payload = ((result.get("artifact_plunder") or {}).get("artifact") or {})
                    if artifact_payload:
                        lines.append(f"你又顺手夺走了 1 件未绑定法宝：{artifact_payload.get('name', '未知法宝')}。")
                    lines.append(f"本次判定成功率约 {round(float(result.get('success_rate', 0)) * 100, 1)}%。")
                    text = "\n".join(lines)
                else:
                    text = (
                        f"抢劫失败，你反而损失了 {-result['amount']} 灵石。\n"
                        f"本次判定成功率约 {round(float(result.get('success_rate', 0)) * 100, 1)}%。"
                    )
                await _reply_text(msg, text, quote=True)
                await _notify_achievement_unlocks(result.get("achievement_unlocks"))
            except Exception as exc:
                LOGGER.warning(
                    f"xiuxian rob failed attacker={getattr(actor, 'id', None)} "
                    f"target={getattr(getattr(getattr(msg, 'reply_to_message', None), 'from_user', None), 'id', None)}: {exc}"
                )
                await _reply_text(msg, str(exc) or "抢劫失败，请稍后重试。", quote=True)
        finally:
            await _delete_user_command_message(msg)

    @bot_instance.on_message(filters.command(["seek"], prefixes) & filters.chat(group))
    async def xiuxian_seek_command(_, msg):
        try:
            if not _register_command_dispatch(msg, "seek"):
                LOGGER.warning(
                    f"xiuxian command duplicate skipped chat={getattr(getattr(msg, 'chat', None), 'id', None)} "
                    f"message={getattr(msg, 'id', None)} command=seek"
                )
                return
            LOGGER.info(
                f"xiuxian seek command received chat={getattr(getattr(msg, 'chat', None), 'id', None)} "
                f"actor={getattr(getattr(msg, 'from_user', None), 'id', None)} "
                f"reply_to={getattr(getattr(getattr(msg, 'reply_to_message', None), 'from_user', None), 'id', None)}"
            )
            try:
                actor = await _require_message_user(msg, action_text="探查对方信息")
                if actor is None:
                    return
                if msg.reply_to_message is None or msg.reply_to_message.from_user is None:
                    return await _reply_text(msg, "请先回复目标道友，再尝试探查。", quote=True)
                if msg.reply_to_message.from_user.is_bot:
                    return await _reply_text(msg, "机器人没有可供探查的修仙信息。", quote=True)
                if int(msg.reply_to_message.from_user.id) == int(actor.id):
                    return await _reply_text(msg, "你观照己身即可，无需对自己施展探查。", quote=True)

                seeker = serialize_full_profile(actor.id)
                if not seeker["profile"]["consented"]:
                    return await _reply_text(msg, "你还没有踏入仙途，先私聊机器人点击 /xiuxian 入道。", quote=True)

                target = serialize_full_profile(msg.reply_to_message.from_user.id)
                if not target["profile"]["consented"]:
                    return await _reply_text(msg, "对方尚未踏入仙途，探查不到任何灵息。", quote=True)

                seeker_divine_sense = _effective_divine_sense(seeker)
                target_divine_sense = _effective_divine_sense(target)
                if seeker_divine_sense <= target_divine_sense:
                    return await _reply_text(
                        msg,
                        f"神识强度不够，无法看破对方虚实。你的神识 {seeker_divine_sense}，对方神识 {target_divine_sense}。",
                        quote=True,
                    )

                fallback_name = msg.reply_to_message.from_user.first_name or f"TG {msg.reply_to_message.from_user.id}"
                lines = [
                    f"探查成功。你的神识 {seeker_divine_sense}，对方神识 {target_divine_sense}。",
                    "",
                    _format_group_profile_showcase(target, fallback_name),
                ]
                await _reply_text(msg, "\n".join(lines), quote=True, parse_mode=RICH_TEXT_MODE)
            except Exception as exc:
                LOGGER.warning(
                    f"xiuxian seek failed seeker={getattr(actor, 'id', None)} "
                    f"target={getattr(getattr(msg.reply_to_message, 'from_user', None), 'id', None)}: {exc}"
                )
                await _reply_text(msg, f"探查失败：{exc or '请稍后重试。'}", quote=True)
        finally:
            await _delete_user_command_message(msg)

    @bot_instance.on_message(filters.command(["gift"], prefixes))
    async def xiuxian_gift_command(_, msg):
        try:
            if not _register_command_dispatch(msg, "gift"):
                LOGGER.warning(
                    f"xiuxian command duplicate skipped chat={getattr(getattr(msg, 'chat', None), 'id', None)} "
                    f"message={getattr(msg, 'id', None)} command=gift"
                )
                return
            await _handle_xiuxian_gift_command(msg)
        finally:
            await _delete_user_command_message(msg)

    @bot_instance.on_message(filters.regex(GIFT_INLINE_AMOUNT_PATTERN))
    async def xiuxian_gift_inline_command(_, msg):
        try:
            if not _register_command_dispatch(msg, "gift"):
                LOGGER.warning(
                    f"xiuxian command duplicate skipped chat={getattr(getattr(msg, 'chat', None), 'id', None)} "
                    f"message={getattr(msg, 'id', None)} command=gift-inline"
                )
                return
            text = str(getattr(msg, "text", None) or "").strip()
            match = GIFT_INLINE_AMOUNT_PATTERN.match(text)
            if match is None:
                return
            await _handle_xiuxian_gift_command(msg, inline_amount=int(match.group(1)))
        finally:
            await _delete_user_command_message(msg)


def register_web(app) -> None:
    user_router = APIRouter(prefix="/plugins/xiuxian", tags=["xiuxian-user"])
    admin_router = APIRouter(prefix="/plugins/xiuxian/admin-api", tags=["xiuxian-admin"])

    if STATIC_DIR.exists():
        app.mount("/plugins/xiuxian/static", StaticFiles(directory=STATIC_DIR), name="xiuxian-static")
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    app.mount("/plugins/xiuxian/uploads", StaticFiles(directory=UPLOAD_DIR), name="xiuxian-uploads")

    if not getattr(app.state, "xiuxian_request_context_middleware", False):
        @app.middleware("http")
        async def xiuxian_request_context_middleware(request: Request, call_next):
            path = str(request.url.path or "")
            if path.startswith("/plugins/xiuxian"):
                init_data = request.headers.get("x-telegram-init-data")
                if not init_data:
                    body = await request.body()
                    init_data = _extract_init_data_from_body_bytes(request.headers.get("content-type", ""), body)

                    async def receive():
                        return {"type": "http.request", "body": body, "more_body": False}

                    request = Request(request.scope, receive)
                request.state.xiuxian_init_data = init_data
            return await call_next(request)

        app.state.xiuxian_request_context_middleware = True

    if not getattr(app.state, "xiuxian_value_error_handler", False):
        @app.exception_handler(ValueError)
        async def xiuxian_value_error_handler(request: Request, exc: ValueError):
            if str(request.url.path or "").startswith("/plugins/xiuxian"):
                _record_request_error(request, exc, status_code=400, level="WARNING")
            return JSONResponse(status_code=400, content={"code": 400, "message": str(exc), "detail": str(exc)})

        app.state.xiuxian_value_error_handler = True

    if not getattr(app.state, "xiuxian_http_exception_handler", False):
        @app.exception_handler(HTTPException)
        async def xiuxian_http_exception_handler(request: Request, exc: HTTPException):
            if str(request.url.path or "").startswith("/plugins/xiuxian"):
                level = "ERROR" if int(exc.status_code or 500) >= 500 else "WARNING"
                detail = str(exc.detail or exc.status_code)
                _record_request_error(request, Exception(detail), status_code=int(exc.status_code or 500), level=level)
            return JSONResponse(
                status_code=exc.status_code,
                content={"code": exc.status_code, "message": str(exc.detail), "detail": str(exc.detail)},
            )

        app.state.xiuxian_http_exception_handler = True

    if not getattr(app.state, "xiuxian_exception_handler", False):
        @app.exception_handler(Exception)
        async def xiuxian_exception_handler(request: Request, exc: Exception):
            if str(request.url.path or "").startswith("/plugins/xiuxian"):
                _record_request_error(request, exc, status_code=500, level="ERROR")
            LOGGER.exception(f"xiuxian api unhandled error: {exc}")
            return JSONResponse(
                status_code=500,
                content={
                    "code": 500,
                    "message": "内部服务暂时出了点岔子，请稍后再试。",
                    "detail": str(exc) or "Internal Server Error",
                },
            )

        app.state.xiuxian_exception_handler = True

    def render_versioned_static_page(filename: str) -> HTMLResponse:
        html_path = STATIC_DIR / filename
        content = html_path.read_text(encoding="utf-8")

        def replace_asset(match: re.Match[str]) -> str:
            asset_url = match.group(1)
            asset_name = match.group(2)
            asset_path = STATIC_DIR / asset_name
            try:
                asset_version = f"{PLUGIN_VERSION}-{int(asset_path.stat().st_mtime)}"
            except OSError:
                asset_version = PLUGIN_VERSION
            return f"{asset_url}?v={asset_version}"

        rendered = STATIC_ASSET_PATTERN.sub(replace_asset, content)
        return HTMLResponse(
            rendered,
            headers={
                "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
                "Pragma": "no-cache",
                "Expires": "0",
            },
        )

    @user_router.get("/app")
    async def xiuxian_app_page():
        return render_versioned_static_page("app.html")

    @user_router.get("/admin")
    async def xiuxian_admin_page():
        return render_versioned_static_page("admin.html")

    @user_router.post("/api/bootstrap")
    async def xiuxian_bootstrap(payload: InitDataPayload):
        telegram_user = _verify_user_from_init_data(payload.init_data)
        profile = _full_bundle(telegram_user["id"])
        return {
            "code": 200,
            "data": {
                "telegram_user": telegram_user,
                "profile_bundle": profile,
                "app_url": build_plugin_url("/plugins/xiuxian/app"),
                "admin_panel_url": _admin_panel_url() if is_admin_user_id(telegram_user["id"]) else None,
                "home_url": build_plugin_url("/miniapp"),
                "bottom_nav": _build_bottom_nav(),
            },
        }

    @user_router.post("/api/upload-image")
    async def xiuxian_upload_image_api(
        request: Request,
        init_data: str = Form(...),
        folder: str = Form("tasks"),
        file: UploadFile = File(...),
    ):
        telegram_user = _verify_user_from_init_data(init_data)
        allowed, reason = _can_user_upload_images(telegram_user["id"])
        if not allowed:
            raise HTTPException(status_code=403, detail=reason)
        result = await _save_uploaded_image(file, f"user/{telegram_user['id']}/{folder}", str(request.base_url))
        return {"code": 200, "data": result}

    @user_router.post("/api/enter")
    async def xiuxian_enter(payload: InitDataPayload):
        telegram_user = _verify_user_from_init_data(payload.init_data)
        init_path_for_user(telegram_user["id"])
        create_foundation_pill_for_user_if_missing(telegram_user["id"])
        return {"code": 200, "data": _full_bundle(telegram_user["id"])}

    @user_router.post("/api/train")
    async def xiuxian_train_api(payload: InitDataPayload):
        telegram_user = _verify_user_from_init_data(payload.init_data)
        result = practice_for_user(telegram_user["id"])
        return {"code": 200, "data": result}

    @user_router.post("/api/commission/claim")
    async def xiuxian_commission_claim_api(payload: CommissionClaimPayload):
        telegram_user = _verify_user_from_init_data(payload.init_data)
        result = claim_spirit_stone_commission(telegram_user["id"], payload.commission_key)
        return {"code": 200, "data": result}

    @user_router.post("/api/breakthrough")
    async def xiuxian_breakthrough_api(payload: BreakthroughPayload):
        telegram_user = _verify_user_from_init_data(payload.init_data)
        result = breakthrough_for_user(telegram_user["id"], use_pill=payload.use_pill)
        return {"code": 200, "data": result}

    @user_router.post("/api/pill/use")
    async def xiuxian_use_pill_api(payload: ConsumePillPayload):
        telegram_user = _verify_user_from_init_data(payload.init_data)
        result = consume_pill_for_user(telegram_user["id"], payload.pill_id)
        return {"code": 200, "data": result}

    @user_router.post("/api/artifact/equip")
    async def xiuxian_equip_api(payload: EquipArtifactPayload):
        telegram_user = _verify_user_from_init_data(payload.init_data)
        result = equip_artifact_for_user(telegram_user["id"], payload.artifact_id)
        return {"code": 200, "data": result}

    @user_router.post("/api/artifact/bind")
    async def xiuxian_bind_artifact_api(payload: ArtifactBindingPayload):
        telegram_user = _verify_user_from_init_data(payload.init_data)
        result = bind_artifact_for_user(telegram_user["id"], payload.artifact_id)
        return {"code": 200, "data": result}

    @user_router.post("/api/artifact/unbind")
    async def xiuxian_unbind_artifact_api(payload: ArtifactBindingPayload):
        telegram_user = _verify_user_from_init_data(payload.init_data)
        result = unbind_artifact_for_user(telegram_user["id"], payload.artifact_id)
        return {"code": 200, "data": result}

    @user_router.post("/api/talisman/activate")
    async def xiuxian_activate_talisman_api(payload: ActivateTalismanPayload):
        telegram_user = _verify_user_from_init_data(payload.init_data)
        result = activate_talisman_for_user(telegram_user["id"], payload.talisman_id)
        return {"code": 200, "data": result}

    @user_router.post("/api/talisman/bind")
    async def xiuxian_bind_talisman_api(payload: TalismanBindingPayload):
        telegram_user = _verify_user_from_init_data(payload.init_data)
        result = bind_talisman_for_user(telegram_user["id"], payload.talisman_id)
        return {"code": 200, "data": result}

    @user_router.post("/api/talisman/unbind")
    async def xiuxian_unbind_talisman_api(payload: TalismanBindingPayload):
        telegram_user = _verify_user_from_init_data(payload.init_data)
        result = unbind_talisman_for_user(telegram_user["id"], payload.talisman_id)
        return {"code": 200, "data": result}

    @user_router.post("/api/technique/activate")
    async def xiuxian_activate_technique_api(payload: ActivateTechniquePayload):
        telegram_user = _verify_user_from_init_data(payload.init_data)
        result = activate_technique_for_user(telegram_user["id"], payload.technique_id)
        return {"code": 200, "data": result}

    @user_router.post("/api/title/equip")
    async def xiuxian_equip_title_api(payload: TitleEquipPayload):
        telegram_user = _verify_user_from_init_data(payload.init_data)
        result = set_current_title_for_user(telegram_user["id"], payload.title_id)
        return {"code": 200, "data": result}

    @user_router.post("/api/title/group-sync")
    async def xiuxian_sync_title_to_group_api(payload: TitleGroupSyncPayload):
        telegram_user = _verify_user_from_init_data(payload.init_data)
        bundle = serialize_full_profile(telegram_user["id"])
        current_title = bundle.get("current_title") or {}
        title_name = str(current_title.get("name") or "").strip()
        if not title_name:
            raise HTTPException(status_code=400, detail="请先佩戴称号，再同步到群头衔。")
        chat_id = int(payload.chat_id or _main_group_chat_id() or 0)
        if not chat_id:
            raise HTTPException(status_code=400, detail="当前未配置可同步的群组。")
        set_title = getattr(bot, "set_administrator_title", None)
        if not callable(set_title):
            raise HTTPException(status_code=501, detail="当前 Bot 运行环境暂不支持设置群头衔。")
        sync_title = title_name[:16]
        try:
            await set_title(chat_id, telegram_user["id"], sync_title)
        except Exception as exc:
            LOGGER.warning(f"xiuxian title sync failed chat={chat_id} tg={telegram_user['id']}: {exc}")
            raise HTTPException(
                status_code=400,
                detail="同步失败。需要先将你设为群管理员，并确保 Bot 拥有修改管理员头衔的权限。",
            ) from exc
        return {
            "code": 200,
            "data": {
                "chat_id": chat_id,
                "title": sync_title,
                "profile": bundle,
            },
        }

    @user_router.post("/api/retreat/start")
    async def xiuxian_retreat_start_api(payload: RetreatPayload):
        telegram_user = _verify_user_from_init_data(payload.init_data)
        result = start_retreat_for_user(telegram_user["id"], payload.hours)
        return {"code": 200, "data": result}

    @user_router.post("/api/retreat/finish")
    async def xiuxian_retreat_finish_api(payload: InitDataPayload):
        telegram_user = _verify_user_from_init_data(payload.init_data)
        result = finish_retreat_for_user(telegram_user["id"])
        return {"code": 200, "data": result}

    @user_router.post("/api/exchange")
    async def xiuxian_exchange_api(payload: ExchangePayload):
        telegram_user = _verify_user_from_init_data(payload.init_data)
        if payload.direction == "coin_to_stone":
            result = convert_emby_coin_to_stone(telegram_user["id"], payload.amount)
        elif payload.direction == "stone_to_coin":
            result = convert_stone_to_emby_coin(telegram_user["id"], payload.amount)
        else:
            raise HTTPException(status_code=400, detail="Unsupported exchange direction")
        return {"code": 200, "data": result}

    @user_router.post("/api/sect/join")
    async def xiuxian_join_sect_api(payload: SectJoinPayload):
        telegram_user = _verify_user_from_init_data(payload.init_data)
        result = join_sect_for_user(telegram_user["id"], payload.sect_id)
        return {"code": 200, "data": {"sect": result, "bundle": _full_bundle(telegram_user["id"])}}

    @user_router.post("/api/sect/leave")
    async def xiuxian_leave_sect_api(payload: InitDataPayload):
        telegram_user = _verify_user_from_init_data(payload.init_data)
        result = leave_sect_for_user(telegram_user["id"])
        return {"code": 200, "data": {"sect": result, "bundle": _full_bundle(telegram_user["id"])}}

    @user_router.post("/api/sect/salary")
    async def xiuxian_claim_salary_api(payload: InitDataPayload):
        telegram_user = _verify_user_from_init_data(payload.init_data)
        result = claim_sect_salary_for_user(telegram_user["id"])
        return {"code": 200, "data": {"salary": result["salary"], "bundle": _full_bundle(telegram_user["id"])}}

    @user_router.post("/api/task/create")
    async def xiuxian_create_task_api(payload: UserTaskPayload):
        telegram_user = _verify_user_from_init_data(payload.init_data)
        task = create_bounty_task(
            actor_tg=telegram_user["id"],
            title=payload.title,
            description=payload.description,
            task_scope=payload.task_scope,
            task_type=payload.task_type,
            question_text=payload.question_text,
            answer_text=payload.answer_text,
            image_url=payload.image_url,
            required_item_kind=payload.required_item_kind,
            required_item_ref_id=payload.required_item_ref_id,
            required_item_quantity=payload.required_item_quantity,
            reward_stone=payload.reward_stone,
            reward_item_kind=payload.reward_item_kind,
            reward_item_ref_id=payload.reward_item_ref_id,
            reward_item_quantity=payload.reward_item_quantity,
            max_claimants=payload.max_claimants,
            active_in_group=payload.active_in_group,
            group_chat_id=payload.group_chat_id or _main_group_chat_id(),
        )
        push_warning = None
        if task.get("active_in_group"):
            task, push_warning = await _safe_push_task_to_group(task)
        _remember_journal(telegram_user["id"], "task", "发布任务", f"发布了任务【{task['title']}】")
        return {"code": 200, "data": {"task": task, "push_warning": push_warning, "bundle": _full_bundle(telegram_user["id"])}}

    @user_router.post("/api/task/claim")
    async def xiuxian_claim_task_api(payload: TaskClaimPayload):
        telegram_user = _verify_user_from_init_data(payload.init_data)
        result = claim_task_for_user(telegram_user["id"], payload.task_id)
        return {"code": 200, "data": {"result": result, "bundle": _full_bundle(telegram_user["id"])}}

    @user_router.post("/api/task/cancel")
    async def xiuxian_cancel_task_api(payload: TaskCancelPayload):
        telegram_user = _verify_user_from_init_data(payload.init_data)
        result = cancel_task_for_user(telegram_user["id"], payload.task_id)
        task = result.get("task") or {}
        try:
            task_chat_id = int(task.get("group_chat_id") or _main_group_chat_id() or 0)
            if task_chat_id and task.get("group_message_id"):
                summary = _task_group_text(task) + "\n\n发起者已主动撤销该任务。"
                if task.get("image_url"):
                    caption, _ = _split_photo_caption(summary)
                    await bot.edit_message_caption(
                        task_chat_id,
                        int(task["group_message_id"]),
                        caption or "任务已撤销",
                        parse_mode=RICH_TEXT_MODE,
                    )
                else:
                    await _edit_message_text(
                        bot,
                        task_chat_id,
                        int(task["group_message_id"]),
                        summary,
                        parse_mode=RICH_TEXT_MODE,
                        persistent=True,
                    )
        except Exception as exc:
            LOGGER.warning(f"xiuxian task cancel message refresh failed: {exc}")
        return {"code": 200, "data": {"result": result, "bundle": _full_bundle(telegram_user["id"])}}

    @user_router.post("/api/recipe/craft")
    async def xiuxian_craft_recipe_api(payload: CraftPayload):
        telegram_user = _verify_user_from_init_data(payload.init_data)
        result = craft_recipe_for_user(telegram_user["id"], payload.recipe_id)
        await _maybe_broadcast_craft(telegram_user["id"], result)
        await _notify_achievement_unlocks(result.get("achievement_unlocks"))
        return {"code": 200, "data": {"result": result, "bundle": _full_bundle(telegram_user["id"])}}

    @user_router.post("/api/explore/start")
    async def xiuxian_explore_start_api(payload: ExploreStartPayload):
        telegram_user = _verify_user_from_init_data(payload.init_data)
        result = start_exploration_for_user(telegram_user["id"], payload.scene_id, payload.minutes)
        return {"code": 200, "data": {"exploration": result, "bundle": _full_bundle(telegram_user["id"])}}

    @user_router.post("/api/explore/claim")
    async def xiuxian_explore_claim_api(payload: ExploreClaimPayload):
        telegram_user = _verify_user_from_init_data(payload.init_data)
        result = claim_exploration_for_user(telegram_user["id"], payload.exploration_id)
        await _notify_achievement_unlocks(result.get("achievement_unlocks"))
        return {"code": 200, "data": {"result": result, "bundle": _full_bundle(telegram_user["id"])}}

    @user_router.post("/api/red-envelope/create")
    async def xiuxian_create_red_envelope_api(payload: RedEnvelopePayload):
        telegram_user = _verify_user_from_init_data(payload.init_data)
        result = create_red_envelope_for_user(
            tg=telegram_user["id"],
            cover_text=payload.cover_text,
            image_url=payload.image_url,
            mode=payload.mode,
            amount_total=payload.amount_total,
            count_total=payload.count_total,
            target_tg=payload.target_tg,
            group_chat_id=_main_group_chat_id(),
        )
        await _push_red_envelope_notice(result["envelope"])
        await _notify_achievement_unlocks(result.get("achievement_unlocks"))
        return {"code": 200, "data": {"result": result, "bundle": _full_bundle(telegram_user["id"])}}

    @user_router.post("/api/shop/personal")
    async def xiuxian_personal_shop_api(payload: PersonalShopPayload):
        telegram_user = _verify_user_from_init_data(payload.init_data)
        result = create_personal_shop_listing(
            tg=telegram_user["id"],
            shop_name=payload.shop_name or generate_shop_name(telegram_user.get("first_name", "道友")),
            item_kind=payload.item_kind,
            item_ref_id=payload.item_ref_id,
            quantity=payload.quantity,
            price_stone=payload.price_stone,
            broadcast=payload.broadcast,
        )

        if payload.broadcast:
            try:
                await _send_message(
                    bot,
                    group[0],
                    broadcast_shop_copy(
                        telegram_user.get("first_name", "道友"),
                        result["listing"]["shop_name"],
                        result["listing"]["item_name"],
                        result["listing"]["price_stone"],
                    ),
                    parse_mode=RICH_TEXT_MODE,
                )
            except Exception as exc:
                LOGGER.warning(f"修仙坊市全群播报发送失败: {exc}")

        _remember_journal(telegram_user["id"], "shop", "上架商品", f"上架了【{result['listing']['item_name']}】")
        return {"code": 200, "data": result}

    @user_router.post("/api/auction/personal")
    async def xiuxian_personal_auction_api(payload: PersonalAuctionPayload):
        telegram_user = _verify_user_from_init_data(payload.init_data)
        seller_name = " ".join(
            part for part in [telegram_user.get("first_name"), telegram_user.get("last_name")] if part
        ).strip()
        if not seller_name:
            username = str(telegram_user.get("username") or "").strip()
            seller_name = f"@{username}" if username else f"TG {telegram_user['id']}"

        result = create_personal_auction_listing(
            tg=telegram_user["id"],
            seller_name=seller_name,
            item_kind=payload.item_kind,
            item_ref_id=payload.item_ref_id,
            quantity=payload.quantity,
            opening_price_stone=payload.opening_price_stone,
            bid_increment_stone=payload.bid_increment_stone,
            buyout_price_stone=payload.buyout_price_stone,
        )
        auction = dict(result.get("auction") or {})
        push_warning = None
        try:
            auction, push_warning = await _push_auction_to_group(auction)
        except Exception:
            try:
                cancel_personal_auction_listing(telegram_user["id"], int(auction.get("id") or 0))
            except Exception as rollback_exc:
                LOGGER.warning(f"xiuxian auction rollback failed auction={auction.get('id')}: {rollback_exc}")
            raise

        _remember_journal(
            telegram_user["id"],
            "auction",
            "发起拍卖",
            f"拍卖了【{auction.get('item_name') or '未知拍品'}】",
        )
        return {
            "code": 200,
            "data": {
                "auction": auction,
                "push_warning": push_warning,
                "bundle": _full_bundle(telegram_user["id"]),
            },
        }

    @user_router.post("/api/shop/cancel")
    async def xiuxian_cancel_listing_api(payload: ShopCancelPayload):
        telegram_user = _verify_user_from_init_data(payload.init_data)
        result = cancel_personal_shop_item(telegram_user["id"], payload.item_id)
        _remember_journal(telegram_user["id"], "shop", "取消上架", f"取消了商品 #{payload.item_id} 的上架")
        return {"code": 200, "data": {"result": result, "bundle": _full_bundle(telegram_user["id"])}}

    @user_router.post("/api/shop/purchase")
    async def xiuxian_purchase_api(payload: PurchasePayload):
        telegram_user = _verify_user_from_init_data(payload.init_data)
        result = purchase_shop_item(telegram_user["id"], payload.item_id, payload.quantity)
        _remember_journal(telegram_user["id"], "shop", "购买商品", f"购买了【{result['item']['item_name']}】")
        seller_tg = result.get("seller_tg")
        if seller_tg and int(seller_tg) != int(telegram_user["id"]):
            try:
                await _send_message(
                    bot,
                    int(seller_tg),
                    f"你的商品【{result['item']['item_name']}】已被 {result.get('buyer_name') or '道友'} 购买，到账 {result['total_cost']} 灵石。",
                )
            except Exception as exc:
                LOGGER.warning(f"xiuxian seller notify failed: {exc}")
        return {"code": 200, "data": result}

    @user_router.post("/api/player/search")
    async def xiuxian_player_search_api(payload: PlayerLookupPayload):
        telegram_user = _verify_user_from_init_data(payload.init_data)
        keyword = str(payload.query or "").strip()
        if not keyword:
            return {"code": 200, "data": {"items": [], "page": payload.page, "page_size": payload.page_size, "total": 0}}
        result = search_xiuxian_players(query=keyword, page=payload.page, page_size=payload.page_size)
        return {"code": 200, "data": _minimal_player_lookup_payload(result, telegram_user["id"])}

    @user_router.post("/api/gift")
    async def xiuxian_gift_api(payload: GiftPayload):
        telegram_user = _verify_user_from_init_data(payload.init_data)
        result = gift_spirit_stone(telegram_user["id"], payload.target_tg, payload.amount)
        await _notify_achievement_unlocks(result.get("achievement_unlocks"))
        return {"code": 200, "data": {"result": result, "bundle": _full_bundle(telegram_user["id"])}}

    @user_router.post("/api/gift/item")
    async def xiuxian_item_gift_api(payload: ItemGiftPayload):
        telegram_user = _verify_user_from_init_data(payload.init_data)
        result = gift_inventory_item(
            telegram_user["id"],
            payload.target_tg,
            payload.item_kind,
            payload.item_ref_id,
            payload.quantity,
        )
        return {"code": 200, "data": {"result": result, "bundle": _full_bundle(telegram_user["id"])}}

    @user_router.post("/api/journal")
    async def xiuxian_journal_api(payload: InitDataPayload):
        telegram_user = _verify_user_from_init_data(payload.init_data)
        return {"code": 200, "data": list_recent_journals(telegram_user["id"])}

    @user_router.post("/api/leaderboard")
    async def xiuxian_leaderboard_api(payload: LeaderboardPayload):
        _verify_user_from_init_data(payload.init_data)
        result = build_leaderboard(payload.kind, payload.page)
        return {"code": 200, "data": result}

    @user_router.get("/api/shop")
    async def xiuxian_public_shop_api():
        return {"code": 200, "data": list_public_shop_items()}

    @admin_router.post("/bootstrap")
    async def xiuxian_admin_bootstrap(payload: AdminBootstrapPayload):
        admin_user = _verify_admin_credential(payload.token, payload.init_data)
        # 管理页启动时先同步一次默认种子，确保拉新镜像后能立即看到最新配置。
        ensure_seed_data()
        world = _admin_world_snapshot()
        return {
            "code": 200,
            "data": {
                "admin_user": admin_user,
                "settings": update_xiuxian_settings({}),
                "pill_type_options": list_pill_type_options(),
                "artifacts": list_artifacts(),
                "pills": list_pills(),
                "talismans": list_talismans(),
                "techniques": list_techniques(),
                "official_shop": list_shop_items(official_only=True, include_disabled=True),
                **world,
            },
        }

    @admin_router.post("/settings")
    async def xiuxian_settings_api(payload: AdminSettingPayload, request: Request):
        token = request.headers.get("x-admin-token")
        init_data = request.headers.get("x-telegram-init-data")
        _verify_admin_credential(token, init_data)
        patch = {key: value for key, value in payload.model_dump().items() if value is not None}
        return {"code": 200, "data": update_xiuxian_settings(patch)}

    @admin_router.post("/error-logs")
    async def xiuxian_error_logs_api(payload: ErrorLogQueryPayload, request: Request):
        token = request.headers.get("x-admin-token")
        init_data = request.headers.get("x-telegram-init-data")
        _verify_admin_credential(token, init_data)
        return {
            "code": 200,
            "data": list_error_logs(
                limit=payload.limit,
                tg=payload.tg,
                level=payload.level,
                keyword=payload.keyword,
            ),
        }

    @admin_router.post("/upload-image")
    async def xiuxian_admin_upload_image_api(
        request: Request,
        folder: str = Form("admin"),
        file: UploadFile = File(...),
    ):
        token = request.headers.get("x-admin-token")
        init_data = request.headers.get("x-telegram-init-data")
        _verify_admin_credential(token, init_data)
        result = await _save_uploaded_image(file, f"admin/{folder}", str(request.base_url))
        return {"code": 200, "data": result}

    @admin_router.post("/upload-permission/grant")
    async def xiuxian_admin_grant_upload_permission_api(payload: UploadPermissionPayload, request: Request):
        token = request.headers.get("x-admin-token")
        init_data = request.headers.get("x-telegram-init-data")
        _verify_admin_credential(token, init_data)
        if is_admin_user_id(payload.tg):
            return {"code": 200, "data": {"tg": payload.tg, "granted": True, "builtin": True}}
        grant_image_upload_permission(payload.tg)
        return {"code": 200, "data": {"tg": payload.tg, "granted": True, "builtin": False}}

    @admin_router.post("/upload-permission/revoke")
    async def xiuxian_admin_revoke_upload_permission_api(payload: UploadPermissionPayload, request: Request):
        token = request.headers.get("x-admin-token")
        init_data = request.headers.get("x-telegram-init-data")
        _verify_admin_credential(token, init_data)
        removed = revoke_image_upload_permission(payload.tg)
        return {"code": 200, "data": {"tg": payload.tg, "removed": removed}}

    @admin_router.post("/title")
    async def xiuxian_title_api(payload: TitlePayload, request: Request):
        token = request.headers.get("x-admin-token")
        init_data = request.headers.get("x-telegram-init-data")
        _verify_admin_credential(token, init_data)
        return {"code": 200, "data": create_title(**payload.model_dump())}

    @admin_router.patch("/title/{title_id}")
    async def xiuxian_patch_title_api(title_id: int, payload: TitlePayload, request: Request):
        token = request.headers.get("x-admin-token")
        init_data = request.headers.get("x-telegram-init-data")
        _verify_admin_credential(token, init_data)
        result = patch_title(title_id, **payload.model_dump())
        if result is None:
            raise HTTPException(status_code=404, detail="Title not found")
        return {"code": 200, "data": result}

    @admin_router.post("/title/grant")
    async def xiuxian_grant_title_api(payload: TitleGrantPayload, request: Request):
        token = request.headers.get("x-admin-token")
        init_data = request.headers.get("x-telegram-init-data")
        _verify_admin_credential(token, init_data)
        result = grant_title_to_user(payload.tg, payload.title_id, source="admin", equip=payload.equip)
        return {"code": 200, "data": result}

    @admin_router.post("/achievement")
    async def xiuxian_achievement_api(payload: AchievementPayload, request: Request):
        token = request.headers.get("x-admin-token")
        init_data = request.headers.get("x-telegram-init-data")
        _verify_admin_credential(token, init_data)
        return {"code": 200, "data": create_achievement(**payload.model_dump())}

    @admin_router.patch("/achievement/{achievement_id}")
    async def xiuxian_patch_achievement_api(achievement_id: int, payload: AchievementPayload, request: Request):
        token = request.headers.get("x-admin-token")
        init_data = request.headers.get("x-telegram-init-data")
        _verify_admin_credential(token, init_data)
        result = patch_achievement(achievement_id, **payload.model_dump())
        if result is None:
            raise HTTPException(status_code=404, detail="Achievement not found")
        return {"code": 200, "data": result}

    @admin_router.post("/achievement/progress")
    async def xiuxian_achievement_progress_api(payload: AchievementProgressPayload, request: Request):
        token = request.headers.get("x-admin-token")
        init_data = request.headers.get("x-telegram-init-data")
        _verify_admin_credential(token, init_data)
        result = record_achievement_progress(payload.tg, payload.increments, source=payload.source or "admin")
        await _notify_achievement_unlocks(result.get("unlocks"))
        return {"code": 200, "data": result}

    @admin_router.post("/artifact")
    async def xiuxian_artifact_api(payload: ArtifactPayload, request: Request):
        token = request.headers.get("x-admin-token")
        init_data = request.headers.get("x-telegram-init-data")
        _verify_admin_credential(token, init_data)
        artifact = create_artifact(**payload.model_dump())
        return {"code": 200, "data": artifact}

    @admin_router.patch("/artifact/{artifact_id}")
    async def xiuxian_artifact_patch_api(artifact_id: int, payload: ArtifactPayload, request: Request):
        token = request.headers.get("x-admin-token")
        init_data = request.headers.get("x-telegram-init-data")
        _verify_admin_credential(token, init_data)
        result = patch_artifact(artifact_id, **payload.model_dump())
        if result is None:
            raise HTTPException(status_code=404, detail="法宝不存在")
        return {"code": 200, "data": result}

    @admin_router.post("/pill")
    async def xiuxian_pill_api(payload: PillPayload, request: Request):
        token = request.headers.get("x-admin-token")
        init_data = request.headers.get("x-telegram-init-data")
        _verify_admin_credential(token, init_data)
        pill = create_pill(**payload.model_dump())
        return {"code": 200, "data": pill}

    @admin_router.patch("/pill/{pill_id}")
    async def xiuxian_pill_patch_api(pill_id: int, payload: PillPayload, request: Request):
        token = request.headers.get("x-admin-token")
        init_data = request.headers.get("x-telegram-init-data")
        _verify_admin_credential(token, init_data)
        result = patch_pill(pill_id, **payload.model_dump())
        if result is None:
            raise HTTPException(status_code=404, detail="丹药不存在")
        return {"code": 200, "data": result}

    @admin_router.post("/talisman")
    async def xiuxian_talisman_api(payload: TalismanPayload, request: Request):
        token = request.headers.get("x-admin-token")
        init_data = request.headers.get("x-telegram-init-data")
        _verify_admin_credential(token, init_data)
        talisman = create_talisman(**payload.model_dump())
        return {"code": 200, "data": talisman}

    @admin_router.patch("/talisman/{talisman_id}")
    async def xiuxian_talisman_patch_api(talisman_id: int, payload: TalismanPayload, request: Request):
        token = request.headers.get("x-admin-token")
        init_data = request.headers.get("x-telegram-init-data")
        _verify_admin_credential(token, init_data)
        result = patch_talisman(talisman_id, **payload.model_dump())
        if result is None:
            raise HTTPException(status_code=404, detail="符箓不存在")
        return {"code": 200, "data": result}

    @admin_router.post("/technique")
    async def xiuxian_technique_api(payload: TechniquePayload, request: Request):
        token = request.headers.get("x-admin-token")
        init_data = request.headers.get("x-telegram-init-data")
        _verify_admin_credential(token, init_data)
        technique = create_technique(**payload.model_dump())
        return {"code": 200, "data": technique}

    @admin_router.patch("/technique/{technique_id}")
    async def xiuxian_technique_patch_api(technique_id: int, payload: TechniquePayload, request: Request):
        token = request.headers.get("x-admin-token")
        init_data = request.headers.get("x-telegram-init-data")
        _verify_admin_credential(token, init_data)
        result = patch_technique(technique_id, **payload.model_dump())
        if result is None:
            raise HTTPException(status_code=404, detail="功法不存在")
        return {"code": 200, "data": result}

    @admin_router.post("/artifact-set")
    async def xiuxian_artifact_set_api(payload: ArtifactSetPayload, request: Request):
        token = request.headers.get("x-admin-token")
        init_data = request.headers.get("x-telegram-init-data")
        _verify_admin_credential(token, init_data)
        return {"code": 200, "data": create_artifact_set(**payload.model_dump())}

    @admin_router.patch("/artifact-set/{artifact_set_id}")
    async def xiuxian_artifact_set_patch_api(artifact_set_id: int, payload: ArtifactSetPayload, request: Request):
        token = request.headers.get("x-admin-token")
        init_data = request.headers.get("x-telegram-init-data")
        _verify_admin_credential(token, init_data)
        result = patch_artifact_set(artifact_set_id, **payload.model_dump())
        if result is None:
            raise HTTPException(status_code=404, detail="法宝套装不存在")
        return {"code": 200, "data": result}

    @admin_router.post("/sect")
    async def xiuxian_sect_api(payload: SectPayload, request: Request):
        token = request.headers.get("x-admin-token")
        init_data = request.headers.get("x-telegram-init-data")
        _verify_admin_credential(token, init_data)
        sect = create_sect_with_roles(
            name=payload.name,
            description=payload.description,
            image_url=payload.image_url,
            camp=payload.camp,
            min_realm_stage=payload.min_realm_stage,
            min_realm_layer=payload.min_realm_layer,
            min_stone=payload.min_stone,
            min_bone=payload.min_bone,
            min_comprehension=payload.min_comprehension,
            min_divine_sense=payload.min_divine_sense,
            min_fortune=payload.min_fortune,
            min_willpower=payload.min_willpower,
            min_charisma=payload.min_charisma,
            min_karma=payload.min_karma,
            min_body_movement=payload.min_body_movement,
            min_combat_power=payload.min_combat_power,
            attack_bonus=payload.attack_bonus,
            defense_bonus=payload.defense_bonus,
            duel_rate_bonus=payload.duel_rate_bonus,
            cultivation_bonus=payload.cultivation_bonus,
            fortune_bonus=payload.fortune_bonus,
            body_movement_bonus=payload.body_movement_bonus,
            salary_min_stay_days=payload.salary_min_stay_days,
            entry_hint=payload.entry_hint,
            roles=[item.model_dump() for item in payload.roles],
        )
        return {"code": 200, "data": sect}

    @admin_router.patch("/sect/{sect_id}")
    async def xiuxian_patch_sect_api(sect_id: int, payload: SectPayload, request: Request):
        token = request.headers.get("x-admin-token")
        init_data = request.headers.get("x-telegram-init-data")
        _verify_admin_credential(token, init_data)
        result = patch_sect(
            sect_id,
            name=payload.name,
            description=payload.description,
            image_url=payload.image_url,
            camp=payload.camp,
            min_realm_stage=payload.min_realm_stage,
            min_realm_layer=payload.min_realm_layer,
            min_stone=payload.min_stone,
            min_bone=payload.min_bone,
            min_comprehension=payload.min_comprehension,
            min_divine_sense=payload.min_divine_sense,
            min_fortune=payload.min_fortune,
            min_willpower=payload.min_willpower,
            min_charisma=payload.min_charisma,
            min_karma=payload.min_karma,
            min_body_movement=payload.min_body_movement,
            min_combat_power=payload.min_combat_power,
            attack_bonus=payload.attack_bonus,
            defense_bonus=payload.defense_bonus,
            duel_rate_bonus=payload.duel_rate_bonus,
            cultivation_bonus=payload.cultivation_bonus,
            fortune_bonus=payload.fortune_bonus,
            body_movement_bonus=payload.body_movement_bonus,
            salary_min_stay_days=payload.salary_min_stay_days,
            entry_hint=payload.entry_hint,
        )
        if result is None:
            raise HTTPException(status_code=404, detail="宗门不存在")
        result["roles"] = replace_sect_roles(sect_id, [item.model_dump() for item in payload.roles])
        return {"code": 200, "data": result}

    @admin_router.post("/sect/role")
    async def xiuxian_sect_role_assign_api(payload: SectRoleAssignPayload, request: Request):
        token = request.headers.get("x-admin-token")
        init_data = request.headers.get("x-telegram-init-data")
        _verify_admin_credential(token, init_data)
        return {"code": 200, "data": set_user_sect_role(payload.tg, payload.sect_id, payload.role_key)}

    @admin_router.post("/material")
    async def xiuxian_material_api(payload: MaterialPayload, request: Request):
        token = request.headers.get("x-admin-token")
        init_data = request.headers.get("x-telegram-init-data")
        _verify_admin_credential(token, init_data)
        return {"code": 200, "data": create_material(**payload.model_dump())}

    @admin_router.patch("/material/{material_id}")
    async def xiuxian_material_patch_api(material_id: int, payload: MaterialPayload, request: Request):
        token = request.headers.get("x-admin-token")
        init_data = request.headers.get("x-telegram-init-data")
        _verify_admin_credential(token, init_data)
        result = patch_material(material_id, **payload.model_dump())
        if result is None:
            raise HTTPException(status_code=404, detail="材料不存在")
        return {"code": 200, "data": result}

    @admin_router.post("/recipe")
    async def xiuxian_recipe_api(payload: RecipePayload, request: Request):
        token = request.headers.get("x-admin-token")
        init_data = request.headers.get("x-telegram-init-data")
        _verify_admin_credential(token, init_data)
        recipe = create_recipe_with_ingredients(
            name=payload.name,
            recipe_kind=payload.recipe_kind,
            result_kind=payload.result_kind,
            result_ref_id=payload.result_ref_id,
            result_quantity=payload.result_quantity,
            base_success_rate=payload.base_success_rate,
            broadcast_on_success=payload.broadcast_on_success,
            ingredients=[item.model_dump() for item in payload.ingredients],
        )
        return {"code": 200, "data": recipe}

    @admin_router.patch("/recipe/{recipe_id}")
    async def xiuxian_recipe_patch_api(recipe_id: int, payload: RecipePayload, request: Request):
        token = request.headers.get("x-admin-token")
        init_data = request.headers.get("x-telegram-init-data")
        _verify_admin_credential(token, init_data)
        recipe = patch_recipe_with_ingredients(
            recipe_id,
            name=payload.name,
            recipe_kind=payload.recipe_kind,
            result_kind=payload.result_kind,
            result_ref_id=payload.result_ref_id,
            result_quantity=payload.result_quantity,
            base_success_rate=payload.base_success_rate,
            broadcast_on_success=payload.broadcast_on_success,
            ingredients=[item.model_dump() for item in payload.ingredients],
        )
        return {"code": 200, "data": recipe}

    @admin_router.post("/scene")
    async def xiuxian_scene_api(payload: ScenePayload, request: Request):
        token = request.headers.get("x-admin-token")
        init_data = request.headers.get("x-telegram-init-data")
        _verify_admin_credential(token, init_data)
        scene = create_scene_with_drops(
            name=payload.name,
            description=payload.description,
            image_url=payload.image_url,
            max_minutes=payload.max_minutes,
            min_realm_stage=payload.min_realm_stage,
            min_realm_layer=payload.min_realm_layer,
            min_combat_power=payload.min_combat_power,
            event_pool=[item.model_dump() for item in payload.event_pool],
            drops=[item.model_dump() for item in payload.drops],
        )
        return {"code": 200, "data": scene}

    @admin_router.patch("/scene/{scene_id}")
    async def xiuxian_scene_patch_api(scene_id: int, payload: ScenePayload, request: Request):
        token = request.headers.get("x-admin-token")
        init_data = request.headers.get("x-telegram-init-data")
        _verify_admin_credential(token, init_data)
        scene = patch_scene_with_drops(
            scene_id,
            name=payload.name,
            description=payload.description,
            image_url=payload.image_url,
            max_minutes=payload.max_minutes,
            min_realm_stage=payload.min_realm_stage,
            min_realm_layer=payload.min_realm_layer,
            min_combat_power=payload.min_combat_power,
            event_pool=[item.model_dump() for item in payload.event_pool],
            drops=[item.model_dump() for item in payload.drops],
        )
        return {"code": 200, "data": scene}

    @admin_router.post("/encounter")
    async def xiuxian_encounter_api(payload: EncounterPayload, request: Request):
        token = request.headers.get("x-admin-token")
        init_data = request.headers.get("x-telegram-init-data")
        _verify_admin_credential(token, init_data)
        encounter = create_encounter_template(**payload.model_dump())
        return {"code": 200, "data": encounter}

    @admin_router.patch("/encounter/{encounter_id}")
    async def xiuxian_encounter_patch_api(encounter_id: int, payload: EncounterPayload, request: Request):
        token = request.headers.get("x-admin-token")
        init_data = request.headers.get("x-telegram-init-data")
        _verify_admin_credential(token, init_data)
        encounter = patch_encounter_template(encounter_id, **payload.model_dump())
        if encounter is None:
            raise HTTPException(status_code=404, detail="Encounter not found")
        return {"code": 200, "data": encounter}

    @admin_router.post("/encounter/dispatch")
    async def xiuxian_encounter_dispatch_api(payload: EncounterDispatchPayload, request: Request):
        token = request.headers.get("x-admin-token")
        init_data = request.headers.get("x-telegram-init-data")
        _verify_admin_credential(token, init_data)
        chat_id = int(payload.group_chat_id or _main_group_chat_id() or 0)
        if not chat_id:
            raise HTTPException(status_code=400, detail="当前未配置可投放奇遇的群组。")
        encounter_payload = spawn_group_encounter(chat_id, template_id=payload.template_id)
        message_payload = await _push_group_encounter_notice(encounter_payload)
        return {"code": 200, "data": {"encounter": encounter_payload, "message": message_payload}}

    @admin_router.post("/task")
    async def xiuxian_admin_task_api(payload: AdminTaskPayload, request: Request):
        token = request.headers.get("x-admin-token")
        init_data = request.headers.get("x-telegram-init-data")
        _verify_admin_credential(token, init_data)
        task = create_bounty_task(
            actor_tg=None,
            title=payload.title,
            description=payload.description,
            task_scope=payload.task_scope,
            task_type=payload.task_type,
            question_text=payload.question_text,
            answer_text=payload.answer_text,
            image_url=payload.image_url,
            required_item_kind=payload.required_item_kind,
            required_item_ref_id=payload.required_item_ref_id,
            required_item_quantity=payload.required_item_quantity,
            reward_stone=payload.reward_stone,
            reward_item_kind=payload.reward_item_kind,
            reward_item_ref_id=payload.reward_item_ref_id,
            reward_item_quantity=payload.reward_item_quantity,
            max_claimants=payload.max_claimants,
            sect_id=payload.sect_id,
            active_in_group=payload.active_in_group,
            group_chat_id=payload.group_chat_id or _main_group_chat_id(),
        )
        if task.get("active_in_group"):
            task, push_warning = await _safe_push_task_to_group(task)
            if push_warning:
                task["push_warning"] = push_warning
        return {"code": 200, "data": task}

    @admin_router.post("/grant")
    async def xiuxian_grant_api(payload: GrantPayload, request: Request):
        token = request.headers.get("x-admin-token")
        init_data = request.headers.get("x-telegram-init-data")
        _verify_admin_credential(token, init_data)
        result = grant_item_to_user(payload.tg, payload.item_kind, payload.item_ref_id, payload.quantity)
        return {"code": 200, "data": result}

    @admin_router.post("/shop/official")
    async def xiuxian_official_shop_api(payload: OfficialShopPayload, request: Request):
        token = request.headers.get("x-admin-token")
        init_data = request.headers.get("x-telegram-init-data")
        _verify_admin_credential(token, init_data)
        result = create_official_shop_listing(
            item_kind=payload.item_kind,
            item_ref_id=payload.item_ref_id,
            quantity=payload.quantity,
            price_stone=payload.price_stone,
            shop_name=payload.shop_name,
        )
        return {"code": 200, "data": result}

    @admin_router.patch("/shop/{item_id}")
    async def xiuxian_patch_shop_api(item_id: int, payload: OfficialShopPatchPayload, request: Request):
        token = request.headers.get("x-admin-token")
        init_data = request.headers.get("x-telegram-init-data")
        _verify_admin_credential(token, init_data)
        patch = {key: value for key, value in payload.model_dump().items() if value is not None}
        result = patch_shop_listing(item_id, **patch)
        if result is None:
            raise HTTPException(status_code=404, detail="Shop item not found")
        return {"code": 200, "data": result}

    @admin_router.delete("/artifact/{artifact_id}")
    async def xiuxian_delete_artifact_api(artifact_id: int, request: Request):
        _verify_admin_credential(request.headers.get("x-admin-token"), request.headers.get("x-telegram-init-data"))
        if not delete_artifact(artifact_id):
            raise HTTPException(status_code=404, detail="Artifact not found")
        return {"code": 200, "data": {"deleted": True, "id": artifact_id}}

    @admin_router.delete("/artifact-set/{artifact_set_id}")
    async def xiuxian_delete_artifact_set_api(artifact_set_id: int, request: Request):
        _verify_admin_credential(request.headers.get("x-admin-token"), request.headers.get("x-telegram-init-data"))
        if not delete_artifact_set(artifact_set_id):
            raise HTTPException(status_code=404, detail="Artifact set not found")
        return {"code": 200, "data": {"deleted": True, "id": artifact_set_id}}

    @admin_router.delete("/pill/{pill_id}")
    async def xiuxian_delete_pill_api(pill_id: int, request: Request):
        _verify_admin_credential(request.headers.get("x-admin-token"), request.headers.get("x-telegram-init-data"))
        if not delete_pill(pill_id):
            raise HTTPException(status_code=404, detail="Pill not found")
        return {"code": 200, "data": {"deleted": True, "id": pill_id}}

    @admin_router.delete("/talisman/{talisman_id}")
    async def xiuxian_delete_talisman_api(talisman_id: int, request: Request):
        _verify_admin_credential(request.headers.get("x-admin-token"), request.headers.get("x-telegram-init-data"))
        if not delete_talisman(talisman_id):
            raise HTTPException(status_code=404, detail="Talisman not found")
        return {"code": 200, "data": {"deleted": True, "id": talisman_id}}

    @admin_router.delete("/technique/{technique_id}")
    async def xiuxian_delete_technique_api(technique_id: int, request: Request):
        _verify_admin_credential(request.headers.get("x-admin-token"), request.headers.get("x-telegram-init-data"))
        if not delete_technique(technique_id):
            raise HTTPException(status_code=404, detail="Technique not found")
        return {"code": 200, "data": {"deleted": True, "id": technique_id}}

    @admin_router.delete("/title/{title_id}")
    async def xiuxian_delete_title_api(title_id: int, request: Request):
        _verify_admin_credential(request.headers.get("x-admin-token"), request.headers.get("x-telegram-init-data"))
        if not delete_title(title_id):
            raise HTTPException(status_code=404, detail="Title not found")
        return {"code": 200, "data": {"deleted": True, "id": title_id}}

    @admin_router.delete("/achievement/{achievement_id}")
    async def xiuxian_delete_achievement_api(achievement_id: int, request: Request):
        _verify_admin_credential(request.headers.get("x-admin-token"), request.headers.get("x-telegram-init-data"))
        if not delete_achievement(achievement_id):
            raise HTTPException(status_code=404, detail="Achievement not found")
        return {"code": 200, "data": {"deleted": True, "id": achievement_id}}

    @admin_router.delete("/sect/{sect_id}")
    async def xiuxian_delete_sect_api(sect_id: int, request: Request):
        _verify_admin_credential(request.headers.get("x-admin-token"), request.headers.get("x-telegram-init-data"))
        if not delete_sect(sect_id):
            raise HTTPException(status_code=404, detail="Sect not found")
        return {"code": 200, "data": {"deleted": True, "id": sect_id}}

    @admin_router.delete("/material/{material_id}")
    async def xiuxian_delete_material_api(material_id: int, request: Request):
        _verify_admin_credential(request.headers.get("x-admin-token"), request.headers.get("x-telegram-init-data"))
        if not delete_material(material_id):
            raise HTTPException(status_code=404, detail="Material not found")
        return {"code": 200, "data": {"deleted": True, "id": material_id}}

    @admin_router.delete("/recipe/{recipe_id}")
    async def xiuxian_delete_recipe_api(recipe_id: int, request: Request):
        _verify_admin_credential(request.headers.get("x-admin-token"), request.headers.get("x-telegram-init-data"))
        if not delete_recipe(recipe_id):
            raise HTTPException(status_code=404, detail="Recipe not found")
        return {"code": 200, "data": {"deleted": True, "id": recipe_id}}

    @admin_router.delete("/scene/{scene_id}")
    async def xiuxian_delete_scene_api(scene_id: int, request: Request):
        _verify_admin_credential(request.headers.get("x-admin-token"), request.headers.get("x-telegram-init-data"))
        if not delete_scene(scene_id):
            raise HTTPException(status_code=404, detail="Scene not found")
        return {"code": 200, "data": {"deleted": True, "id": scene_id}}

    @admin_router.delete("/encounter/{encounter_id}")
    async def xiuxian_delete_encounter_api(encounter_id: int, request: Request):
        _verify_admin_credential(request.headers.get("x-admin-token"), request.headers.get("x-telegram-init-data"))
        if not delete_encounter_template(encounter_id):
            raise HTTPException(status_code=404, detail="Encounter not found")
        return {"code": 200, "data": {"deleted": True, "id": encounter_id}}

    @admin_router.delete("/task/{task_id}")
    async def xiuxian_delete_task_api(task_id: int, request: Request):
        _verify_admin_credential(request.headers.get("x-admin-token"), request.headers.get("x-telegram-init-data"))
        if not delete_task(task_id):
            raise HTTPException(status_code=404, detail="Task not found")
        return {"code": 200, "data": {"deleted": True, "id": task_id}}

    @admin_router.get("/players")
    async def xiuxian_admin_players_api(request: Request, q: str = "", page: int = 1, page_size: int = 10):
        token = request.headers.get("x-admin-token")
        init_data = request.headers.get("x-telegram-init-data")
        _verify_admin_credential(token, init_data)
        result = search_xiuxian_players(query=q or None, page=page, page_size=page_size)
        items = result.get("items") or []
        identities = await asyncio.gather(
            *(_refresh_profile_identity_from_telegram(int(item["tg"])) for item in items),
            return_exceptions=True,
        )
        result["items"] = [
            _merge_profile_identity(
                item,
                None if isinstance(identity, Exception) else identity,
            )
            for item, identity in zip(items, identities)
        ]
        return {"code": 200, "data": result}

    @admin_router.post("/system/realm-migrate")
    async def xiuxian_admin_realm_migrate_api(request: Request):
        token = request.headers.get("x-admin-token")
        init_data = request.headers.get("x-telegram-init-data")
        _verify_admin_credential(token, init_data)
        result = admin_migrate_all_profile_realms()
        return {"code": 200, "data": result}

    @admin_router.post("/system/reset-player-data")
    async def xiuxian_admin_reset_player_data_api(request: Request):
        token = request.headers.get("x-admin-token")
        init_data = request.headers.get("x-telegram-init-data")
        _verify_admin_credential(token, init_data)
        result = admin_clear_all_xiuxian_data()
        return {"code": 200, "data": result}

    @admin_router.get("/players/{tg}")
    async def xiuxian_admin_player_detail_api(tg: int, request: Request):
        token = request.headers.get("x-admin-token")
        init_data = request.headers.get("x-telegram-init-data")
        _verify_admin_credential(token, init_data)
        return {"code": 200, "data": await _admin_player_bundle_payload(tg)}

    @admin_router.patch("/players/{tg}")
    async def xiuxian_admin_player_patch_api(tg: int, payload: PlayerPatchPayload, request: Request):
        token = request.headers.get("x-admin-token")
        init_data = request.headers.get("x-telegram-init-data")
        _verify_admin_credential(token, init_data)
        patch = {key: value for key, value in payload.model_dump().items() if value is not None}
        result = admin_patch_player(tg, **patch)
        if result is None:
            raise HTTPException(status_code=404, detail="Player not found")
        create_journal(tg, "admin", "主人修改", f"主人修改了属性: {', '.join(patch.keys())}")
        return {"code": 200, "data": await _admin_player_bundle_payload(tg)}

    @admin_router.post("/players/{tg}/resource/grant")
    async def xiuxian_admin_player_grant_resource_api(tg: int, payload: PlayerResourceGrantPayload, request: Request):
        token = request.headers.get("x-admin-token")
        init_data = request.headers.get("x-telegram-init-data")
        _verify_admin_credential(token, init_data)
        admin_grant_player_resource(
            tg,
            payload.item_kind,
            payload.item_ref_id,
            quantity=payload.quantity,
            equip=payload.equip,
        )
        create_journal(tg, "admin", "主人发放", f"主人发放了 {payload.item_kind}:{payload.item_ref_id}")
        return {"code": 200, "data": await _admin_player_bundle_payload(tg)}

    @admin_router.post("/players/{tg}/resource/inventory")
    async def xiuxian_admin_player_inventory_api(tg: int, payload: PlayerInventoryPayload, request: Request):
        token = request.headers.get("x-admin-token")
        init_data = request.headers.get("x-telegram-init-data")
        _verify_admin_credential(token, init_data)
        admin_set_player_inventory(
            tg,
            payload.item_kind,
            payload.item_ref_id,
            payload.quantity,
            payload.bound_quantity,
        )
        create_journal(tg, "admin", "主人调包", f"主人调整了背包: {payload.item_kind}:{payload.item_ref_id}")
        return {"code": 200, "data": await _admin_player_bundle_payload(tg)}

    @admin_router.post("/players/{tg}/resource/select")
    async def xiuxian_admin_player_select_resource_api(tg: int, payload: PlayerSelectionPayload, request: Request):
        token = request.headers.get("x-admin-token")
        init_data = request.headers.get("x-telegram-init-data")
        _verify_admin_credential(token, init_data)
        admin_set_player_selection(tg, payload.selection_kind, payload.item_ref_id)
        target = f"{payload.selection_kind}:{payload.item_ref_id or 0}"
        create_journal(tg, "admin", "主人设定", f"主人切换了当前配置: {target}")
        return {"code": 200, "data": await _admin_player_bundle_payload(tg)}

    @admin_router.post("/players/{tg}/resource/revoke")
    async def xiuxian_admin_player_revoke_resource_api(tg: int, payload: PlayerRevokePayload, request: Request):
        token = request.headers.get("x-admin-token")
        init_data = request.headers.get("x-telegram-init-data")
        _verify_admin_credential(token, init_data)
        admin_revoke_player_resource(tg, payload.item_kind, payload.item_ref_id)
        create_journal(tg, "admin", "主人回收", f"主人移除了 {payload.item_kind}:{payload.item_ref_id}")
        return {"code": 200, "data": await _admin_player_bundle_payload(tg)}

    app.include_router(user_router)
    app.include_router(admin_router)

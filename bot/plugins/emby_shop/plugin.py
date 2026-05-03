from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit
from uuid import uuid4

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from bot import LOGGER, api as api_config, bot, config, group, owner
from bot.plugins import list_miniapp_plugins
from bot.sql_helper.sql_emby import sql_get_emby
from bot.sql_helper.sql_invite import (
    INVITE_CREDIT_TYPE_ACCOUNT_OPEN,
    INVITE_CREDIT_TYPE_GROUP,
)
from bot.sql_helper.sql_shop import (
    create_shop_item,
    delete_shop_item,
    get_shop_item,
    get_shop_settings,
    list_shop_items,
    list_shop_orders,
    purchase_shop_item,
    set_shop_settings,
    update_shop_item,
)
from bot.web.api.miniapp import is_admin_user_id, verify_init_data
from bot.web.presenters import serialize_emby_user


PLUGIN_ROOT = Path(__file__).resolve().parent
STATIC_DIR = PLUGIN_ROOT / "static"
DATA_DIR = PLUGIN_ROOT.parent.parent.parent / "data"
UPLOAD_DIR = DATA_DIR / "shop_uploads"
PLUGIN_MANIFEST = json.loads((PLUGIN_ROOT / "plugin.json").read_text(encoding="utf-8"))
MAX_UPLOAD_BYTES = 8 * 1024 * 1024
ALLOWED_IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
ALLOWED_IMAGE_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}


class InitDataPayload(BaseModel):
    init_data: str


class AdminBootstrapPayload(BaseModel):
    token: str | None = None
    init_data: str | None = None


class ShopSettingsPayload(BaseModel):
    allow_user_listing: bool | None = None
    currency_name: str | None = None
    shop_title: str | None = None
    shop_notice: str | None = None


class ShopItemPayload(BaseModel):
    title: str
    description: str = ""
    image_url: str = ""
    delivery_text: str = ""
    item_type: str = "digital"
    invite_credit_quantity: int = 0
    price_iv: int = 0
    stock: int = 1
    notify_group: bool = False
    official: bool = True
    enabled: bool = True


class ShopItemPatchPayload(BaseModel):
    title: str | None = None
    description: str | None = None
    image_url: str | None = None
    delivery_text: str | None = None
    item_type: str | None = None
    invite_credit_quantity: int | None = None
    price_iv: int | None = None
    stock: int | None = None
    notify_group: bool | None = None
    official: bool | None = None
    enabled: bool | None = None


class ShopPurchasePayload(InitDataPayload):
    item_id: int
    quantity: int = 1


class UserListingPayload(InitDataPayload):
    title: str
    description: str = ""
    image_url: str = ""
    delivery_text: str = ""
    price_iv: int = 0
    stock: int = 1
    notify_group: bool = False


def _item_invite_credit_type(item_type: str | None) -> str | None:
    normalized = str(item_type or "").strip().lower()
    if normalized in {"invite_credit", "group_invite_credit"}:
        return INVITE_CREDIT_TYPE_GROUP
    if normalized == "account_open_credit":
        return INVITE_CREDIT_TYPE_ACCOUNT_OPEN
    return None


def _item_invite_label(item_type: str | None) -> str:
    return "注册资格" if _item_invite_credit_type(item_type) == INVITE_CREDIT_TYPE_ACCOUNT_OPEN else "入群资格"


def _invite_credit_purchase_disabled_message(invite_credit_type: str | None) -> str:
    if invite_credit_type == INVITE_CREDIT_TYPE_GROUP:
        return "入群资格已改为拥有观影资格后自动获得一次，暂不支持商店购买"
    if invite_credit_type == INVITE_CREDIT_TYPE_ACCOUNT_OPEN:
        return "注册资格已改为申请制，暂不支持商店购买"
    return "该邀请资格暂不支持购买"


def _public_url_root(base_url: str | None = None) -> str:
    if api_config.public_url:
        return str(api_config.public_url).rstrip("/")
    return str(base_url or "").rstrip("/")


def _sanitize_upload_folder(folder: str | None) -> str:
    raw = (folder or "misc").strip().replace("\\", "/")
    parts = []
    for part in raw.split("/"):
        clean = "".join(ch for ch in part.lower() if ch.isalnum() or ch in {"-", "_"})
        if clean:
            parts.append(clean)
    return "/".join(parts[:3]) or "misc"


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
        if not upload_path.startswith("/plugins/shop/uploads/"):
            return image_url
    if upload_path.startswith("/plugins/shop/uploads/"):
        relative_path = upload_path.removeprefix("/plugins/shop/uploads/").strip("/")
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
        suffix = {
            "image/jpeg": ".jpg",
            "image/png": ".png",
            "image/webp": ".webp",
            "image/gif": ".gif",
        }.get(content_type, ".jpg")

    payload = await file.read()
    if not payload:
        raise HTTPException(status_code=400, detail="上传图片不能为空")
    if len(payload) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=400, detail="图片大小不能超过 8MB")

    subdir = _sanitize_upload_folder(folder)
    target_dir = UPLOAD_DIR / subdir
    target_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{uuid4().hex}{suffix}"
    target = target_dir / filename
    target.write_bytes(payload)
    relative_url = f"/plugins/shop/uploads/{subdir}/{filename}"
    public_root = _public_url_root(base_url)
    return {
        "name": filename,
        "size": len(payload),
        "relative_url": relative_url,
        "url": f"{public_root}{relative_url}" if public_root else relative_url,
    }


def _verify_user_from_init_data(init_data: str) -> dict[str, Any]:
    verified = verify_init_data(init_data)
    return verified["user"]


def _verify_admin_credential(token: str | None, init_data: str | None) -> dict[str, Any]:
    expected_token = api_config.admin_token or ""
    if token and token == expected_token:
        return {"id": owner, "auth": "token"}
    if init_data:
        user = _verify_user_from_init_data(init_data)
        if is_admin_user_id(user["id"]):
            user["auth"] = "telegram"
            return user
        raise HTTPException(status_code=403, detail="当前 Telegram 账号没有后台权限")
    raise HTTPException(status_code=401, detail="缺少后台登录凭证")


def _can_user_publish(user_id: int) -> bool:
    if is_admin_user_id(user_id):
        return True
    return bool(get_shop_settings().get("allow_user_listing", False))


def _main_group_chat_id() -> int | None:
    for value in group:
        try:
            return int(value)
        except (TypeError, ValueError):
            continue
    return None


async def _send_group_notice(text: str, image_url: str | None = None) -> None:
    chat_id = _main_group_chat_id()
    if not chat_id:
        return
    photo = _resolve_group_image_source(image_url)
    try:
        if photo:
            await bot.send_photo(chat_id=chat_id, photo=photo, caption=text)
        else:
            await bot.send_message(chat_id=chat_id, text=text)
    except Exception as exc:
        LOGGER.warning(f"shop group notice failed: {exc}")


async def _notify_item_published(item: dict[str, Any]) -> None:
    if not item.get("notify_group"):
        return
    owner_text = item.get("owner_display_name") or (f"@{item['owner_username']}" if item.get("owner_username") else "官方")
    text = (
        f"🛒 商店上新：{item['title']}\n"
        f"售价：{item['price_iv']} {get_shop_settings().get('currency_name')}\n"
        f"库存：{item['stock']}\n"
        f"卖家：{owner_text}"
    )
    await _send_group_notice(text, item.get("image_url"))


async def _deliver_order_notice(
    *,
    buyer_tg: int,
    item: dict[str, Any],
    order: dict[str, Any],
    seller_tg: int | None = None,
) -> None:
    currency_name = get_shop_settings().get("currency_name")
    delivery_text = item.get("delivery_text") or "卖家未填写自动发货内容，请联系管理员处理。"
    invite_credit_type = _item_invite_credit_type(item.get("item_type"))
    if invite_credit_type:
        invite_count = max(int(item.get("invite_credit_quantity") or 1), 1) * max(int(order.get("quantity") or 1), 1)
        invite_label = _item_invite_label(item.get("item_type"))
        delivery_text = (
            f"本次购买已为你增加 {invite_count} 次{invite_label}。\n"
            + (
                "请进入 miniapp 主页的“入群资格邀请”模块，为指定 TGID 发送一次性入群链接。"
                if invite_credit_type == INVITE_CREDIT_TYPE_GROUP
                else "请进入 miniapp 主页的“注册资格申请”模块，把申请提交给后台审核。"
            )
        )
    buyer_text = (
        f"🎁 你已成功购买《{item['title']}》\n"
        f"订单号：#{order['id']}\n"
        f"支付：{order['total_price_iv']} {currency_name}\n\n"
        f"{delivery_text}"
    )
    try:
        photo = _resolve_group_image_source(item.get("image_url"))
        if photo:
            await bot.send_photo(chat_id=buyer_tg, photo=photo, caption=buyer_text)
        else:
            await bot.send_message(chat_id=buyer_tg, text=buyer_text)
    except Exception as exc:
        LOGGER.warning(f"shop buyer delivery failed tg={buyer_tg}: {exc}")

    if seller_tg:
        try:
            await bot.send_message(
                chat_id=seller_tg,
                text=(
                    f"💸 你的商品《{item['title']}》已售出\n"
                    f"订单号：#{order['id']}\n"
                    f"收入：{order['total_price_iv']} {currency_name}"
                ),
            )
        except Exception as exc:
            LOGGER.warning(f"shop seller notice failed tg={seller_tg}: {exc}")

    if item.get("notify_group"):
        await _send_group_notice(
            f"🛍️ 群内成交：{item['title']} 已售出，订单 #{order['id']}，成交价 {order['total_price_iv']} {currency_name}。",
            item.get("image_url"),
        )


def _serialize_shop_bundle(user_id: int | None = None, *, include_orders: bool = False) -> dict[str, Any]:
    account = sql_get_emby(user_id) if user_id is not None else None
    is_admin = bool(user_id is not None and is_admin_user_id(user_id))
    payload = {
        "meta": {
            "plugin_name": PLUGIN_MANIFEST.get("name"),
            "version": PLUGIN_MANIFEST.get("version"),
            "bottom_nav": _build_bottom_nav(),
        },
        "settings": get_shop_settings(),
        "items": list_shop_items(enabled_only=not include_orders),
        "orders": list_shop_orders(limit=20) if include_orders else [],
        "my_items": list_shop_items(enabled_only=False, owner_tg=user_id) if user_id is not None else [],
        "account": None if account is None else serialize_emby_user(account),
        "permissions": {
            "is_admin": is_admin,
            "can_publish": bool(user_id is not None and _can_user_publish(user_id)),
            "admin_url": "/plugins/shop/admin" if is_admin else None,
        },
    }
    return payload


def _build_bottom_nav() -> list[dict[str, str]]:
    items = [
        {
            "id": "home",
            "label": "主页",
            "path": "/miniapp",
            "icon": "🏠",
        }
    ]

    for plugin in list_miniapp_plugins():
        if not plugin.get("enabled") or not plugin.get("loaded") or not plugin.get("web_registered"):
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


def register_web(app) -> None:
    user_router = APIRouter(prefix="/plugins/shop", tags=["shop-user"])
    admin_router = APIRouter(prefix="/plugins/shop/admin-api", tags=["shop-admin"])

    if STATIC_DIR.exists():
        app.mount("/plugins/shop/static", StaticFiles(directory=STATIC_DIR), name="shop-static")
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    app.mount("/plugins/shop/uploads", StaticFiles(directory=UPLOAD_DIR), name="shop-uploads")

    @user_router.get("/app")
    async def shop_app_page():
        return FileResponse(STATIC_DIR / "app.html")

    @user_router.get("/admin")
    async def shop_admin_page():
        return FileResponse(STATIC_DIR / "admin.html")

    @user_router.post("/api/bootstrap")
    async def shop_bootstrap(payload: InitDataPayload):
        user = await run_in_threadpool(_verify_user_from_init_data, payload.init_data)
        bundle = await run_in_threadpool(_serialize_shop_bundle, int(user["id"]))
        return {"code": 200, "data": bundle}

    @user_router.post("/api/listing")
    async def shop_create_listing(payload: UserListingPayload):
        user = _verify_user_from_init_data(payload.init_data)
        if not _can_user_publish(int(user["id"])):
            raise HTTPException(status_code=403, detail="当前未开放普通用户上架商品")
        display_name = " ".join(part for part in [user.get("first_name"), user.get("last_name")] if part).strip()
        item = create_shop_item(
            owner_tg=int(user["id"]),
            owner_display_name=display_name,
            owner_username=str(user.get("username") or "").lstrip("@"),
            title=payload.title,
            description=payload.description,
            image_url=payload.image_url,
            delivery_text=payload.delivery_text,
            item_type="digital",
            invite_credit_quantity=0,
            price_iv=payload.price_iv,
            stock=payload.stock,
            notify_group=payload.notify_group,
            official=False,
            enabled=True,
        )
        await _notify_item_published(item)
        return {"code": 200, "data": {"item": item, **_serialize_shop_bundle(int(user["id"]))}}

    @user_router.post("/api/purchase")
    async def shop_purchase(payload: ShopPurchasePayload):
        user = _verify_user_from_init_data(payload.init_data)
        item = get_shop_item(payload.item_id)
        if item is None:
            raise HTTPException(status_code=404, detail="商品不存在")
        invite_credit_type = _item_invite_credit_type(item.get("item_type"))
        if invite_credit_type:
            raise HTTPException(status_code=403, detail=_invite_credit_purchase_disabled_message(invite_credit_type))
        result = purchase_shop_item(buyer_tg=int(user["id"]), item_id=payload.item_id, quantity=payload.quantity)
        granted_invites = []
        result_invite_type = _item_invite_credit_type(result["item"].get("item_type"))
        if result_invite_type:
            raise HTTPException(status_code=403, detail=_invite_credit_purchase_disabled_message(result_invite_type))
        await _deliver_order_notice(
            buyer_tg=int(user["id"]),
            item=result["item"],
            order=result["order"],
            seller_tg=result["order"].get("seller_tg"),
        )
        bundle = _serialize_shop_bundle(int(user["id"]))
        bundle["last_order"] = result["order"]
        bundle["buyer_balance"] = result["buyer_balance"]
        bundle["granted_invites"] = granted_invites
        return {"code": 200, "data": bundle}

    @user_router.post("/api/upload-image")
    async def shop_upload_image_api(
        request: Request,
        folder: str = Form("user"),
        file: UploadFile = File(...),
    ):
        init_data = request.headers.get("x-telegram-init-data")
        user = _verify_user_from_init_data(init_data or "")
        if not _can_user_publish(int(user["id"])):
            raise HTTPException(status_code=403, detail="当前未开放普通用户上架商品")
        return {"code": 200, "data": await _save_uploaded_image(file, folder, str(request.base_url))}

    @admin_router.post("/bootstrap")
    async def shop_admin_bootstrap(payload: AdminBootstrapPayload):
        admin_user = await run_in_threadpool(_verify_admin_credential, payload.token, payload.init_data)
        bundle = await run_in_threadpool(lambda: _serialize_shop_bundle(admin_user.get("id"), include_orders=True))
        return {
            "code": 200,
            "data": {
                "admin_user": admin_user,
                **bundle,
            },
        }

    @admin_router.post("/settings")
    async def shop_settings_api(payload: ShopSettingsPayload, request: Request):
        token = request.headers.get("x-admin-token")
        init_data = request.headers.get("x-telegram-init-data")
        _verify_admin_credential(token, init_data)
        settings = set_shop_settings(payload.model_dump(exclude_unset=True))
        return {"code": 200, "data": settings}

    @admin_router.post("/item")
    async def shop_item_api(payload: ShopItemPayload, request: Request):
        token = request.headers.get("x-admin-token")
        init_data = request.headers.get("x-telegram-init-data")
        admin_user = _verify_admin_credential(token, init_data)
        item = create_shop_item(
            owner_tg=int(admin_user.get("id")) if admin_user.get("id") is not None else None,
            owner_display_name=admin_user.get("first_name") or "官方",
            owner_username=str(admin_user.get("username") or "").lstrip("@"),
            title=payload.title,
            description=payload.description,
            image_url=payload.image_url,
            delivery_text=payload.delivery_text,
            item_type=payload.item_type,
            invite_credit_quantity=payload.invite_credit_quantity,
            price_iv=payload.price_iv,
            stock=payload.stock,
            notify_group=payload.notify_group,
            official=payload.official,
            enabled=payload.enabled,
        )
        await _notify_item_published(item)
        return {"code": 200, "data": {"item": item, "items": list_shop_items(enabled_only=False), "orders": list_shop_orders(limit=20)}}

    @admin_router.patch("/item/{item_id}")
    async def shop_item_patch_api(item_id: int, payload: ShopItemPatchPayload, request: Request):
        token = request.headers.get("x-admin-token")
        init_data = request.headers.get("x-telegram-init-data")
        _verify_admin_credential(token, init_data)
        item = update_shop_item(item_id, **payload.model_dump(exclude_unset=True))
        if item is None:
            raise HTTPException(status_code=404, detail="商品不存在")
        return {"code": 200, "data": {"item": item, "items": list_shop_items(enabled_only=False)}}

    @admin_router.delete("/item/{item_id}")
    async def shop_item_delete_api(item_id: int, request: Request):
        token = request.headers.get("x-admin-token")
        init_data = request.headers.get("x-telegram-init-data")
        _verify_admin_credential(token, init_data)
        deleted = delete_shop_item(item_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="商品不存在")
        return {"code": 200, "data": {"deleted": True, "items": list_shop_items(enabled_only=False)}}

    @admin_router.post("/upload-image")
    async def shop_admin_upload_api(
        request: Request,
        folder: str = Form("admin"),
        file: UploadFile = File(...),
    ):
        token = request.headers.get("x-admin-token")
        init_data = request.headers.get("x-telegram-init-data")
        _verify_admin_credential(token, init_data)
        return {"code": 200, "data": await _save_uploaded_image(file, folder, str(request.base_url))}

    app.include_router(user_router)
    app.include_router(admin_router)


def register_bot(_bot) -> None:
    return None

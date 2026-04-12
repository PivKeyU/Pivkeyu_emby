from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import JSON, BigInteger, Boolean, Column, DateTime, ForeignKey, Integer, String, Text

from bot import pivkeyu
from bot.sql_helper import Base, Session
from bot.sql_helper.sql_emby import Emby


UTC_TZ = timezone.utc
SHANGHAI_TZ = timezone(timedelta(hours=8))
DEFAULT_SHOP_SETTINGS = {
    "allow_user_listing": False,
    # 商店默认沿用全局配置中的货币名称。
    "currency_name": pivkeyu,
    "shop_title": "仙舟小铺",
    "shop_notice": "欢迎使用 Emby 货币购买数字商品。",
}


def utcnow() -> datetime:
    return datetime.utcnow()


def serialize_datetime(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC_TZ)
    return value.astimezone(SHANGHAI_TZ).isoformat()


class ShopSetting(Base):
    __tablename__ = "shop_settings"

    setting_key = Column(String(64), primary_key=True)
    setting_value = Column(JSON, nullable=True)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)


class ShopItem(Base):
    __tablename__ = "shop_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    owner_tg = Column(BigInteger, nullable=True)
    owner_display_name = Column(String(128), nullable=True)
    owner_username = Column(String(64), nullable=True)
    title = Column(String(128), nullable=False)
    description = Column(Text, nullable=True)
    image_url = Column(String(512), nullable=True)
    delivery_text = Column(Text, nullable=True)
    price_iv = Column(Integer, default=0, nullable=False)
    stock = Column(Integer, default=0, nullable=False)
    sold_count = Column(Integer, default=0, nullable=False)
    notify_group = Column(Boolean, default=False, nullable=False)
    official = Column(Boolean, default=False, nullable=False)
    enabled = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=utcnow, nullable=False)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)


class ShopOrder(Base):
    __tablename__ = "shop_orders"

    id = Column(Integer, primary_key=True, autoincrement=True)
    item_id = Column(Integer, ForeignKey("shop_items.id", ondelete="SET NULL"), nullable=True)
    buyer_tg = Column(BigInteger, nullable=False)
    seller_tg = Column(BigInteger, nullable=True)
    item_title = Column(String(128), nullable=False)
    image_url = Column(String(512), nullable=True)
    delivery_text = Column(Text, nullable=True)
    quantity = Column(Integer, default=1, nullable=False)
    unit_price_iv = Column(Integer, default=0, nullable=False)
    total_price_iv = Column(Integer, default=0, nullable=False)
    status = Column(String(32), default="delivered", nullable=False)
    created_at = Column(DateTime, default=utcnow, nullable=False)


def serialize_shop_item(item: ShopItem | None) -> dict[str, Any] | None:
    if item is None:
        return None
    return {
        "id": item.id,
        "owner_tg": item.owner_tg,
        "owner_display_name": item.owner_display_name,
        "owner_username": item.owner_username,
        "title": item.title,
        "description": item.description or "",
        "image_url": item.image_url or "",
        "delivery_text": item.delivery_text or "",
        "price_iv": int(item.price_iv or 0),
        "stock": int(item.stock or 0),
        "sold_count": int(item.sold_count or 0),
        "notify_group": bool(item.notify_group),
        "official": bool(item.official),
        "enabled": bool(item.enabled),
        "created_at": serialize_datetime(item.created_at),
        "updated_at": serialize_datetime(item.updated_at),
    }


def serialize_shop_order(order: ShopOrder | None) -> dict[str, Any] | None:
    if order is None:
        return None
    return {
        "id": order.id,
        "item_id": order.item_id,
        "buyer_tg": order.buyer_tg,
        "seller_tg": order.seller_tg,
        "item_title": order.item_title,
        "image_url": order.image_url or "",
        "delivery_text": order.delivery_text or "",
        "quantity": int(order.quantity or 0),
        "unit_price_iv": int(order.unit_price_iv or 0),
        "total_price_iv": int(order.total_price_iv or 0),
        "status": order.status,
        "created_at": serialize_datetime(order.created_at),
    }


def get_shop_settings() -> dict[str, Any]:
    with Session() as session:
        rows = session.query(ShopSetting).all()
        data = {row.setting_key: row.setting_value for row in rows}
    merged = dict(DEFAULT_SHOP_SETTINGS)
    merged.update(data)
    merged["allow_user_listing"] = bool(merged.get("allow_user_listing", False))
    merged["currency_name"] = str(merged.get("currency_name") or pivkeyu)
    merged["shop_title"] = str(merged.get("shop_title") or DEFAULT_SHOP_SETTINGS["shop_title"])
    merged["shop_notice"] = str(merged.get("shop_notice") or DEFAULT_SHOP_SETTINGS["shop_notice"])
    return merged


def set_shop_settings(patch: dict[str, Any]) -> dict[str, Any]:
    sanitized = dict(patch)
    if "allow_user_listing" in sanitized:
        sanitized["allow_user_listing"] = bool(sanitized["allow_user_listing"])
    if "currency_name" in sanitized and sanitized["currency_name"] is not None:
        sanitized["currency_name"] = str(sanitized["currency_name"]).strip() or pivkeyu
    if "shop_title" in sanitized and sanitized["shop_title"] is not None:
        sanitized["shop_title"] = str(sanitized["shop_title"]).strip() or DEFAULT_SHOP_SETTINGS["shop_title"]
    if "shop_notice" in sanitized and sanitized["shop_notice"] is not None:
        sanitized["shop_notice"] = str(sanitized["shop_notice"]).strip() or DEFAULT_SHOP_SETTINGS["shop_notice"]

    with Session() as session:
        for key, value in sanitized.items():
            row = session.query(ShopSetting).filter(ShopSetting.setting_key == key).first()
            if row is None:
                row = ShopSetting(setting_key=key, setting_value=value)
                session.add(row)
            else:
                row.setting_value = value
        session.commit()
    return get_shop_settings()


def list_shop_items(*, enabled_only: bool = True, owner_tg: int | None = None) -> list[dict[str, Any]]:
    with Session() as session:
        query = session.query(ShopItem)
        if enabled_only:
            query = query.filter(ShopItem.enabled.is_(True))
        if owner_tg is not None:
            query = query.filter(ShopItem.owner_tg == int(owner_tg))
        rows = query.order_by(ShopItem.official.desc(), ShopItem.id.desc()).all()
        return [serialize_shop_item(row) for row in rows]


def list_shop_orders(*, limit: int = 50) -> list[dict[str, Any]]:
    with Session() as session:
        rows = session.query(ShopOrder).order_by(ShopOrder.id.desc()).limit(max(int(limit or 50), 1)).all()
        return [serialize_shop_order(row) for row in rows]


def get_shop_item(item_id: int) -> dict[str, Any] | None:
    with Session() as session:
        row = session.query(ShopItem).filter(ShopItem.id == int(item_id)).first()
        return serialize_shop_item(row)


def create_shop_item(
    *,
    owner_tg: int | None,
    owner_display_name: str = "",
    owner_username: str = "",
    title: str,
    description: str = "",
    image_url: str = "",
    delivery_text: str = "",
    price_iv: int,
    stock: int,
    notify_group: bool = False,
    official: bool = False,
    enabled: bool = True,
) -> dict[str, Any]:
    clean_title = str(title or "").strip()
    if not clean_title:
        raise ValueError("商品标题不能为空")
    if int(price_iv or 0) < 0:
        raise ValueError("商品价格不能小于 0")
    if int(stock or 0) < 0:
        raise ValueError("商品库存不能小于 0")

    with Session() as session:
        item = ShopItem(
            owner_tg=int(owner_tg) if owner_tg is not None else None,
            owner_display_name=str(owner_display_name or "").strip(),
            owner_username=str(owner_username or "").strip().lstrip("@"),
            title=clean_title,
            description=str(description or "").strip(),
            image_url=str(image_url or "").strip(),
            delivery_text=str(delivery_text or "").strip(),
            price_iv=int(price_iv or 0),
            stock=int(stock or 0),
            notify_group=bool(notify_group),
            official=bool(official),
            enabled=bool(enabled),
        )
        session.add(item)
        session.commit()
        session.refresh(item)
        return serialize_shop_item(item)


def update_shop_item(item_id: int, **fields) -> dict[str, Any] | None:
    with Session() as session:
        item = session.query(ShopItem).filter(ShopItem.id == int(item_id)).first()
        if item is None:
            return None
        for key, value in fields.items():
            if not hasattr(item, key):
                continue
            if key in {"title", "description", "image_url", "delivery_text", "owner_display_name", "owner_username"} and value is not None:
                value = str(value).strip()
            if key in {"price_iv", "stock", "sold_count"} and value is not None:
                value = int(value)
            if key in {"notify_group", "official", "enabled"} and value is not None:
                value = bool(value)
            if key == "owner_username" and value is not None:
                value = str(value).lstrip("@")
            setattr(item, key, value)
        session.commit()
        session.refresh(item)
        return serialize_shop_item(item)


def delete_shop_item(item_id: int) -> bool:
    with Session() as session:
        item = session.query(ShopItem).filter(ShopItem.id == int(item_id)).first()
        if item is None:
            return False
        session.delete(item)
        session.commit()
        return True


def purchase_shop_item(*, buyer_tg: int, item_id: int, quantity: int = 1) -> dict[str, Any]:
    qty = max(int(quantity or 1), 1)
    with Session() as session:
        item = session.query(ShopItem).filter(ShopItem.id == int(item_id)).with_for_update().first()
        if item is None or not item.enabled:
            raise ValueError("商品不存在或已下架")
        if int(item.stock or 0) < qty:
            raise ValueError("商品库存不足")
        if item.owner_tg and int(item.owner_tg) == int(buyer_tg):
            raise ValueError("不能购买自己上架的商品")

        buyer = session.query(Emby).filter(Emby.tg == int(buyer_tg)).with_for_update().first()
        if buyer is None:
            raise ValueError("未找到你的 Emby 账户")

        total_price = int(item.price_iv or 0) * qty
        buyer_balance = int(buyer.iv or 0)
        if buyer_balance < total_price:
            raise ValueError("余额不足")

        seller = None
        if item.owner_tg is not None:
            seller = session.query(Emby).filter(Emby.tg == int(item.owner_tg)).with_for_update().first()

        buyer.iv = buyer_balance - total_price
        if seller is not None and int(seller.tg) != int(buyer_tg):
            seller.iv = int(seller.iv or 0) + total_price

        item.stock = int(item.stock or 0) - qty
        item.sold_count = int(item.sold_count or 0) + qty

        order = ShopOrder(
            item_id=item.id,
            buyer_tg=int(buyer_tg),
            seller_tg=int(item.owner_tg) if item.owner_tg is not None else None,
            item_title=item.title,
            image_url=item.image_url,
            delivery_text=item.delivery_text,
            quantity=qty,
            unit_price_iv=int(item.price_iv or 0),
            total_price_iv=total_price,
            status="delivered",
        )
        session.add(order)
        session.commit()
        session.refresh(order)
        session.refresh(item)
        session.refresh(buyer)
        if seller is not None:
            session.refresh(seller)
        return {
            "order": serialize_shop_order(order),
            "item": serialize_shop_item(item),
            "buyer_balance": int(buyer.iv or 0),
            "seller_balance": None if seller is None else int(seller.iv or 0),
        }

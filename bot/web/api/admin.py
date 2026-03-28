from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, or_

from bot.plugins import list_plugins
from bot.sql_helper import Session
from bot.sql_helper.sql_emby import Emby

router = APIRouter()


def serialize_user(user: Emby) -> dict:
    return {
        "tg": user.tg,
        "embyid": user.embyid,
        "name": user.name,
        "pwd": user.pwd,
        "pwd2": user.pwd2,
        "lv": user.lv,
        "cr": user.cr.isoformat() if user.cr else None,
        "ex": user.ex.isoformat() if user.ex else None,
        "us": user.us,
        "iv": user.iv,
        "ch": user.ch.isoformat() if user.ch else None,
    }


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
        },
    }


@router.get("/users")
async def list_users(
    q: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
):
    with Session() as session:
        query = session.query(Emby)

        if q:
            filters = [
                Emby.name.like(f"%{q}%"),
                Emby.embyid.like(f"%{q}%"),
            ]
            if q.isdigit():
                filters.append(Emby.tg == int(q))
            query = query.filter(or_(*filters))

        total = query.count()
        users = (
            query.order_by(Emby.tg.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )

    return {
        "code": 200,
        "data": {
            "items": [serialize_user(user) for user in users],
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
            raise HTTPException(status_code=404, detail="User not found")
        return {"code": 200, "data": serialize_user(user)}


@router.patch("/users/{tg}")
async def update_user(tg: int, payload: AdminUserPatch):
    changes = payload.model_dump(exclude_unset=True)
    if not changes:
        return {"code": 200, "data": {"updated": False, "reason": "no_changes"}}

    with Session() as session:
        user = session.query(Emby).filter(Emby.tg == tg).first()
        if user is None:
            raise HTTPException(status_code=404, detail="User not found")

        for key, value in changes.items():
            setattr(user, key, value)

        session.commit()
        session.refresh(user)
        return {"code": 200, "data": serialize_user(user)}


@router.get("/plugins")
async def plugins():
    return {"code": 200, "data": list_plugins()}

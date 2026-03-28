#! /usr/bin/python3
# -*- coding: utf-8 -*-
"""
__init__.py -
Author:susu
Date:2024/8/27
"""
from fastapi import APIRouter, Depends, HTTPException, Request

from bot import LOGGER, api as config_api, bot_token

from .admin import router as admin_router
from .ban_playlist import route as ban_playlist_route
from .login import router as login_router
from .miniapp import router as miniapp_router
from .user_info import route as user_info_route
from .webhook.client_filter import router as client_filter_router
from .webhook.favorites import router as favorites_router
from .webhook.media import router as media_router

emby_api_route = APIRouter(prefix="/emby", tags=["对接 Emby 的接口"])
user_api_route = APIRouter(prefix="/user", tags=["对接用户信息的接口"])
auth_api_route = APIRouter(prefix="/auth", tags=["用户认证接口"])
admin_api_route = APIRouter(prefix="/admin-api", tags=["后台管理"])
miniapp_api_route = APIRouter(tags=["Mini App"])


def _resolve_token(request: Request) -> str | None:
    token = request.query_params.get("token") or request.headers.get("x-api-token")
    if token:
        return token

    authorization = request.headers.get("authorization", "")
    if authorization.lower().startswith("bearer "):
        return authorization.split(" ", 1)[1].strip()
    return None


async def verify_token(request: Request):
    try:
        token = _resolve_token(request)
        if not token:
            raise HTTPException(status_code=401, detail="No token provided")
        if token != bot_token:
            LOGGER.warning("Invalid token attempt")
            raise HTTPException(status_code=403, detail="Invalid token")
        return True
    except HTTPException:
        raise
    except Exception as exc:
        LOGGER.error(f"Token verification error: {exc}")
        raise HTTPException(status_code=500, detail="Token verification failed")


async def verify_admin_token(request: Request):
    token = _resolve_token(request)
    expected_token = config_api.admin_token or bot_token

    if not token:
        raise HTTPException(status_code=401, detail="No admin token provided")
    if token != expected_token:
        LOGGER.warning("Invalid admin token attempt")
        raise HTTPException(status_code=403, detail="Invalid admin token")
    return True


emby_api_route.include_router(
    ban_playlist_route,
)
emby_api_route.include_router(
    favorites_router,
    dependencies=[Depends(verify_token)]
)
emby_api_route.include_router(
    media_router,
    dependencies=[Depends(verify_token)]
)
emby_api_route.include_router(
    client_filter_router,
    dependencies=[Depends(verify_token)]
)
user_api_route.include_router(
    user_info_route,
    dependencies=[Depends(verify_token)]
)
auth_api_route.include_router(
    login_router,
    dependencies=[Depends(verify_token)]
)
admin_api_route.include_router(
    admin_router,
    dependencies=[Depends(verify_admin_token)]
)
miniapp_api_route.include_router(
    miniapp_router,
)

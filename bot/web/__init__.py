#! /usr/bin/python3
# -*- coding: utf-8 -*-
"""
__init__.py -
Author:susu
Date:2024/8/27
"""
import asyncio
import errno
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.cors import CORSMiddleware

from bot import LOGGER, api as config_api
from bot.func_helper.redis_cache import get_status as get_redis_status
from bot.func_helper.telegram_webapp import configure_chat_menu_button
from bot.plugins import load_plugins, register_web_plugins

from .api import admin_api_route, auth_api_route, emby_api_route, miniapp_api_route, user_api_route

STATIC_DIR = Path(__file__).resolve().parent / "static"


class Web:
    def __init__(self):
        self.app: FastAPI = FastAPI(title="pivkeyu_emby Web API")
        self.web_api = None
        self.start_api = None

    def init_api(self):
        self.app.include_router(emby_api_route)
        self.app.include_router(user_api_route)
        self.app.include_router(auth_api_route)
        self.app.include_router(admin_api_route)
        self.app.include_router(miniapp_api_route)
        load_plugins()
        register_web_plugins(self.app)

        if STATIC_DIR.exists():
            self.app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

            @self.app.get("/", include_in_schema=False)
            async def root():
                return {
                    "ok": True,
                    "admin": "/admin",
                    "miniapp": "/miniapp",
                    "health": "/health",
                }

            @self.app.get("/health", include_in_schema=False)
            async def health():
                return {
                    "ok": True,
                    "redis": get_redis_status(),
                }

            @self.app.get("/admin", include_in_schema=False)
            async def admin_page():
                return FileResponse(STATIC_DIR / "admin.html")

            @self.app.get("/miniapp", include_in_schema=False)
            async def miniapp_page():
                return FileResponse(STATIC_DIR / "miniapp.html")

        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=config_api.allow_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    async def start(self):
        if not config_api.status:
            LOGGER.info("【API服务】未配置，跳过")
            return
        LOGGER.info("【API服务】检测到配置，开始启动")
        import uvicorn

        self.init_api()
        self.web_api = uvicorn.Server(
            config=uvicorn.Config(
                self.app,
                host=config_api.http_url,
                port=config_api.http_port,
                access_log=False,
            )
        )
        server_config = self.web_api.config
        if not server_config.loaded:
            server_config.load()
        self.web_api.lifespan = server_config.lifespan_class(server_config)
        try:
            await self.web_api.startup()
        except OSError as exc:
            if exc.errno == errno.EADDRINUSE:
                LOGGER.error(f"【API服务】端口 {config_api.http_port} 已被占用，请修改配置文件")
            LOGGER.error("【API服务】启动失败，退出")
            raise SystemExit from None
        if self.web_api.should_exit:
            LOGGER.error("【API服务】启动失败，退出")
            raise SystemExit from None

        LOGGER.info("【API服务】启动成功")

    def stop(self):
        if self.start_api:
            LOGGER.info("正在停止 API 服务...")
            try:
                self.start_api.cancel()
                asyncio.run(self.start_api)
            except asyncio.CancelledError:
                pass
            finally:
                LOGGER.info("API 服务已停止")


check = Web()

loop = asyncio.get_event_loop()
loop.create_task(check.start())
loop.create_task(configure_chat_menu_button())

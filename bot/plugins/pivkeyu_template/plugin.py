from __future__ import annotations

from fastapi import APIRouter


def register_bot(bot) -> None:
    # 在这里注册新的 bot 指令或事件处理器。
    # 建议直接在此文件内使用 @bot.on_message / @bot.on_callback_query。
    return None


def register_web(app) -> None:
    # 在这里注册 FastAPI 路由。
    router = APIRouter(prefix="/plugins/template", tags=["Template Plugin"])

    @router.get("/ping")
    async def ping():
        return {"ok": True, "plugin": "pivkeyu-template"}

    app.include_router(router)

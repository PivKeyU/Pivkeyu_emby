# PIVKEYU Plugin Guide

插件目录结构：

```text
bot/plugins/<your_plugin>/
├── plugin.json
└── plugin.py
```

`plugin.json` 最小示例：

```json
{
  "id": "xiuxian-game",
  "name": "修仙玩法",
  "version": "0.1.0",
  "description": "示例：修仙养成玩法",
  "entry": "plugin",
  "enabled": true
}
```

`plugin.py` 可选入口：

```python
from fastapi import APIRouter


def register_bot(bot) -> None:
    # 在这里注册 bot 指令、回调或消息处理器
    pass


def register_web(app) -> None:
    router = APIRouter(prefix="/plugins/xiuxian", tags=["修仙玩法"])

    @router.get("/status")
    async def status():
        return {"ok": True}

    app.include_router(router)
```

约定：

- `enabled: true` 时，`main.py` 会在 bot 启动前自动装载插件。
- `register_bot(bot)` 用于挂 bot 指令或事件。
- `register_web(app)` 用于暴露 FastAPI 路由。
- 已加载和未启用的插件都会出现在 `/admin` 面板的插件区。

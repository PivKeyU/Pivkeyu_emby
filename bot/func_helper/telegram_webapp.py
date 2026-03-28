from __future__ import annotations

import aiohttp

from bot import LOGGER, api as api_config, bot_token


def build_miniapp_url() -> str | None:
    public_url = (api_config.public_url or "").rstrip("/")
    if not public_url:
        return None
    return f"{public_url}/miniapp"


async def configure_chat_menu_button() -> bool:
    if not api_config.status:
        LOGGER.info("API 未启用，跳过 Mini App 菜单按钮配置")
        return False

    miniapp_url = build_miniapp_url()
    if not miniapp_url:
        LOGGER.info("未配置 api.public_url，跳过 Mini App 菜单按钮配置")
        return False

    if not miniapp_url.startswith("https://"):
        LOGGER.warning(f"Mini App URL 不是 HTTPS，Telegram 客户端可能不会显示按钮: {miniapp_url}")

    payload = {
        "menu_button": {
            "type": "web_app",
            "text": api_config.miniapp_title,
            "web_app": {"url": miniapp_url},
        }
    }

    endpoint = f"https://api.telegram.org/bot{bot_token}/setChatMenuButton"

    try:
        timeout = aiohttp.ClientTimeout(total=10)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(endpoint, json=payload) as response:
                data = await response.json()

        if data.get("ok"):
            LOGGER.info(f"Mini App 菜单按钮已配置: {miniapp_url}")
            return True

        LOGGER.warning(f"Mini App 菜单按钮配置失败: {data}")
        return False
    except Exception as exc:
        LOGGER.warning(f"Mini App 菜单按钮配置异常: {exc}")
        return False

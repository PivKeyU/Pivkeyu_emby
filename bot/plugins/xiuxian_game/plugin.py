from __future__ import annotations

# Entry point for the xiuxian_game plugin.
# Bot handlers and web routes are split into separate modules.

from .plugin_bot_handlers import register_bot
from .plugin_web_routes import register_web

__all__ = ["register_bot", "register_web"]

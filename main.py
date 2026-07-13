#! /usr/bin/python3
# -*- coding: utf-8 -*-

from bot import bot, bot_token
from bot.func_helper.bot_watchdog import schedule_bot_watchdog

# 面板
from bot.modules.panel import *
# 命令
from bot.modules.commands import *
# 其他
from bot.modules.extra import *
from bot.modules.callback import *
from bot.plugins import load_plugins
from bot.web import *

from bot import LOGGER

try:
    load_plugins()
except Exception as exc:
    LOGGER.error(f"插件加载失败: {exc}")

schedule_bot_watchdog(bot, bot_token)
bot.run()

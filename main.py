#! /usr/bin/python3
# -*- coding: utf-8 -*-

from bot import bot

# 面板
from bot.modules.panel import *
# 命令
from bot.modules.commands import *
# 其他
from bot.modules.extra import *
from bot.modules.callback import *
from bot.plugins import load_plugins
from bot.web import *

load_plugins()
bot.run()

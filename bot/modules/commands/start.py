"""
Start panel commands.
"""

import asyncio

from pyrogram import filters

from bot import LOGGER, bot, bot_photo, group, prefixes, ranks, sakura_b
from bot.func_helper.emby import Embyservice
from bot.func_helper.filters import user_in_group_filter, user_in_group_on_filter
from bot.func_helper.fix_bottons import cr_kk_ikb, group_f, judge_group_ikb, judge_start_ikb
from bot.func_helper.msg_utils import callAnswer, deleteMessage, editMessage, sendMessage, sendPhoto
from bot.func_helper.utils import judge_admins, members_info, open_check
from bot.modules.commands.exchange import rgs_code
from bot.modules.extra import user_cha_ip
from bot.sql_helper.sql_emby import sql_add_emby, sql_get_emby


@bot.on_message((filters.command("start", prefixes) | filters.command("count", prefixes)) & filters.chat(group))
async def ui_g_command(_, msg):
    await asyncio.gather(
        deleteMessage(msg),
        sendMessage(
            msg,
            f"💬 这是私聊命令哦，请点下面的按钮来找本女仆单独说话。",
            buttons=group_f,
            timer=60,
        ),
    )


@bot.on_message(filters.command("myinfo", prefixes) & user_in_group_on_filter)
async def my_info(_, msg):
    await deleteMessage(msg)
    if msg.sender_chat:
        return
    text, _keyboard = await cr_kk_ikb(uid=msg.from_user.id, first=msg.from_user.first_name)
    await sendMessage(msg, text, timer=60)


@bot.on_message(filters.command("count", prefixes) & user_in_group_on_filter & filters.private)
async def count_info(_, msg):
    await deleteMessage(msg)
    text = await Embyservice.get_medias_count()
    await sendMessage(msg, text, timer=60)


@bot.on_message(filters.command("start", prefixes) & filters.private)
async def p_start(_, msg):
    user_id = getattr(getattr(msg, "from_user", None), "id", None)
    LOGGER.info(f"[/start] received private start from user={user_id}")

    try:
        in_group = await user_in_group_filter(_, msg)
        LOGGER.info(f"[/start] group check user={user_id} in_group={in_group}")
        if not in_group:
            return await asyncio.gather(
                deleteMessage(msg),
                sendMessage(
                    msg,
                    "🚫 哼，还没加入群组和频道呢...先加完再来找本女仆啦。",
                    buttons=judge_group_ikb,
                ),
            )

        try:
            command_arg = msg.command[1]
            arg_prefix = command_arg.split("-")[0]

            if arg_prefix == "userip":
                name = command_arg.split("-")[1]
                if judge_admins(msg.from_user.id):
                    return await user_cha_ip(_, msg, name)
                return await sendMessage(msg, "🔒 哼，这个只有主人才行...你、你还不够格啦。")

            if arg_prefix in f"{ranks.logo}" or arg_prefix == str(msg.from_user.id):
                await asyncio.gather(msg.delete(), rgs_code(_, msg, register_code=command_arg))
                LOGGER.info(f"[/start] exchange flow user={user_id} arg={command_arg}")
                return

            await asyncio.gather(sendMessage(msg, "❓ 这个参数...才、才不对呢！检查一下再试。"), msg.delete())
            return
        except (IndexError, TypeError):
            LOGGER.info(f"[/start] enter panel flow user={user_id}")

        exist_emby_data = sql_get_emby(msg.from_user.id)
        if not exist_emby_data:
            sql_add_emby(msg.from_user.id)

        data = await members_info(tg=msg.from_user.id)
        if not data:
            LOGGER.warning(f"[/start] members_info returned empty for user={user_id}")
            return await sendMessage(msg, "⚠️ 哼、信息获取失败了...不是本女仆的错哦，稍微等等再试。")

        is_admin = judge_admins(msg.from_user.id)
        _name, lv, ex, us, embyid, _pwd2 = data
        stat, all_user, tem, _timing = await open_check()
        text = (
            f"哼，才不是特地迎接你的呢...{msg.from_user.first_name}\n\n"
            f"**👤 用户 ID** | `{msg.from_user.id}`\n"
            f"**📊 当前状态** | {lv}\n"
            f"**💰 持有{sakura_b}** | {us}\n"
            f"**📝 注册状态** | {stat}\n"
            f"**👥 总注册限制** | {all_user}\n"
            f"**🪑 剩余席位** | {all_user - tem}\n"
        )

        if not embyid:
            await asyncio.gather(
                deleteMessage(msg),
                sendPhoto(msg, bot_photo, caption=text, buttons=judge_start_ikb(is_admin, False, msg.from_user.id)),
            )
        else:
            await asyncio.gather(
                deleteMessage(msg),
                sendPhoto(
                    msg,
                    bot_photo,
                    caption=f"🎛️ 请选一个功能继续操作，{msg.from_user.first_name}。",
                    buttons=judge_start_ikb(is_admin, True, msg.from_user.id),
                ),
            )

        LOGGER.info(f"[/start] panel response sent user={user_id} has_account={bool(embyid)}")
    except Exception as exc:
        LOGGER.exception(f"[/start] failed for user={user_id}: {exc}")
        await sendMessage(msg, "⚠️ 呜...处理失败了。才不是本女仆的错！让、让主人看看日志吧...")


@bot.on_callback_query(filters.regex("back_start"))
async def b_start(_, call):
    try:
        in_group = await user_in_group_filter(_, call)
        await callAnswer(call, "返回 start")
        if in_group:
            is_admin = judge_admins(call.from_user.id)
            await editMessage(
                call,
                text=f"🎛️ 随、随便你选啦，{call.from_user.first_name}。反正本女仆也不是很在意...",
                buttons=judge_start_ikb(is_admin, account=True, user_id=call.from_user.id),
            )
        else:
            await editMessage(
                call,
                text="🚫 哼，还没加入群组和频道呢...先加完再来找本女仆啦。",
                buttons=judge_group_ikb,
            )
    except Exception as exc:
        LOGGER.exception(f"[back_start] failed user={getattr(call.from_user, 'id', None)}: {exc}")
        await callAnswer(call, "⚠️ 面板返回失败了...才不是本女仆的错！", True)


@bot.on_callback_query(filters.regex("store_all"))
async def store_alls(_, call):
    try:
        in_group = await user_in_group_filter(_, call)
        if not in_group:
            await asyncio.gather(
                callAnswer(call, "返回 start"),
                deleteMessage(call),
                sendPhoto(
                    call,
                    bot_photo,
                    "🚫 哼，还没加入群组和频道呢...先加完再来找本女仆啦。",
                    judge_group_ikb,
                ),
            )
            return

        await callAnswer(call, "正在打开", True)
    except Exception as exc:
        LOGGER.exception(f"[store_all] failed user={getattr(call.from_user, 'id', None)}: {exc}")
        await callAnswer(call, "操作失败", True)

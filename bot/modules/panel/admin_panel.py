"""
 admin 面板
 功能暂定 开关注册，生成注册码，查看注册码情况，邀请注册排名情况
"""
import asyncio

from pyrogram import filters
from pyrogram.errors import BadRequest

from bot import bot, _open, save_config, bot_photo, LOGGER, admins, owner, config
from bot.func_helper.filters import admins_on_filter
from bot.schemas import ExDate
from bot.sql_helper.sql_code import sql_count_code, sql_count_p_code, sql_delete_all_unused, sql_delete_unused_by_days
from bot.sql_helper.sql_emby import sql_count_emby
from bot.func_helper.fix_bottons import gm_ikb_content, open_menu_ikb, gog_rester_ikb, back_open_menu_ikb, \
    back_free_ikb, re_cr_link_ikb, close_it_ikb, ch_link_ikb, date_ikb, cr_paginate, cr_renew_ikb, invite_lv_ikb, checkin_lv_ikb
from bot.func_helper.msg_utils import callAnswer, editMessage, sendPhoto, callListen, deleteMessage, sendMessage
from bot.func_helper.utils import open_check, cr_link_one,rn_link_one


async def _safe_chat_name(client, chat_id: int) -> str:
    try:
        chat = await client.get_chat(chat_id)
    except BadRequest as exc:
        LOGGER.warning(f"[admin_panel] get_chat failed for chat_id={chat_id}: {exc}")
        return str(chat_id)
    except Exception as exc:
        LOGGER.warning(f"[admin_panel] unexpected get_chat failure for chat_id={chat_id}: {exc}")
        return str(chat_id)

    return chat.first_name or chat.title or str(chat_id)


@bot.on_callback_query(filters.regex('manage') & admins_on_filter)
async def gm_ikb(_, call):
    await callAnswer(call, '✔️ manage面板')
    stat, all_user, tem, timing = await open_check()
    stat = "True" if stat else "False"
    timing = 'Turn off' if timing == 0 else str(timing) + ' min'
    tg, emby, white = sql_count_emby()
    gm_text = f'⚙️ 欢迎您，亲爱的主人 {call.from_user.first_name}\n\n' \
              f'· ®️ 注册状态 | **{stat}**\n' \
              f'· ⏳ 定时注册 | **{timing}**\n' \
              f'· 🎫 总注册限制 | **{all_user}**\n'\
              f'· 🎟️ 已注册人数 | **{emby}** • WL **{white}**\n' \
              f'· 🤖 本女仆使用人数 | {tg}'

    await editMessage(call, gm_text, buttons=gm_ikb_content)


# 开关注册
@bot.on_callback_query(filters.regex('open-menu') & admins_on_filter)
async def open_menu(_, call):
    await callAnswer(call, '®️ register面板')
    # [开关，注册总数，定时注册] 此间只对emby表中tg用户进行统计
    stat, all_user, tem, timing = await open_check()
    tg, emby, white = sql_count_emby()
    openstats = '✅' if stat else '❎'  # 三元运算
    timingstats = '❎' if timing == 0 else '✅'
    text = f'⚙ **注册状态设置**：\n\n- 自由注册即定量方式，定时注册既定时又定量，将自动转发消息至群组，再次点击按钮可提前结束并报告。\n' \
           f'- **注册总人数限制 {all_user}**'
    await editMessage(call, text, buttons=open_menu_ikb(openstats, timingstats))
    if tem != emby:
        _open.tem = emby
        save_config()


@bot.on_callback_query(filters.regex('open_stat') & admins_on_filter)
async def open_stats(_, call):
    stat, all_user, tem, timing = await open_check()
    if timing != 0:
        return await callAnswer(call, "🔴 目前正在运行定时注册。\n无法调用，请再次点击，【定时注册】关闭状态", True)

    tg, emby, white = sql_count_emby()
    if stat:
        _open.stat = False
        save_config()
        await callAnswer(call, "🟢【自由注册】\n\n已结束", True)
        sur = all_user - tem
        text = f'🫧 主人 {call.from_user.first_name} 已关闭 **自由注册**\n\n' \
               f'🎫 总注册限制 | {all_user}\n🎟️ 已注册人数 | {tem}\n' \
               f'🎭 剩余可注册 | **{sur}**\n🤖 本女仆使用人数 | {tg}'
        await asyncio.gather(sendPhoto(call, photo=bot_photo, caption=text, send=True),
                             editMessage(call, text, buttons=back_free_ikb))
        # await open_menu(_, call)
        LOGGER.info(f"【admin】：主人 {call.from_user.first_name} 关闭了自由注册")
    elif not stat:
        _open.stat = True
        save_config()
        await callAnswer(call, "🟡【自由注册】\n\n已开启", True)
        sur = all_user - tem  # for i in group可以多个群组用，但是现在不做
        text = f'🫧 主人 {call.from_user.first_name} 已开启 **自由注册**\n\n' \
               f'🎫 总注册限制 | {all_user}\n🎟️ 已注册人数 | {tem}\n' \
               f'🎭 剩余可注册 | **{sur}**\n🤖 本女仆使用人数 | {tg}'
        await asyncio.gather(sendPhoto(call, photo=bot_photo, caption=text, buttons=gog_rester_ikb(), send=True),
                             editMessage(call, text=text, buttons=back_free_ikb))
        # await open_menu(_, call)
        LOGGER.info(f"【admin】：主人 {call.from_user.first_name} 开启了自由注册，总人数限制 {all_user}")


change_for_timing_task = None


@bot.on_callback_query(filters.regex('open_timing') & admins_on_filter)
async def open_timing(_, call):
    global change_for_timing_task
    if _open.timing == 0:
        await callAnswer(call, '⭕ 定时设置')
        await editMessage(call,
                          "🦄【定时注册】 \n\n- 请在 120s 内发送 [定时时长] [总人数]\n"
                          "- 形如：`30 50` 即30min，总人数限制50\n"
                          "- 如需要关闭定时注册，再次点击【定时注册】\n"
                          "- 设置好之后将发送置顶消息注意权限\n- 退出 /cancel")

        txt = await callListen(call, 120, buttons=back_open_menu_ikb)
        if txt is False:
            return

        await txt.delete()
        if txt.text == '/cancel':
            return await open_menu(_, call)

        try:
            new_timing, new_all_user = txt.text.split()
            _open.timing = int(new_timing)
            _open.all_user = int(new_all_user)
            _open.stat = True
            save_config()
        except ValueError:
            await editMessage(call, "🚫 请检查数字填写是否正确。\n`[时长min] [总人数]`", buttons=back_open_menu_ikb)
        else:
            tg, emby, white = sql_count_emby()
            sur = _open.all_user - emby
            await asyncio.gather(sendPhoto(call, photo=bot_photo,
                                           caption=f'🫧 主人 {call.from_user.first_name} 已开启 **定时注册**\n\n'
                                                   f'⏳ 可持续时间 | **{_open.timing}** min\n'
                                                   f'🎫 总注册限制 | {_open.all_user}\n🎟️ 已注册人数 | {emby}\n'
                                                   f'🎭 剩余可注册 | **{sur}**\n🤖 本女仆使用人数 | {tg}',
                                           buttons=gog_rester_ikb(), send=True),
                                 editMessage(call,
                                             f"®️ 好，已设置**定时注册 {_open.timing} min 总限额 {_open.all_user}**",
                                             buttons=back_free_ikb))
            LOGGER.info(
                f"【admin】-定时注册：主人 {call.from_user.first_name} 开启了定时注册 {_open.timing} min，人数限制 {sur}")
            # 创建一个异步任务并保存为变量，并给它一个名字
            change_for_timing_task = asyncio.create_task(
                change_for_timing(_open.timing, call.from_user.id, call), name='change_for_timing')

    else:
        try:
            # 遍历所有的异步任务，找到'change_for_timing'，取消
            for task in asyncio.all_tasks():
                if task.get_name() == 'change_for_timing':
                    change_for_timing_task = task
                    break
            change_for_timing_task.cancel()
        except AttributeError:
            pass
        else:
            await callAnswer(call, "Ⓜ️【定时任务运行终止】\n\n**已为您停止**", True)
            await open_menu(_, call)


async def change_for_timing(timing, tgid, call):
    a = _open.tem
    timing = timing * 60
    try:
        await asyncio.sleep(timing)
    except asyncio.CancelledError:
        pass
    finally:
        _open.timing = 0
        _open.stat = False
        save_config()
        b = _open.tem - a
        s = _open.all_user - _open.tem
        text = f'⏳** 注册结束**：\n\n🍉 目前席位：{_open.tem}\n🥝 新增席位：{b}\n🍋 剩余席位：{s}'
        send = await sendPhoto(call, photo=bot_photo, caption=text, timer=300, send=True)
        send1 = await send.forward(tgid)
        LOGGER.info(f'【admin】-定时注册：运行结束，本次注册 目前席位：{_open.tem}  新增席位:{b}  剩余席位：{s}')
        await deleteMessage(send1, 30)


@bot.on_callback_query(filters.regex('all_user_limit') & admins_on_filter)
async def open_all_user_l(_, call):
    await callAnswer(call, '⭕ 限制人数')
    send = await call.message.edit(
        "🦄 请在 120s 内发送开注总人数，本次修改不会对注册状态改动，如需要开注册请点击打开自由注册\n**注**：总人数满自动关闭注册 取消 /cancel")
    if send is False:
        return

    txt = await callListen(call, 120, buttons=back_free_ikb)
    if txt is False:
        return
    elif txt.text == "/cancel":
        await txt.delete()
        return await open_menu(_, call)

    try:
        await txt.delete()
        a = int(txt.text)
    except ValueError:
        await editMessage(call, f"❌ 八嘎，请输入一个数字给我。", buttons=back_free_ikb)
    else:
        _open.all_user = a
        save_config()
        await editMessage(call, f"✔️ 成功，您已设置 **注册总人数 {a}**", buttons=back_free_ikb)
        LOGGER.info(f"【admin】：主人 {call.from_user.first_name} 调整了总人数限制：{a}")
@bot.on_callback_query(filters.regex('open_us') & admins_on_filter)
async def open_us(_, call):
    await callAnswer(call, '🤖开放账号天数')
    send = await call.message.edit(
        "🦄 请在 120s 内发送开放注册时账号的有效天数，本次修改不会对注册状态改动，如需要开注册请点击打开自由注册\n**注**：总人数满自动关闭注册 取消 /cancel")
    if send is False:
        return

    txt = await callListen(call, 120, buttons=back_free_ikb)
    if txt is False:
        return
    elif txt.text == "/cancel":
        await txt.delete()
        return await open_menu(_, call)

    try:
        await txt.delete()
        a = int(txt.text)
    except ValueError:
        await editMessage(call, f"❌ 八嘎，请输入一个数字给我。", buttons=back_free_ikb)
    else:
        _open.open_us = a
        save_config()
        await editMessage(call, f"✔️ 成功，您已设置 **开放注册时账号的有效天数 {a}**", buttons=back_free_ikb)
        LOGGER.info(f"【admin】：主人 {call.from_user.first_name} 调整了开放注册时账号的有效天数：{a}")

# 生成注册链接
@bot.on_callback_query(filters.regex('cr_link') & admins_on_filter)
async def cr_link(_, call):
    def parse_payload(raw_text: str):
        parts = raw_text.split(maxsplit=6)
        if len(parts) < 4:
            raise ValueError("参数不足")

        times, count, method, renew = parts[:4]
        days = int(times)
        count = int(count)
        method = method.lower()
        renew = renew.upper()
        usage_limit = int(parts[4]) if len(parts) >= 5 else 1
        suffix_mode = parts[5].lower() if len(parts) >= 6 else "random"
        suffix_text = parts[6].strip() if len(parts) >= 7 else None

        if count <= 0:
            raise ValueError("数量必须大于 0")
        if usage_limit <= 0:
            raise ValueError("使用次数必须大于 0")
        if method not in {"code", "link"}:
            raise ValueError("模式只能是 code 或 link")
        if renew not in {"F", "T"}:
            raise ValueError("类型只能是 F 或 T")
        if suffix_mode not in {"random", "fixed"}:
            raise ValueError("后缀模式只能是 random 或 fixed")
        if suffix_mode == "fixed" and not suffix_text:
            raise ValueError("固定后缀模式必须提供后缀文本")

        return {
            "times": times,
            "days": days,
            "count": count,
            "method": method,
            "renew": renew,
            "usage_limit": usage_limit,
            "suffix_mode": suffix_mode,
            "suffix_text": suffix_text,
        }

    await callAnswer(call, '生成注册码/续期码')
    send = await editMessage(
        call,
        "请回复以下格式：\n"
        "`[天数] [数量] [模式] [类型] [使用次数] [后缀模式] [固定后缀]`\n\n"
        "字段说明：\n"
        "- 天数：30 / 90 / 180 / 365\n"
        "- 模式：`code` 显示纯码，`link` 显示 deep link\n"
        "- 类型：`F` 注册码，`T` 续期码\n"
        "- 使用次数：每个码允许被核销多少次，默认 1\n"
        "- 后缀模式：`random` 或 `fixed`，默认 `random`\n"
        "- 固定后缀：仅 `fixed` 时必填，只允许字母/数字/_/-\n\n"
        "示例：\n"
        "`30 1 link T`\n"
        "`30 1 code F 5 fixed VIP2026`\n"
        "`90 3 code T 2 random`\n\n"
        "说明：固定后缀模式下如果数量大于 1，会自动追加序号。\n"
        "取消请发送 `/cancel`",
    )
    if send is False:
        return

    content = await callListen(call, 120, buttons=re_cr_link_ikb)
    if content is False:
        return
    if content.text == '/cancel':
        await content.delete()
        await editMessage(call, '已取消本次生成。', buttons=re_cr_link_ikb)
        return

    try:
        payload = parse_payload(content.text)
        await content.delete()
        if payload["renew"] == "F":
            links = await cr_link_one(
                call.from_user.id,
                payload["times"],
                payload["count"],
                payload["days"],
                payload["method"],
                usage_limit=payload["usage_limit"],
                suffix_mode=payload["suffix_mode"],
                suffix_text=payload["suffix_text"],
            )
            code_label = "注册码"
        else:
            links = await rn_link_one(
                call.from_user.id,
                payload["times"],
                payload["count"],
                payload["days"],
                payload["method"],
                usage_limit=payload["usage_limit"],
                suffix_mode=payload["suffix_mode"],
                suffix_text=payload["suffix_text"],
            )
            code_label = "续期码"
    except ValueError as exc:
        await editMessage(call, f'输入格式错误：{exc}', buttons=re_cr_link_ikb)
        return

    if links is None:
        await editMessage(call, '数据库写入失败，请检查数据库。', buttons=re_cr_link_ikb)
        return

    suffix_desc = f"固定后缀 `{payload['suffix_text']}`" if payload["suffix_mode"] == "fixed" else "随机后缀"
    body = (
        f"🎆 本女仆已为你生成 **{payload['days']} 天{code_label}** {payload['count']} 个\n"
        f"- 每码可用：**{payload['usage_limit']} 次**\n"
        f"- 后缀模式：**{suffix_desc}**\n\n"
        f"{links}"
    )
    chunks = [body[i:i + 4096] for i in range(0, len(body), 4096)]
    for chunk in chunks:
        await sendMessage(content, chunk, buttons=close_it_ikb)

    await editMessage(
        call,
        f'已生成 {payload["count"]} 个 {payload["days"]} 天{code_label}，每码可用 {payload["usage_limit"]} 次。',
        buttons=re_cr_link_ikb,
    )
    LOGGER.info(
        f"【admin】本女仆为 {content.from_user.id} 生成了 {payload['count']} 个 "
        f"{payload['days']} 天{code_label}，usage_limit={payload['usage_limit']}，"
        f"suffix_mode={payload['suffix_mode']}，suffix_text={payload['suffix_text']}"
    )
    return
    await callAnswer(call, '✔️ 创建注册/续期码')
    send = await editMessage(call,
                             '🎟️ 请回复创建 [天数] [数量] [模式] [续期]\n\n'
                             '**天数**：月30，季90，半年180，年365\n'
                             '**模式**： link -深链接 | code -码\n'
                             '**续期**： F - 注册码，T - 续期码\n'
                             '**示例**：`30 1 link T` 记作 30天一条续期深链接\n'
                             '__取消本次操作，请 /cancel__')
    if send is False:
        return

    content = await callListen(call, 120, buttons=re_cr_link_ikb)
    if content is False:
        return
    elif content.text == '/cancel':
        await content.delete()
        return await editMessage(call, '⭕ 您已经取消操作了。', buttons=re_cr_link_ikb)
    try:
        await content.delete()
        times, count, method, renew = content.text.split()
        count = int(count)
        days = int(times)
        if method != 'code' and method != 'link':
            return editMessage(call, '⭕ 输入的method参数有误', buttons=re_cr_link_ikb)
    except (ValueError, IndexError):
        return await editMessage(call, '⚠️ 检查输入，有误。', buttons=re_cr_link_ikb)
    else:
        if renew == 'F':
            links = await cr_link_one(call.from_user.id, times, count, days, method)
            if links is None:
                return await editMessage(call, '⚠️ 数据库插入失败，请检查数据库。', buttons=re_cr_link_ikb)
            links = f"🎯 本女仆已为您生成 **{days}天** 注册码 {count} 个\n\n" + links
            chunks = [links[i:i + 4096] for i in range(0, len(links), 4096)]
            for chunk in chunks:
                await sendMessage(content, chunk, buttons=close_it_ikb)
            await editMessage(call, f'📂 本女仆已为您生成了 {count} 个 {days} 天注册码', buttons=re_cr_link_ikb)
            LOGGER.info(f"【admin】：本女仆已为 {content.from_user.id} 生成了 {count} 个 {days} 天注册码")

        else:
            links = await rn_link_one(call.from_user.id, times, count, days, method)
            if links is None:
                return await editMessage(call, '⚠️ 数据库插入失败，请检查数据库。', buttons=re_cr_link_ikb)
            links = f"🎯 本女仆已为您生成 **{days}天** 续期码 {count} 个\n\n" + links
            chunks = [links[i:i + 4096] for i in range(0, len(links), 4096)]
            for chunk in chunks:
                await sendMessage(content, chunk, buttons=close_it_ikb)
            await editMessage(call, f'📂 本女仆已为您生成了 {count} 个 {days} 天续期码', buttons=re_cr_link_ikb)
            LOGGER.info(f"【admin】：本女仆已为 {content.from_user.id} 生成了 {count} 个 {days} 天续期码")


# 检索
@bot.on_callback_query(filters.regex('ch_link') & admins_on_filter)
async def ch_link(_, call):
    await callAnswer(call, '查看注册码统计...', True)
    exhausted, mon, sea, half, year, available = sql_count_code()
    text = (
        f"**🎿 Code 统计：**\n"
        f"· 已用完 - {exhausted} | 可继续使用 - {available}\n"
        f"· 月码 - {mon} | 季码 - {sea}\n"
        f"· 半年码 - {half} | 年码 - {year}"
    )
    ls = []
    admin_ids = list(dict.fromkeys([*admins, owner]))
    for admin_id in admin_ids:
        name = await _safe_chat_name(bot, admin_id)
        exhausted, mon, sea, half, year, available = sql_count_code(admin_id)
        text += (
            f"\n👏 `{name}`: 月 {mon} / 季 {sea} / 半年 {half} / 年 {year} / "
            f"已用完 {exhausted} / 可用 {available}"
        )
        ls.append([f"📗 {name}", f"ch_admin_link-{admin_id}"])
    ls.append(["🪊 删除可用码", "delete_codes"])
    keyboard = ch_link_ikb(ls)
    text += '\n详细列表见下方按钮。'

    await editMessage(call, text, buttons=keyboard)
    return
    await callAnswer(call, '🔍 查看管理们注册码...时长会久一点', True)
    a, b, c, d, f, e = sql_count_code()
    text = f'**🎫 常用code数据：\n• 已使用 - {a}  | • 未使用 - {e}\n• 月码 - {b}   | • 季码 - {c} \n• 半年码 - {d}  | • 年码 - {f}**'
    ls = []
    admins.append(owner)
    for i in admins:
        name = await bot.get_chat(i)
        a, b, c, d, f ,e= sql_count_code(i)
        text += f'\n👮🏻`{name.first_name}`: 月/{b}，季/{c}，半年/{d}，年/{f}，已用/{a}，未用/{e}'
        f = [f"🔎 {name.first_name}", f"ch_admin_link-{i}"]
        ls.append(f)
    ls.append(["🚮 删除未使用码", f"delete_codes"])
    admins.remove(owner)
    keyboard = ch_link_ikb(ls)
    text += '\n详情查询 👇'

    await editMessage(call, text, buttons=keyboard)

# 删除未使用码
@bot.on_callback_query(filters.regex('delete_codes') & admins_on_filter)
async def delete_unused_codes(_, call):
    await callAnswer(call, '⚠️ 请确认要删除码的类别')
    if call.from_user.id != owner:
        return await callAnswer(call, '🚫 不可以哦！ 你又不是owner', True)
    
    await editMessage(call, 
        "请回复要删除的未使用码天数类别，多个天数用空格分隔\n"
        "例如: `5 30 180` 将删除属于5天、30天和180天类别的未使用码\n"
        "输入 `all` 删除所有未使用码\n"
        "取消请输入 /cancel")
    
    content = await callListen(call, 120)
    if content is False:
        return
    elif content.text == '/cancel':
        await content.delete()
        return await gm_ikb(_, call)
        
    try:
        if content.text.lower() == 'all':
            count = sql_delete_all_unused()
            text = f"已删除所有未使用码，共 {count} 个"
        else:
            days = [int(x) for x in content.text.split()]
            count = sql_delete_unused_by_days(days)
            text = f"已删除指定天数的未使用码，共 {count} 个"
        await content.delete()
    except ValueError:
        text = "❌ 输入格式错误"
    
    ls=[]
    ls.append(["🔄 继续删除", f"delete_codes"])
    keyboard = ch_link_ikb(ls)
    await editMessage(call, text, buttons=keyboard)


@bot.on_callback_query(filters.regex('ch_admin_link'))
async def ch_admin_link(client, call):
    i = int(call.data.split('-')[1])
    if call.from_user.id != owner and call.from_user.id != i:
        await callAnswer(call, '你不能查看别人的注册码详情。', True)
        return

    await callAnswer(call, f'查看 {i} 的注册码统计')
    exhausted, mon, sea, half, year, available = sql_count_code(i)
    name = await _safe_chat_name(client, i)
    text = (
        f"**🎿 [{name}-{i}](tg://user?id={i})：**\n"
        f"· 已用完 - {exhausted} | 可继续使用 - {available}\n"
        f"· 月码 - {mon} | 季码 - {sea}\n"
        f"· 半年码 - {half} | 年码 - {year}"
    )
    await editMessage(call, text, date_ikb(i))
    return

    i = int(call.data.split('-')[1])
    if call.from_user.id != owner and call.from_user.id != i:
        return await callAnswer(call, '🚫 你怎么偷窥别人呀! 你又不是owner', True)
    await callAnswer(call, f'💫 主人 {i} 的注册码')
    a, b, c, d, f, e= sql_count_code(i)
    name = await client.get_chat(i)
    text = f'**🎫 [{name.first_name}-{i}](tg://user?id={i})：\n• 已使用 - {a}  | • 未使用 - {e}\n• 月码 - {b}    | • 季码 - {c} \n• 半年码 - {d}  | • 年码 - {f}**'
    await editMessage(call, text, date_ikb(i))


@bot.on_callback_query(
    filters.regex('register_mon') | filters.regex('register_sea')
    | filters.regex('register_half') | filters.regex('register_year') | filters.regex('register_used') | filters.regex('register_unused'))
async def buy_mon(_, call):
    await call.answer('✅ 显示注册码')
    cd, times, u = call.data.split('_')
    target_user_id = int(u)
    if call.from_user.id != owner and call.from_user.id != target_user_id:
        return await callAnswer(call, '你不能查看别人的注册码详情。', True)
    n = getattr(ExDate(), times)
    a, i = sql_count_p_code(target_user_id, n)
    if a is None:
        x = '**空**'
    else:
        x = a[0]
    first_name = await _safe_chat_name(bot, target_user_id)
    keyboard = await cr_paginate(i, 1, n, target_user_id)
    await sendMessage(call, f'🔎当前 {first_name} - **{n}**天，检索出以下 **{i}**页：\n\n{x}', keyboard)


# 检索翻页
@bot.on_callback_query(filters.regex('pagination_keyboard'))
async def paginate_keyboard(_, call):
    parts = call.data.split(":", 1)[1].split('_')
    if len(parts) == 2:
        j, mode = map(int, parts)
        target_user_id = call.from_user.id
    elif len(parts) == 3:
        j, mode, target_user_id = map(int, parts)
    else:
        return await callAnswer(call, '分页参数无效。', True)

    if call.from_user.id != owner and call.from_user.id != target_user_id:
        return await callAnswer(call, '你不能查看别人的注册码详情。', True)

    await callAnswer(call, f'好的，将为您翻到第 {j} 页')
    a, b = sql_count_p_code(target_user_id, mode)
    keyboard = await cr_paginate(b, j, mode, target_user_id)
    text = a[j-1]
    await editMessage(call, f'🔎当前模式- **{mode}**天，检索出以下 **{b}**页链接：\n\n{text}', keyboard)


@bot.on_callback_query(filters.regex('set_renew'))
async def set_renew(_, call):
    await callAnswer(call, '🚀 进入续期设置')
    try:
        method = call.data.split('-')[1]
        setattr(_open, method, not getattr(_open, method))
        save_config()
    except IndexError:
        pass
    finally:
        await editMessage(call, text='⭕ **关于用户组的续期功能**\n\n选择点击下方按钮开关任意兑换功能',
                          buttons=cr_renew_ikb())
@bot.on_callback_query(filters.regex('set_freeze_days') & admins_on_filter)
async def set_freeze_days(_, call):
    await callAnswer(call, '⭕ 设置封存天数')
    send = await call.message.edit(
        "🦄 请在 120s 内发送封存账号天数，\n**注**：用户到期后被禁用，再过指定天数后会被删除 取消 /cancel")
    if send is False:
        return

    txt = await callListen(call, 120, buttons=back_free_ikb)
    if txt is False:
        return
    elif txt.text == "/cancel":
        await txt.delete()
        return await open_menu(_, call)

    try:
        await txt.delete()
        a = int(txt.text)
    except ValueError:
        await editMessage(call, f"❌ 八嘎，请输入一个数字给我。", buttons=back_free_ikb)
    else:
        config.freeze_days = a
        save_config()
        await editMessage(call, f"✔️ 成功，您已设置 **封存账号天数 {a}**", buttons=back_free_ikb)
        LOGGER.info(f"【admin】：主人 {call.from_user.first_name} 调整了封存账号天数：{a}")

@bot.on_callback_query(filters.regex('set_invite_lv'))
async def invite_lv_set(_, call):
    try:
        method = call.data
        if method.startswith('set_invite_lv-'):
            # 当选择具体等级时
            level = method.split('-')[1]
            if level in ['a', 'b', 'c', 'd']:
                _open.invite_lv = level
                save_config()
                await callAnswer(call, f'✅ 已设置邀请等级为 {level}', show_alert=True)
        await callAnswer(call, '🚀 进入邀请等级设置')
        # 当点击设置邀请等级按钮时
        await editMessage(call, 
            "请选择邀请等级:\n\n"
            f"当前等级: {_open.invite_lv}\n\n"
            "🅰️ - 白名单可使用\n"
            "🅱️ - 普通用户及以上可使用\n" 
            "©️ - 已禁用用户及以上可使用\n"
            "🅳️ - 所有用户可使用",
            buttons=invite_lv_ikb())
        return
    except IndexError:
        pass
@bot.on_callback_query(filters.regex('set_checkin_lv'))
async def checkin_lv_set(_, call):
    try:
        method = call.data
        if method.startswith('set_checkin_lv-'):
            # 当选择具体等级时
            level = method.split('-')[1]
            if level in ['a', 'b', 'c', 'd']:
                _open.checkin_lv = level
                save_config()
                await callAnswer(call, f'✅ 已设置签到等级为 {level}', show_alert=True)
        await callAnswer(call, '🚀 进入签到等级设置')
        # 当点击设置签到等级按钮时
        await editMessage(call, 
            "请选择签到等级:\n\n"
            f"当前等级: {_open.checkin_lv}\n\n"
            "🅰️ - 白名单可签到\n"
            "🅱️ - 普通用户及以上可签到\n" 
            "©️ - 已禁用用户及以上可签到\n"
            "🅳️ - 所有用户可签到",
            buttons=checkin_lv_ikb())
        return
    except IndexError:
        pass

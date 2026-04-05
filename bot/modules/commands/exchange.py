"""
Exchange register / renew codes.
"""

from datetime import datetime, timedelta

from sqlalchemy.exc import IntegrityError

from bot import LOGGER, _open, bot, bot_photo, ranks
from bot.func_helper.emby import emby
from bot.func_helper.fix_bottons import register_code_ikb
from bot.func_helper.msg_utils import sendMessage, sendPhoto
from bot.sql_helper import Session
from bot.sql_helper.sql_code import Code, CodeRedeem
from bot.sql_helper.sql_emby import Emby, sql_get_emby


def is_renew_code(input_string):
    return "Renew" in input_string


def _code_limit(record: Code) -> int:
    return max(int(record.use_limit or 1), 1)


def _code_count(record: Code) -> int:
    return max(int(record.use_count or 0), 0)


def _code_remaining(record: Code) -> int:
    return max(_code_limit(record) - _code_count(record), 0)


def _code_usage_text(record: Code) -> str:
    return f"{_code_count(record)}/{_code_limit(record)}"


def _mask_code(code_value: str) -> str:
    if len(code_value) <= 7:
        return "******"
    return f"{code_value[:-7]}{'*' * 7}"


def _code_prefix(code_value: str) -> str:
    return (code_value or "").split("-", 1)[0]


def _can_use_register_code(code_value: str, user_id: int) -> bool:
    prefix = _code_prefix(code_value)
    return prefix in {str(ranks.logo), str(user_id)}


def _load_locked_code(session, code_value: str):
    return session.query(Code).filter(Code.code == code_value).with_for_update().first()


def _user_already_redeemed(session, code_value: str, user_id: int) -> bool:
    return (
        session.query(CodeRedeem.id)
        .filter(CodeRedeem.code == code_value, CodeRedeem.user_id == user_id)
        .first()
        is not None
    )


def _apply_code_redeem(session, record: Code, user_id: int):
    if _user_already_redeemed(session, record.code, user_id):
        return record, "duplicate_user"

    if _code_remaining(record) <= 0:
        return record, "exhausted"

    consumed_at = datetime.now()
    next_count = _code_count(record) + 1
    record.use_count = next_count
    record.used = user_id
    record.usedtime = consumed_at
    session.add(
        CodeRedeem(
            code=record.code,
            user_id=user_id,
            owner_tg=record.tg,
            code_days=record.us,
            use_index=next_count,
            redeemed_at=consumed_at,
        )
    )

    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        refreshed = session.query(Code).filter(Code.code == record.code).first()
        return refreshed or record, "duplicate_user"

    session.refresh(record)
    return record, "ok"


async def _creator_mention(record: Code) -> str:
    if not record or not record.tg:
        return "未知用户"

    try:
        chat = await bot.get_chat(record.tg)
        display_name = chat.first_name or str(record.tg)
    except Exception:
        display_name = str(record.tg)

    return f"[{display_name}](tg://user?id={record.tg})"


async def _latest_user_mention(record: Code) -> str:
    if not record or not record.used:
        return "未知用户"
    return f"[{record.used}](tg://user?id={record.used})"


async def _reply_code_unavailable(msg, record: Code, code_label: str):
    if record and record.used:
        latest_user = await _latest_user_mention(record)
        return await sendMessage(
            msg,
            f"这个{code_label}已用完，最近一次使用者是 {latest_user}。\n"
            f"总使用进度：{_code_usage_text(record)}",
            timer=60,
        )

    return await sendMessage(
        msg,
        f"这个{code_label}已不可用。\n当前使用进度：{_code_usage_text(record)}" if record else f"这个{code_label}已不可用。",
        timer=60,
    )


async def _reply_code_duplicate(msg, record: Code, code_label: str):
    progress = _code_usage_text(record) if record else "未知"
    return await sendMessage(
        msg,
        f"你已经使用过这个{code_label}了。\n同一个用户对同一个码只能使用一次。\n当前使用进度：{progress}",
        timer=60,
    )


async def rgs_code(_, msg, register_code):
    if _open.stat:
        return await sendMessage(msg, "当前自由注册已开启，暂时不能使用注册码或续期码。")

    data = sql_get_emby(tg=msg.from_user.id)
    if not data:
        return await sendMessage(msg, "未找到你的账号记录，请先私聊发送 /start。")

    embyid = data.embyid
    ex = data.ex
    lv = data.lv

    try:
        if embyid:
            if not is_renew_code(register_code):
                return await sendMessage(msg, "你当前已经有账号，这里只能使用续期码。", timer=60)

            with Session() as session:
                record = _load_locked_code(session, register_code)
                if not record:
                    return await sendMessage(msg, "你输入的续期码不存在，请检查后重试。", timer=60)

                record, status = _apply_code_redeem(session, record, msg.from_user.id)
                if status == "duplicate_user":
                    return await _reply_code_duplicate(msg, record, "续期码")
                if status == "exhausted":
                    return await _reply_code_unavailable(msg, record, "续期码")

                now = datetime.now()
                current_ex = ex if ex and isinstance(ex, datetime) else now
                if now > current_ex:
                    new_ex = now + timedelta(days=record.us)
                    await emby.emby_change_policy(emby_id=embyid, disable=False)
                    if lv == "c":
                        session.query(Emby).filter(Emby.tg == msg.from_user.id).update(
                            {Emby.ex: new_ex, Emby.lv: "b"}
                        )
                    else:
                        session.query(Emby).filter(Emby.tg == msg.from_user.id).update({Emby.ex: new_ex})
                else:
                    new_ex = current_ex + timedelta(days=record.us)
                    session.query(Emby).filter(Emby.tg == msg.from_user.id).update({Emby.ex: new_ex})

                session.commit()

                creator = await _creator_mention(record)
                await sendMessage(
                    msg,
                    f"已收到来自 {creator} 的 {record.us} 天续期。\n"
                    f"当前续期码使用进度：{_code_usage_text(record)}\n"
                    f"到期时间：{new_ex.strftime('%Y-%m-%d %H:%M:%S')}",
                )

                masked_code = _mask_code(register_code)
                await sendMessage(
                    msg,
                    f"🎫 续期码使用 - [{msg.from_user.first_name}](tg://user?id={msg.chat.id}) [{msg.from_user.id}] 使用了 {masked_code}\n"
                    f"📊 使用进度 - {_code_usage_text(record)}\n"
                    f"⏰ 实时到期 - {new_ex.strftime('%Y-%m-%d %H:%M:%S')}",
                    send=True,
                )
                LOGGER.info(
                    f"【续期码】{msg.from_user.first_name}[{msg.chat.id}] 使用了 {register_code}，"
                    f"次数 {_code_usage_text(record)}，到期时间 {new_ex}"
                )
            return

        if is_renew_code(register_code):
            return await sendMessage(msg, "你当前还没有账号，这里只能使用注册码。", timer=60)

        if data.us > 0:
            return await sendMessage(msg, "你已经有注册资格，请先使用“创建账号”。")

        with Session() as session:
            record = _load_locked_code(session, register_code)
            if not record:
                return await sendMessage(msg, "你输入的注册码不存在，请检查后重试。")

            if not _can_use_register_code(register_code, msg.from_user.id):
                return await sendMessage(msg, "这个注册码不属于你可使用的来源。", timer=60)

            record, status = _apply_code_redeem(session, record, msg.from_user.id)
            if status == "duplicate_user":
                return await _reply_code_duplicate(msg, record, "注册码")
            if status == "exhausted":
                return await _reply_code_unavailable(msg, record, "注册码")

            creator = await _creator_mention(record)
            new_credits = (data.us or 0) + record.us
            session.query(Emby).filter(Emby.tg == msg.from_user.id).update({Emby.us: new_credits})
            session.commit()

            await sendPhoto(
                msg,
                photo=bot_photo,
                caption=(
                    f"🎉 已收到 {creator} 发来的注册资格。\n"
                    f"📊 当前注册码使用进度：{_code_usage_text(record)}\n"
                    "👇 请选择接下来的操作。"
                ),
                buttons=register_code_ikb,
            )

            masked_code = _mask_code(register_code)
            await sendMessage(
                msg,
                f"🎫 注册码使用 - [{msg.from_user.first_name}](tg://user?id={msg.chat.id}) [{msg.from_user.id}] 使用了 {masked_code}\n"
                f"📊 使用进度 - {_code_usage_text(record)}",
                send=True,
            )
            LOGGER.info(
                f"【注册码】{msg.from_user.first_name}[{msg.chat.id}] 使用了 {register_code}，"
                f"次数 {_code_usage_text(record)}，获得 {record.us}"
            )
    except Exception:
        LOGGER.exception(f"【兑换失败】user={msg.from_user.id} code={register_code}")
        return await sendMessage(msg, "❌ 兑换过程中出现错误，请稍后重试或联系主人。", timer=60)

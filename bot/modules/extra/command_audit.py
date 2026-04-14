from __future__ import annotations

from pyrogram import filters

from bot import LOGGER, bot, prefixes


def _extract_command_name(message) -> str | None:
    text = str(getattr(message, "text", "") or "").strip()
    if not text:
        return None
    active_prefixes = prefixes if isinstance(prefixes, (list, tuple, set)) else [prefixes]
    prefix_set = {str(item) for item in active_prefixes if str(item)}
    if not prefix_set or text[0] not in prefix_set:
        return None
    command_body = text[1:].split(maxsplit=1)
    if not command_body:
        return None
    command_name = str(command_body[0]).split("@", 1)[0].strip().lower()
    return command_name or None


@bot.on_message(filters.text, group=-1000)
async def audit_command_message(_, message):
    command_name = _extract_command_name(message)
    if not command_name:
        return

    user = getattr(message, "from_user", None)
    sender_chat = getattr(message, "sender_chat", None)
    reply_from_user = getattr(getattr(message, "reply_to_message", None), "from_user", None)
    chat = getattr(message, "chat", None)
    raw_text = str(getattr(message, "text", "") or "").strip()

    LOGGER.info(
        f"command audit: chat={getattr(chat, 'id', None)} "
        f"type={getattr(getattr(chat, 'type', None), 'value', getattr(chat, 'type', None))} "
        f"user={getattr(user, 'id', None)} "
        f"sender_chat={getattr(sender_chat, 'id', None)} "
        f"message={getattr(message, 'id', None)} "
        f"reply_to={getattr(reply_from_user, 'id', None)} "
        f"command={command_name} text={raw_text[:200]!r}"
    )

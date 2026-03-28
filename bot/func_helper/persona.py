from __future__ import annotations

from typing import Any, Callable

from pyrogram import Client
from pyrogram.types import CallbackQuery, Message

_PATCHED = False

MESSAGE_PREFIX = "哼，本女仆这就替你处理。"
SHORT_PREFIX = "哼，本女仆记下了。"
ALERT_PREFIX = "本女仆记下啦"


def _should_skip(text: Any) -> bool:
    if not isinstance(text, str):
        return True
    stripped = text.strip()
    if not stripped:
        return True
    if stripped.startswith(("http://", "https://")):
        return True
    if "本女仆" in stripped[:24]:
        return True
    return False


def stylize_text(text: Any, short: bool = False) -> Any:
    if _should_skip(text):
        return text

    stripped = text.strip()
    prefix = SHORT_PREFIX if short or len(stripped) <= 24 else MESSAGE_PREFIX

    if "\n" in stripped or len(stripped) > 16:
        return f"{prefix}\n\n{text}"
    return f"{prefix} {text}"


def stylize_alert_text(text: Any) -> Any:
    if _should_skip(text):
        return text

    styled = f"{ALERT_PREFIX}，{text}"
    return styled[:180]


def _patch_text_payload(
    args: tuple[Any, ...],
    kwargs: dict[str, Any],
    *,
    kw_name: str,
    position: int,
    transformer: Callable[[Any], Any],
) -> tuple[tuple[Any, ...], dict[str, Any]]:
    if kw_name in kwargs:
        kwargs[kw_name] = transformer(kwargs[kw_name])
        return args, kwargs

    if len(args) > position:
        mutable_args = list(args)
        mutable_args[position] = transformer(mutable_args[position])
        return tuple(mutable_args), kwargs

    return args, kwargs


def install_persona_hooks(bot: Client) -> None:
    global _PATCHED

    if _PATCHED:
        return

    original_send_message = bot.send_message
    original_send_photo = bot.send_photo
    original_send_document = getattr(bot, "send_document", None)

    original_reply_text = Message.reply_text
    original_reply_photo = Message.reply_photo
    original_reply_document = getattr(Message, "reply_document", None)
    original_edit_text = Message.edit_text
    original_answer = CallbackQuery.answer

    async def send_message_wrapper(*args: Any, **kwargs: Any):
        args, kwargs = _patch_text_payload(
            args, kwargs, kw_name="text", position=1, transformer=stylize_text
        )
        return await original_send_message(*args, **kwargs)

    async def send_photo_wrapper(*args: Any, **kwargs: Any):
        args, kwargs = _patch_text_payload(
            args, kwargs, kw_name="caption", position=2, transformer=stylize_text
        )
        return await original_send_photo(*args, **kwargs)

    async def send_document_wrapper(*args: Any, **kwargs: Any):
        args, kwargs = _patch_text_payload(
            args, kwargs, kw_name="caption", position=2, transformer=stylize_text
        )
        return await original_send_document(*args, **kwargs)

    async def reply_text_wrapper(self: Message, *args: Any, **kwargs: Any):
        args, kwargs = _patch_text_payload(
            args, kwargs, kw_name="text", position=0, transformer=stylize_text
        )
        return await original_reply_text(self, *args, **kwargs)

    async def reply_photo_wrapper(self: Message, *args: Any, **kwargs: Any):
        args, kwargs = _patch_text_payload(
            args, kwargs, kw_name="caption", position=1, transformer=stylize_text
        )
        return await original_reply_photo(self, *args, **kwargs)

    async def reply_document_wrapper(self: Message, *args: Any, **kwargs: Any):
        args, kwargs = _patch_text_payload(
            args, kwargs, kw_name="caption", position=1, transformer=stylize_text
        )
        return await original_reply_document(self, *args, **kwargs)

    async def edit_text_wrapper(self: Message, *args: Any, **kwargs: Any):
        args, kwargs = _patch_text_payload(
            args, kwargs, kw_name="text", position=0, transformer=stylize_text
        )
        return await original_edit_text(self, *args, **kwargs)

    async def answer_wrapper(self: CallbackQuery, *args: Any, **kwargs: Any):
        args, kwargs = _patch_text_payload(
            args, kwargs, kw_name="text", position=0, transformer=stylize_alert_text
        )
        return await original_answer(self, *args, **kwargs)

    bot.send_message = send_message_wrapper
    bot.send_photo = send_photo_wrapper

    if original_send_document is not None:
        bot.send_document = send_document_wrapper

    Message.reply_text = reply_text_wrapper
    Message.reply = reply_text_wrapper
    Message.reply_photo = reply_photo_wrapper

    if original_reply_document is not None:
        Message.reply_document = reply_document_wrapper

    Message.edit_text = edit_text_wrapper
    Message.edit = edit_text_wrapper
    CallbackQuery.answer = answer_wrapper

    _PATCHED = True

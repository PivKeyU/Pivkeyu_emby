#!/usr/bin/python3

import aiohttp
from pyrogram.enums import ChatMemberStatus
from pyrogram.errors import BadRequest
from pyrogram.filters import create

from bot import LOGGER, admins, bot_token, group, owner

_LOGGED_INVALID_GROUP_IDS = set()
_BOT_API_ALLOWED_STATUSES = {"creator", "administrator", "member"}


def _iter_valid_group_ids():
    for raw_group_id in group:
        try:
            group_id = int(raw_group_id)
        except (TypeError, ValueError):
            if raw_group_id not in _LOGGED_INVALID_GROUP_IDS:
                LOGGER.error(
                    f"Invalid group id in config.json: {raw_group_id}. "
                    f"Please check the group list."
                )
                _LOGGED_INVALID_GROUP_IDS.add(raw_group_id)
            continue

        if group_id == 0:
            if raw_group_id not in _LOGGED_INVALID_GROUP_IDS:
                LOGGER.error("Invalid group id in config.json: 0. Please check the group list.")
                _LOGGED_INVALID_GROUP_IDS.add(raw_group_id)
            continue

        yield group_id


async def _check_member_via_bot_api(chat_id: int, user_id: int):
    url = f"https://api.telegram.org/bot{bot_token}/getChatMember"
    payload = {"chat_id": chat_id, "user_id": user_id}
    timeout = aiohttp.ClientTimeout(total=10)

    try:
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(url, data=payload) as response:
                data = await response.json(content_type=None)
    except Exception as exc:
        LOGGER.error(f"Bot API getChatMember failed chat={chat_id} user={user_id}: {exc}")
        return None

    if not data.get("ok"):
        description = data.get("description", "unknown error")
        if "user not found" in description.lower() or "participant_id_invalid" in description.lower():
            return False
        if "member not found" in description.lower() or "user not participant" in description.lower():
            return False
        LOGGER.error(f"Bot API getChatMember rejected chat={chat_id} user={user_id}: {description}")
        return None

    result = data.get("result") or {}
    return result.get("status") in _BOT_API_ALLOWED_STATUSES


async def _check_group_membership(client, group_id: int, user_id: int):
    try:
        member = await client.get_chat_member(chat_id=group_id, user_id=user_id)
        return member.status in [
            ChatMemberStatus.ADMINISTRATOR,
            ChatMemberStatus.MEMBER,
            ChatMemberStatus.OWNER,
        ]
    except BadRequest as exc:
        if exc.ID == "USER_NOT_PARTICIPANT":
            return False
        if exc.ID == "CHAT_ADMIN_REQUIRED":
            LOGGER.error(
                f"Bot cannot read members in group {group_id}. "
                f"Check whether the bot is in the group and has enough permissions."
            )
            return False
        LOGGER.error(f"Pyrogram get_chat_member failed group={group_id} user={user_id}: {exc}")
    except (KeyError, ValueError) as exc:
        LOGGER.warning(
            f"Pyrogram peer cache miss for group={group_id} user={user_id}, "
            f"falling back to Bot API: {exc}"
        )
    except Exception as exc:
        LOGGER.error(f"Unexpected get_chat_member failure group={group_id} user={user_id}: {exc}")

    return await _check_member_via_bot_api(group_id, user_id)


async def admins_on_filter(filt, client, update) -> bool:
    user = update.from_user or update.sender_chat
    uid = user.id
    return bool(uid == owner or uid in admins or uid in group)


async def admins_filter(update):
    user = update.from_user or update.sender_chat
    uid = user.id
    return bool(uid == owner or uid in admins)


async def user_in_group_filter(client, update):
    user = update.from_user or update.sender_chat
    uid = user.id

    has_valid_group = False
    for group_id in _iter_valid_group_ids():
        has_valid_group = True
        if await _check_group_membership(client, group_id, uid):
            return True

    if not has_valid_group:
        LOGGER.error("No valid group ids were found in config.json.")
    return False


async def user_in_group_on_filter(filt, client, update):
    user = update.from_user or update.sender_chat
    uid = user.id

    if uid in group:
        return True

    has_valid_group = False
    for group_id in _iter_valid_group_ids():
        has_valid_group = True
        if await _check_group_membership(client, group_id, uid):
            return True

    if not has_valid_group:
        LOGGER.error("No valid group ids were found in config.json.")
    return False


admins_on_filter = create(admins_on_filter)
admins_filter = create(admins_filter)
user_in_group_f = create(user_in_group_filter)
user_in_group_on_filter = create(user_in_group_on_filter)

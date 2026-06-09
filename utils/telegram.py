"""Small Telegram-specific helpers shared across handlers."""
from __future__ import annotations

import asyncio
import logging
from contextlib import suppress

from aiogram import Bot
from aiogram.enums import ChatAction
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import InlineKeyboardMarkup, Message

logger = logging.getLogger(__name__)


async def typing(bot: Bot, chat_id: int, seconds: float = 0.4) -> None:
    """Show a short 'typing…' action to make the bot feel alive.

    Failures are swallowed — a missing animation must never break a flow.
    """
    with suppress(Exception):
        await bot.send_chat_action(chat_id, ChatAction.TYPING)
        await asyncio.sleep(seconds)


async def safe_edit(
    message: Message,
    text: str,
    reply_markup: InlineKeyboardMarkup | None = None,
) -> None:
    """Edit a message, gracefully ignoring the harmless "not modified" error.

    If the message can't be edited for another reason, fall back to sending
    a fresh message so the user never hits a dead end.
    """
    try:
        await message.edit_text(text, reply_markup=reply_markup)
    except TelegramBadRequest as error:
        if "message is not modified" in str(error):
            return
        logger.warning("Не удалось отредактировать сообщение: %s", error)
        with suppress(TelegramBadRequest):
            await message.answer(text, reply_markup=reply_markup)

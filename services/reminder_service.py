"""Streak reminders — gentle daily nudge so an active streak isn't lost.

Deterministic and opt-out-friendly by design: we only message users who were
active *yesterday* and hold a streak (≥ 1), and never more than once a day.
Sending is best-effort — a blocked bot or unreachable chat is swallowed.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import date, timedelta

from aiogram import Bot
from aiogram.exceptions import TelegramForbiddenError, TelegramRetryAfter

from database import models
from services import nudge_service

logger = logging.getLogger(__name__)

# Small pause between sends to stay under Telegram's broadcast rate limits.
_SEND_DELAY = 0.05


async def run_due_reminders(bot: Bot, today: date | None = None) -> int:
    """Send a *personal* streak nudge to every at-risk user. Returns how many sent."""
    today = today or date.today()
    yesterday = (today - timedelta(days=1)).isoformat()
    targets = await models.users_to_remind(yesterday, today.isoformat())

    sent = 0
    for user_id in targets:
        text = await nudge_service.compose(user_id)  # context-aware per user
        delivered = await _send(bot, user_id, text)
        # Mark either way: a blocked user shouldn't be retried again today.
        await models.mark_reminded(user_id, today.isoformat())
        sent += int(delivered)
        await asyncio.sleep(_SEND_DELAY)
    return sent


async def _send(bot: Bot, user_id: int, text: str) -> bool:
    """Deliver one reminder. Never raises — returns whether it went through."""
    try:
        await bot.send_message(user_id, text)
        return True
    except TelegramRetryAfter as exc:
        # Hit a flood limit — wait it out once, then try again.
        await asyncio.sleep(exc.retry_after)
        try:
            await bot.send_message(user_id, text)
            return True
        except Exception:
            return False
    except TelegramForbiddenError:
        return False  # user blocked the bot / never started a chat
    except Exception:
        logger.warning("Не удалось отправить напоминание пользователю %s", user_id)
        return False

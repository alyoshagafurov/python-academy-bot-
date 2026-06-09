"""Lightweight in-process scheduler for periodic background jobs.

Runs as an asyncio task alongside long-polling. The only job today is the daily
streak reminder; the loop is crash-proof (errors are logged, never propagated)
and idempotent (reminder_service guards against double-sends within a day).
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta

from aiogram import Bot

from services import reminder_service

logger = logging.getLogger(__name__)

# Local server hour at which the daily streak reminder goes out.
REMINDER_HOUR = 17


def _seconds_until(hour: int, now: datetime | None = None) -> float:
    """Seconds from now until the next occurrence of `hour:00` (today or tomorrow)."""
    now = now or datetime.now()
    target = now.replace(hour=hour, minute=0, second=0, microsecond=0)
    if target <= now:
        target += timedelta(days=1)
    return (target - now).total_seconds()


async def reminder_loop(bot: Bot) -> None:
    """Once a day at REMINDER_HOUR, nudge users whose streak is about to break."""
    logger.info("⏰ Планировщик напоминаний запущен (ежедневно в %02d:00)", REMINDER_HOUR)
    while True:
        await asyncio.sleep(_seconds_until(REMINDER_HOUR))
        try:
            sent = await reminder_service.run_due_reminders(bot)
            logger.info("📨 Напоминаний отправлено: %d", sent)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Сбой в цикле напоминаний — продолжаю работу")

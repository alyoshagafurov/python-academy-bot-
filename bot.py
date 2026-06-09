"""Python Academy — entry point.

Initializes the database, builds the dispatcher with all routers and
starts long-polling. Run with:  python bot.py
"""
from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import BotCommand, ErrorEvent

from config import config
from database.db import init_db
from handlers import get_main_router
from services import scheduler
from services.diagnostics import run_diagnostics
from utils.logger import setup_logging
from utils.throttling import ThrottlingMiddleware

logger = logging.getLogger(__name__)


async def set_bot_commands(bot: Bot) -> None:
    """Register the command menu shown next to the message input."""
    await bot.set_my_commands([
        BotCommand(command="start", description="🐍 Запустить Knowledge Hub"),
        BotCommand(command="menu", description="🏠 Главное меню"),
        BotCommand(command="courses", description="📚 Курсы и темы"),
        BotCommand(command="codes", description="💻 Готовые коды Minecraft"),
        BotCommand(command="search", description="🔍 Поиск по теории"),
        BotCommand(command="career", description="🎯 Career Path"),
        BotCommand(command="projects", description="🚀 Проекты (PRO)"),
        BotCommand(command="invite", description="🎁 Пригласить друга"),
        BotCommand(command="favorites", description="⭐ Избранное"),
        BotCommand(command="profile", description="👤 Профиль"),
    ])


async def main() -> None:
    setup_logging()
    await init_db()
    run_diagnostics()

    bot = Bot(
        token=config.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()

    # Anti-abuse throttling (shared instance → shared per-user state).
    throttle = ThrottlingMiddleware(min_interval=0.35)
    dp.message.middleware(throttle)
    dp.callback_query.middleware(throttle)

    dp.include_router(get_main_router())

    @dp.errors()
    async def on_error(event: ErrorEvent) -> bool:
        """Catch-all so a single bad update never crashes the bot."""
        logger.exception("Необработанная ошибка в апдейте: %s", event.exception)
        return True

    await set_bot_commands(bot)
    await bot.delete_webhook(drop_pending_updates=True)

    me = await bot.get_me()
    from services import runtime
    runtime.set_bot_username(me.username or "")
    logger.info("🐍 Python Academy запущен как @%s", me.username)

    # Background daily streak reminders (retention) — runs alongside polling.
    reminder_task = asyncio.create_task(scheduler.reminder_loop(bot))

    try:
        await dp.start_polling(bot)
    finally:
        reminder_task.cancel()
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.getLogger(__name__).info("Бот остановлен. Пока! 👋")

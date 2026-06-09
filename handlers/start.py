"""/start, /menu, the home hub and the About screen."""
from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command, CommandObject, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from keyboards import inline
from keyboards.callbacks import MenuCB
from services import (
    level_service,
    progress_service,
    referral_service,
    repetition_service,
    streak_service,
    user_service,
)
from utils import texts
from utils.telegram import safe_edit, typing

router = Router(name="start")


@router.message(CommandStart())
async def cmd_start(message: Message, command: CommandObject, state: FSMContext) -> None:
    await state.clear()
    tg = message.from_user
    user = await user_service.register_user(tg.id, tg.username or tg.full_name)
    await referral_service.attribute(tg.id, command.args)  # deep link: ?start=ref_<id>
    await streak_service.touch(tg.id)  # showing up counts toward the streak
    suggestion = await repetition_service.suggest(tg.id)
    started = (await progress_service.current_lesson(user, progress_service.active_course_id(user))) > 1
    await typing(message.bot, message.chat.id, 0.4)
    await message.answer(
        texts.onboarding(tg.first_name),
        reply_markup=inline.main_menu(suggestion, started=started),
    )


@router.message(Command("menu"))
async def cmd_menu(message: Message, state: FSMContext) -> None:
    await state.clear()
    tg = message.from_user
    user = await user_service.register_user(tg.id, tg.username or tg.full_name)
    suggestion = await repetition_service.suggest(tg.id)
    level = level_service.level_info(user.xp)
    tracks = await progress_service.track_overview(user)
    started = (await progress_service.current_lesson(user, progress_service.active_course_id(user))) > 1
    await message.answer(
        texts.hub(user, level, suggestion, tracks),
        reply_markup=inline.main_menu(suggestion, started=started),
    )


@router.callback_query(MenuCB.filter(F.action == "home"))
async def open_home(query: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    tg = query.from_user
    user = await user_service.register_user(tg.id, tg.username or tg.full_name)
    suggestion = await repetition_service.suggest(tg.id)
    level = level_service.level_info(user.xp)
    tracks = await progress_service.track_overview(user)
    started = (await progress_service.current_lesson(user, progress_service.active_course_id(user))) > 1
    await safe_edit(query.message, texts.hub(user, level, suggestion, tracks),
                    inline.main_menu(suggestion, started=started))
    await query.answer()


@router.callback_query(MenuCB.filter(F.action == "about"))
async def open_about(query: CallbackQuery) -> None:
    await safe_edit(query.message, texts.about(), inline.back_to_menu())
    await query.answer()

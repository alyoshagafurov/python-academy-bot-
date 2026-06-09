"""Daily Challenge: one rewarded task per day with a streak bonus."""
from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from keyboards import inline
from keyboards.callbacks import DailyCB, MenuCB
from services import daily_service, stats_service, user_service
from utils import texts
from utils.telegram import safe_edit, typing

router = Router(name="daily")


@router.callback_query(MenuCB.filter(F.action == "daily"))
async def open_daily(query: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    user = await user_service.get_user(query.from_user.id)
    if user and daily_service.is_done_today(user):
        await safe_edit(query.message, texts.daily_already_done(user), inline.daily_done())
        await query.answer()
        return
    challenge = daily_service.get_today()
    await typing(query.bot, query.message.chat.id, 0.3)
    await safe_edit(query.message, texts.daily_card(challenge), inline.daily_question(challenge.options))
    await query.answer()


@router.callback_query(DailyCB.filter(F.action == "answer"))
async def daily_answer(query: CallbackQuery, callback_data: DailyCB, state: FSMContext) -> None:
    user = await user_service.get_user(query.from_user.id)
    challenge = daily_service.get_today()

    if user and daily_service.is_done_today(user):
        await safe_edit(query.message, texts.daily_already_done(user), inline.daily_done())
        await query.answer("Уже решено сегодня 🙂")
        return

    if not daily_service.check(callback_data.option):
        await stats_service.record_answer(query.from_user.id, challenge.topic, correct=False)
        await query.answer(texts.WRONG_ANSWER_ALERT, show_alert=True)
        return

    result = await daily_service.complete(query.from_user.id)
    if result is None:  # raced with another tap
        await safe_edit(query.message, texts.daily_already_done(user), inline.daily_done())
        await query.answer()
        return

    await typing(query.bot, query.message.chat.id, 0.4)
    await safe_edit(query.message, texts.daily_result(result, challenge), inline.daily_done())
    await query.answer(f"✅ +{result.base_xp + result.bonus_xp} XP")


@router.message(Command("daily"))
async def cmd_daily(message: Message, state: FSMContext) -> None:
    await state.clear()
    tg = message.from_user
    user = await user_service.register_user(tg.id, tg.username or tg.full_name)
    if daily_service.is_done_today(user):
        await message.answer(texts.daily_already_done(user), reply_markup=inline.daily_done())
        return
    challenge = daily_service.get_today()
    await message.answer(texts.daily_card(challenge), reply_markup=inline.daily_question(challenge.options))

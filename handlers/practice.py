"""Practice Mode: categories → difficulty → questions (with FREE/PRO gates)."""
from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from keyboards import inline
from keyboards.callbacks import MenuCB, PracticeCB
from services import feature_service, practice_service, user_service
from utils import texts
from utils.telegram import safe_edit, typing

router = Router(name="practice")


@router.callback_query(MenuCB.filter(F.action == "practice"))
async def open_practice(query: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await safe_edit(query.message, texts.practice_intro(), inline.practice_categories())
    await query.answer()


@router.callback_query(PracticeCB.filter(F.action == "diff"))
async def pick_difficulty(query: CallbackQuery, callback_data: PracticeCB, state: FSMContext) -> None:
    await state.clear()
    user = await user_service.get_user(query.from_user.id)
    await safe_edit(
        query.message,
        texts.practice_pick_difficulty(callback_data.topic),
        inline.practice_difficulties(callback_data.topic, feature_service.is_pro(user)),
    )
    await query.answer()


@router.callback_query(PracticeCB.filter(F.action == "q"))
async def serve_question(query: CallbackQuery, callback_data: PracticeCB, state: FSMContext) -> None:
    topic, difficulty = callback_data.topic, callback_data.difficulty

    # PRO gate: Hard mode.
    if difficulty == "hard":
        user = await user_service.get_user(query.from_user.id)
        if not feature_service.can_hard_mode(user):
            await safe_edit(query.message, texts.upsell("🔴 <b>Hard mode</b> доступен в PRO."), inline.upsell())
            await query.answer(texts.PRO_LOCKED_ALERT, show_alert=True)
            return

    index = practice_service.random_index(topic, difficulty)
    question = practice_service.get_question(topic, difficulty, index)
    if question is None:
        await query.answer("Скоро добавим вопросы по этой теме!", show_alert=True)
        return
    await typing(query.bot, query.message.chat.id, 0.3)
    await safe_edit(
        query.message,
        texts.practice_question(question, difficulty),
        inline.practice_question(topic, difficulty, index, question.options),
    )
    await query.answer()


@router.callback_query(PracticeCB.filter(F.action == "answer"))
async def practice_answer(query: CallbackQuery, callback_data: PracticeCB, state: FSMContext) -> None:
    # FREE daily quota.
    allowed, _used, limit = await feature_service.practice_quota(query.from_user.id)
    if not allowed:
        await safe_edit(query.message, texts.practice_limit_reached(limit), inline.upsell())
        await query.answer("Лимит на сегодня 🚦", show_alert=True)
        return
    await feature_service.consume_practice(query.from_user.id)

    result = await practice_service.answer(
        query.from_user.id, callback_data.topic, callback_data.difficulty,
        callback_data.index, callback_data.option,
    )
    await safe_edit(
        query.message,
        texts.practice_result(result),
        inline.practice_result(callback_data.topic, callback_data.difficulty),
    )
    await query.answer(f"✅ +{result.xp_gain} XP" if result.correct else "❌ Неверно")


@router.message(Command("practice"))
async def cmd_practice(message: Message, state: FSMContext) -> None:
    await state.clear()
    tg = message.from_user
    await user_service.register_user(tg.id, tg.username or tg.full_name)
    await message.answer(texts.practice_intro(), reply_markup=inline.practice_categories())

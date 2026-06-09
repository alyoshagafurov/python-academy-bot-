"""Smart Coach — career-readiness dashboard + next-focus guidance."""
from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from keyboards import inline
from keyboards.callbacks import MenuCB
from services import coach_service, user_service
from utils import texts
from utils.telegram import safe_edit, typing

router = Router(name="coach")


@router.callback_query(MenuCB.filter(F.action == "coach"))
async def open_coach(query: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    report = await coach_service.report(query.from_user.id)
    if report is None:
        await query.answer()
        return
    await typing(query.bot, query.message.chat.id, 0.4)
    await safe_edit(query.message, texts.coach(report), inline.coach())
    await query.answer()


@router.message(Command("coach"))
async def cmd_coach(message: Message, state: FSMContext) -> None:
    await state.clear()
    tg = message.from_user
    await user_service.register_user(tg.id, tg.username or tg.full_name)
    report = await coach_service.report(tg.id)
    if report is not None:
        await message.answer(texts.coach(report), reply_markup=inline.coach())

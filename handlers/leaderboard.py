"""Weekly leaderboard."""
from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from keyboards import inline
from keyboards.callbacks import MenuCB
from services import leaderboard_service, user_service
from utils import texts
from utils.telegram import safe_edit

router = Router(name="leaderboard")


@router.callback_query(MenuCB.filter(F.action == "leaders"))
async def open_leaderboard(query: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    board = await leaderboard_service.get(query.from_user.id)
    await safe_edit(query.message, texts.leaderboard(board), inline.leaderboard())
    await query.answer()


@router.message(Command("top"))
async def cmd_top(message: Message, state: FSMContext) -> None:
    await state.clear()
    tg = message.from_user
    await user_service.register_user(tg.id, tg.username or tg.full_name)
    board = await leaderboard_service.get(tg.id)
    await message.answer(texts.leaderboard(board), reply_markup=inline.leaderboard())

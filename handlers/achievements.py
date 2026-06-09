"""Achievements gallery (locked + unlocked)."""
from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from keyboards import inline
from keyboards.callbacks import MenuCB
from services import achievement_service
from utils import texts
from utils.telegram import safe_edit

router = Router(name="achievements")


@router.callback_query(MenuCB.filter(F.action == "achievements"))
async def open_achievements(query: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    status = await achievement_service.get_status(query.from_user.id)
    await safe_edit(query.message, texts.achievements(status), inline.achievements())
    await query.answer()

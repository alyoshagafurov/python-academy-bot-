"""Fallback handlers for anything not matched above.

Registered last so it only catches leftovers: stray text messages and
expired inline buttons.
"""
from __future__ import annotations

from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from keyboards import inline
from states import LessonStates
from utils import texts

router = Router(name="common")


@router.message()
async def fallback_message(message: Message, state: FSMContext) -> None:
    """Gently redirect free-text input back to the buttons."""
    current = await state.get_state()
    if current in {LessonStates.reading.state, LessonStates.solving.state}:
        await message.answer(texts.IN_LESSON_HINT)
    else:
        await message.answer(texts.USE_BUTTONS_HINT, reply_markup=inline.main_menu())


@router.callback_query()
async def fallback_callback(query: CallbackQuery) -> None:
    """Acknowledge clicks on outdated buttons so the spinner stops."""
    await query.answer(texts.STALE_BUTTON_ALERT)

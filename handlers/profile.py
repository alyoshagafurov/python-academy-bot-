"""User profile: reading progress, level, streak, favourites, course %."""
from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from keyboards import inline
from keyboards.callbacks import MenuCB
from lessons import get_course
from services import bookmark_service, level_service, progress_service, user_service
from utils import texts
from utils.telegram import safe_edit

router = Router(name="profile")


async def _build(user_id: int) -> str | None:
    user = await user_service.get_user(user_id)
    if user is None:
        return None
    level = level_service.level_info(user.xp)
    tracks = await progress_service.track_overview(user)
    bookmarks_count = await bookmark_service.count(user_id)

    beginner = get_course(progress_service.BEGINNER)
    student = get_course(progress_service.STUDENT)
    b_done = max(0, user.current_lesson - 1)
    s_cur = await progress_service.current_lesson(user, progress_service.STUDENT)
    s_done = max(0, s_cur - 1)
    lessons_read = b_done + s_done
    total_all = beginner.total + student.total

    return texts.profile(user, level, lessons_read, total_all, bookmarks_count, tracks)


@router.callback_query(MenuCB.filter(F.action == "profile"))
async def open_profile(query: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    text = await _build(query.from_user.id)
    if text is None:
        await query.answer()
        return
    await safe_edit(query.message, text, inline.profile())
    await query.answer()


@router.message(Command("profile"))
async def cmd_profile(message: Message, state: FSMContext) -> None:
    await state.clear()
    tg = message.from_user
    await user_service.register_user(tg.id, tg.username or tg.full_name)
    text = await _build(tg.id)
    if text is not None:
        await message.answer(text, reply_markup=inline.profile())

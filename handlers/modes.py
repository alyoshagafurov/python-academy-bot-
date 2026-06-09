"""Learning-track selection: 🔵 Beginner and 🟣 Student are both playable."""
from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from keyboards import inline
from keyboards.callbacks import MenuCB, ModeCB
from lessons import get_course
from services import course_service, progress_service, user_service
from utils import texts
from utils.telegram import safe_edit

router = Router(name="modes")


@router.callback_query(MenuCB.filter(F.action == "learn"))
async def open_modes(query: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await safe_edit(query.message, texts.choose_mode(), inline.modes())
    await query.answer()


@router.callback_query(ModeCB.filter(F.mode == "beginner"))
async def choose_beginner(query: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    uid = query.from_user.id
    await user_service.select_mode(uid, "beginner")
    await progress_service.set_active(uid, progress_service.BEGINNER)
    user = await user_service.get_user(uid)
    course = get_course(progress_service.BEGINNER)
    cur = user.current_lesson
    xp_earned = course_service.course_xp_earned(cur, course)
    await safe_edit(query.message, texts.course_overview(course, cur, xp_earned), inline.course_stages(course, cur))
    await query.answer("Трек: 🔵 Новичок")


@router.callback_query(ModeCB.filter(F.mode == "student"))
async def choose_student(query: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    uid = query.from_user.id
    await user_service.select_mode(uid, "student")
    await progress_service.set_active(uid, progress_service.STUDENT)
    user = await user_service.get_user(uid)
    course = get_course(progress_service.STUDENT)
    cur = await progress_service.current_lesson(user, progress_service.STUDENT)
    await safe_edit(query.message, texts.backend_journey(course, cur), inline.course_stages(course, cur))
    await query.answer("Трек: 🟣 Student")


@router.callback_query(ModeCB.filter(F.mode == "kid"))
async def choose_kid(query: CallbackQuery) -> None:
    await safe_edit(query.message, texts.coming_soon(), inline.coming_soon())
    await query.answer("🚧 Скоро!")

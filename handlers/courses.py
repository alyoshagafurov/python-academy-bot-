"""Course navigation: Course select → Course/Journey → Stage (lessons)."""
from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from database.models import User
from keyboards import inline
from keyboards.callbacks import CourseCB, MenuCB, StageCB
from lessons import all_courses, get_course
from services import course_service, progress_service, user_service
from utils import texts
from utils.telegram import safe_edit

router = Router(name="courses")


async def _selection_text(user: User) -> str:
    infos = []
    for course in all_courses().values():
        cur = await progress_service.current_lesson(user, course.id)
        _, _, pct = course_service.course_progress(cur, course)
        infos.append((course, pct))
    return texts.course_selection(infos)


async def _render_course(query: CallbackQuery, user: User, course_id: str) -> None:
    """Show a course's home screen (Journey for Student, stage list for Beginner)."""
    course = get_course(course_id)
    cur = await progress_service.current_lesson(user, course_id)
    await progress_service.set_active(user.user_id, course_id)
    if course.track == "student":
        text = texts.backend_journey(course, cur)
    else:
        xp_earned = course_service.course_xp_earned(cur, course)
        text = texts.course_overview(course, cur, xp_earned)
    await safe_edit(query.message, text, inline.course_stages(course, cur))


@router.callback_query(MenuCB.filter(F.action == "lessons"))
async def open_courses(query: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    user = await user_service.get_user(query.from_user.id)
    if user is None:
        await query.answer()
        return
    await safe_edit(query.message, await _selection_text(user), inline.course_select(list(all_courses().values())))
    await query.answer()


@router.callback_query(CourseCB.filter())
async def open_course(query: CallbackQuery, callback_data: CourseCB, state: FSMContext) -> None:
    await state.clear()
    user = await user_service.get_user(query.from_user.id)
    if user is None:
        await query.answer()
        return
    course_id = callback_data.course_id
    if course_id not in all_courses():
        await safe_edit(query.message, texts.coming_soon(), inline.coming_soon())
        await query.answer("🚧 Скоро!")
        return
    await _render_course(query, user, course_id)
    await query.answer()


@router.callback_query(StageCB.filter())
async def open_stage(query: CallbackQuery, callback_data: StageCB, state: FSMContext) -> None:
    await state.clear()
    user = await user_service.get_user(query.from_user.id)
    if user is None:
        await query.answer()
        return
    course_id = progress_service.active_course_id(user)
    course = get_course(course_id)
    cur = await progress_service.current_lesson(user, course_id)
    stage = course.stage(callback_data.stage_id)
    if stage is None:
        await query.answer()
        return
    if not course_service.stage_unlocked(stage, cur):
        await query.answer(texts.STAGE_LOCKED_ALERT, show_alert=True)
        return
    await safe_edit(query.message, texts.stage_overview(stage, cur), inline.stage_lessons(course, stage.id, cur))
    await query.answer()


@router.message(Command(commands=["courses", "lessons"]))
async def cmd_courses(message: Message, state: FSMContext) -> None:
    await state.clear()
    tg = message.from_user
    user = await user_service.register_user(tg.id, tg.username or tg.full_name)
    await message.answer(await _selection_text(user), reply_markup=inline.course_select(list(all_courses().values())))

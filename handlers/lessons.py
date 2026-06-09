"""Theory reading flow (knowledge-hub mode).

A lesson is pure theory: explanation, analogy, real-world example, code sample,
breakdown and common mistakes — plus controls to explain it simpler, jump to
related topics, bookmark it, or mark it read (which advances progress + streak).

Free browsing: any lesson opens directly (no locks), so search / related /
favourites can jump anywhere. Sequential progress is still tracked for
"continue" and course %.
"""
from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from keyboards import inline
from keyboards.callbacks import LessonCB, MenuCB, ReadCB
from lessons import Course, Lesson, get_course, get_lesson
from services import (
    bookmark_service,
    course_service,
    lesson_service,
    progress_service,
    related_service,
    user_service,
)
from states import LessonStates
from utils import texts
from utils.telegram import safe_edit, typing

router = Router(name="lessons")


async def _context(query: CallbackQuery) -> tuple[object, str, Course]:
    user = await user_service.get_user(query.from_user.id)
    course_id = progress_service.active_course_id(user) if user else progress_service.BEGINNER
    return user, course_id, get_course(course_id)


async def _render_lesson(query: CallbackQuery, state: FSMContext, course_id: str,
                         course: Course, lesson: Lesson) -> None:
    """Render a theory lesson (or a placeholder notice)."""
    if lesson.placeholder:
        await state.clear()
        await safe_edit(query.message, texts.placeholder_lesson(lesson, course), inline.placeholder_card(lesson.stage_id))
        await query.answer()
        return

    uid = query.from_user.id
    await state.set_state(LessonStates.reading)
    await state.update_data(lesson_id=lesson.id, course_id=course_id)
    bookmarked = await bookmark_service.is_bookmarked(uid, course_id, lesson.id)
    has_next = lesson.id < course.total
    await typing(query.bot, query.message.chat.id, 0.4)
    await safe_edit(
        query.message,
        texts.lesson_card(lesson, course=course),
        inline.lesson_card(lesson, bookmarked=bookmarked, has_next=has_next),
    )


async def _course_home(query: CallbackQuery, course: Course, cur: int) -> None:
    if course.track == "student":
        text = texts.backend_journey(course, cur)
    else:
        text = texts.course_overview(course, cur, course_service.course_xp_earned(cur, course))
    await safe_edit(query.message, text, inline.course_stages(course, cur))


@router.callback_query(MenuCB.filter(F.action == "continue"))
async def continue_learning(query: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    user, course_id, course = await _context(query)
    if user is None or (course_id == progress_service.BEGINNER
                        and not user.selected_mode and user.current_lesson == 1):
        await safe_edit(query.message, texts.choose_mode(need_choice=True), inline.modes())
        await query.answer()
        return

    cur = await progress_service.current_lesson(user, course_id)
    lesson = get_lesson(min(cur, course.total), course_id)
    if lesson is None or cur > course.total:
        await _course_home(query, course, cur)
        await query.answer("🎉 Курс пройден!")
        return
    await _render_lesson(query, state, course_id, course, lesson)
    await query.answer()


@router.callback_query(LessonCB.filter(F.action == "open"))
async def open_lesson(query: CallbackQuery, callback_data: LessonCB, state: FSMContext) -> None:
    user, course_id, course = await _context(query)
    lesson = get_lesson(callback_data.lesson_id, course_id)
    if lesson is None:
        await query.answer()
        return
    await _render_lesson(query, state, course_id, course, lesson)  # free browsing, no locks
    await query.answer()


@router.callback_query(ReadCB.filter())
async def open_read(query: CallbackQuery, callback_data: ReadCB, state: FSMContext) -> None:
    """Open any lesson in a given course (from search / related / favourites / recs)."""
    course_id = progress_service.code_to_id(callback_data.course)
    course = get_course(course_id)
    lesson = get_lesson(callback_data.lesson_id, course_id)
    if lesson is None:
        await query.answer()
        return
    await progress_service.set_active(query.from_user.id, course_id)  # so follow-up actions resolve here
    await _render_lesson(query, state, course_id, course, lesson)
    await query.answer()


@router.callback_query(LessonCB.filter(F.action == "read"))
async def read_next(query: CallbackQuery, callback_data: LessonCB, state: FSMContext) -> None:
    user, course_id, course = await _context(query)
    lesson = get_lesson(callback_data.lesson_id, course_id)
    if lesson is None:
        await query.answer()
        return
    result = await lesson_service.mark_read(query.from_user.id, lesson.id, course_id)
    toast = f"📖 +{result.xp_gain} XP" if result.awarded else "📖 Прочитано"

    next_lesson = get_lesson(lesson.id + 1, course_id)
    if next_lesson is None:
        cur = await progress_service.current_lesson(await user_service.get_user(query.from_user.id), course_id)
        await _course_home(query, course, cur)
        await query.answer("🎉 Курс пройден!")
        return
    await _render_lesson(query, state, course_id, course, next_lesson)
    await query.answer(toast)


@router.callback_query(LessonCB.filter(F.action == "simple"))
async def explain_simpler(query: CallbackQuery, callback_data: LessonCB, state: FSMContext) -> None:
    _, course_id, _ = await _context(query)
    lesson = get_lesson(callback_data.lesson_id, course_id)
    if lesson is None:
        await query.answer()
        return
    await safe_edit(query.message, texts.lesson_simple(lesson), inline.lesson_simple(lesson))
    await query.answer()


@router.callback_query(LessonCB.filter(F.action == "related"))
async def show_related(query: CallbackQuery, callback_data: LessonCB, state: FSMContext) -> None:
    _, course_id, _ = await _context(query)
    lesson = get_lesson(callback_data.lesson_id, course_id)
    if lesson is None:
        await query.answer()
        return
    items = related_service.related(course_id, lesson)
    await safe_edit(query.message, texts.related_list(lesson, items), inline.related_lessons(lesson, items))
    await query.answer()


@router.callback_query(LessonCB.filter(F.action == "bookmark"))
async def toggle_bookmark(query: CallbackQuery, callback_data: LessonCB, state: FSMContext) -> None:
    _, course_id, course = await _context(query)
    lesson = get_lesson(callback_data.lesson_id, course_id)
    if lesson is None:
        await query.answer()
        return
    now_saved = await bookmark_service.toggle(query.from_user.id, course_id, lesson.id)
    has_next = lesson.id < course.total
    await safe_edit(
        query.message,
        texts.lesson_card(lesson, course=course),
        inline.lesson_card(lesson, bookmarked=now_saved, has_next=has_next),
    )
    await query.answer("⭐ В избранном" if now_saved else "Убрано из избранного")

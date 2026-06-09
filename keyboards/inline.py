"""Inline keyboard builders."""
from __future__ import annotations

from typing import TYPE_CHECKING

from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from keyboards.callbacks import (
    BuyCB, CertCB, CodeCB, CourseCB, DailyCB, LessonCB, MenuCB, ModeCB,
    PracticeCB, ProjectCB, ReadCB, SandboxCB, SnippetCB, StageCB,
)
from services import pricing
from lessons import coding_tasks, get_course, get_stage, total_lessons
from lessons.practice import CATEGORIES, DIFFICULTIES
from lessons.schema import Lesson, Stage
from utils.constants import CODE_CATEGORIES, DIFFICULTY_NAMES, topic_emoji, topic_name

_DIFF_ICON = {"easy": "🟢", "medium": "🟡", "hard": "🔴"}

if TYPE_CHECKING:
    from services.repetition_service import ReviewSuggestion


def _lesson_icon(lesson_id: int, current: int) -> str:
    return "✅" if lesson_id < current else ("▶️" if lesson_id == current else "🔒")


def _stage_icon(stage: Stage, current: int) -> str:
    if current > stage.last_id:
        return "✅"
    return "▶️" if current >= stage.first_id else "🔒"


# ──────────────────────────────── Menus ───────────────────────────────────

def main_menu(suggestion: "ReviewSuggestion | None" = None, started: bool = True) -> InlineKeyboardMarkup:
    """Python knowledge hub — theory + the paid program hooks (career, projects, PRO)."""
    kb = InlineKeyboardBuilder()
    first = "▶️ Продолжить чтение" if started else "🚀 Начать с основ"
    kb.button(text=first, callback_data=MenuCB(action="continue"))
    kb.button(text="📚 Курсы", callback_data=MenuCB(action="lessons"))
    kb.button(text="🔍 Поиск", callback_data=MenuCB(action="search"))
    kb.button(text="🎯 Career Path", callback_data=MenuCB(action="career"))
    kb.button(text="🚀 Проекты", callback_data=MenuCB(action="projects"))
    kb.button(text="🧠 Рекомендации", callback_data=MenuCB(action="recommend"))
    kb.button(text="⭐ Избранное", callback_data=MenuCB(action="favorites"))
    kb.button(text="💎 PRO", callback_data=MenuCB(action="pro"))
    kb.button(text="🎁 Пригласить друга", callback_data=MenuCB(action="invite"))
    kb.button(text="👤 Профиль", callback_data=MenuCB(action="profile"))
    kb.button(text="ℹ️ О боте", callback_data=MenuCB(action="about"))
    kb.adjust(1, 2, 2, 2, 2, 2)
    return kb.as_markup()


# ─────────────────────── Premium: offer / invite / career / cert ──────────

def offer(is_pro: bool) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    if not is_pro:
        for product in pricing.PRODUCTS:
            kb.button(text=f"💎 {product.title} · {product.stars}⭐", callback_data=BuyCB(product=product.id))
    kb.button(text="🎁 Пригласить друга", callback_data=MenuCB(action="invite"))
    kb.button(text="🏠 Меню", callback_data=MenuCB(action="home"))
    kb.adjust(*([1] * (0 if is_pro else len(pricing.PRODUCTS))), 1, 1)
    return kb.as_markup()


def after_purchase() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="🚀 Проекты", callback_data=MenuCB(action="projects"))
    kb.button(text="🎯 Career Path", callback_data=MenuCB(action="career"))
    kb.button(text="🎁 Пригласить друга", callback_data=MenuCB(action="invite"))
    kb.button(text="🏠 Меню", callback_data=MenuCB(action="home"))
    kb.adjust(2, 1, 1)
    return kb.as_markup()


def invite() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="💎 Открыть PRO", callback_data=MenuCB(action="pro"))
    kb.button(text="🏠 Меню", callback_data=MenuCB(action="home"))
    kb.adjust(1, 1)
    return kb.as_markup()


def career(is_pro: bool) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="▶️ Продолжить", callback_data=MenuCB(action="continue"))
    kb.button(text="🚀 Проекты", callback_data=MenuCB(action="projects"))
    if not is_pro:
        kb.button(text="💎 Ускориться в PRO", callback_data=MenuCB(action="pro"))
    kb.button(text="🏠 Меню", callback_data=MenuCB(action="home"))
    kb.adjust(2, 1, 1) if not is_pro else kb.adjust(2, 1)
    return kb.as_markup()


def certificate(*, share_url: str = "", show_pro: bool = False) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    if share_url:
        kb.button(text="📤 Поделиться", url=share_url)
    if show_pro:
        kb.button(text="💎 Открыть PRO", callback_data=MenuCB(action="pro"))
    kb.button(text="📚 Курсы", callback_data=MenuCB(action="lessons"))
    kb.button(text="🏠 Меню", callback_data=MenuCB(action="home"))
    kb.adjust(1, 1, 2)
    return kb.as_markup()


def back_to_menu() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="🏠 Меню", callback_data=MenuCB(action="home"))
    return kb.as_markup()


def modes() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="🟢 Детский", callback_data=ModeCB(mode="kid"))
    kb.button(text="🔵 Новичок", callback_data=ModeCB(mode="beginner"))
    kb.button(text="🟣 Студент", callback_data=ModeCB(mode="student"))
    kb.button(text="🏠 Меню", callback_data=MenuCB(action="home"))
    kb.adjust(1)
    return kb.as_markup()


def coming_soon() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="🔵 Перейти к Новичку", callback_data=ModeCB(mode="beginner"))
    kb.button(text="🏠 Меню", callback_data=MenuCB(action="home"))
    kb.adjust(1)
    return kb.as_markup()


# ───────────────────────── Courses → Stages → Lessons ─────────────────────

def course_select(courses) -> InlineKeyboardMarkup:
    """One button per discovered course (scales to any number of courses)."""
    kb = InlineKeyboardBuilder()
    for course in courses:
        kb.button(text=f"{course.emoji} {course.title}", callback_data=CourseCB(course_id=course.id))
    kb.button(text="🏠 Меню", callback_data=MenuCB(action="home"))
    kb.adjust(*([1] * len(courses)), 1)
    return kb.as_markup()


def course_stages(course: "Course", current_lesson: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for stage in course.stages:
        icon = _stage_icon(stage, current_lesson)
        kb.button(text=f"{icon} Этап {stage.id}. {stage.title}", callback_data=StageCB(stage_id=stage.id))
    kb.button(text="▶️ Продолжить", callback_data=MenuCB(action="continue"))
    # The Minecraft course gets a ready-to-copy code library.
    extra = 0
    if course.id == "python_minecraft":
        kb.button(text="💻 Готовые коды", callback_data=SnippetCB(action="home"))
        extra = 1
    kb.button(text="⬅️ Курсы", callback_data=MenuCB(action="lessons"))
    kb.button(text="🏠 Меню", callback_data=MenuCB(action="home"))
    kb.adjust(*([1] * len(course.stages)), 1, *([1] * extra), 2)
    return kb.as_markup()


# ──────────────────────────── Code library (Minecraft) ────────────────────

_SNIP_DIFF = {"easy": "🟢", "medium": "🟡", "hard": "🔴"}


def snippet_categories(categories) -> InlineKeyboardMarkup:
    """`categories` is a list of (cat_id, emoji, title)."""
    kb = InlineKeyboardBuilder()
    for cat_id, emoji, title in categories:
        kb.button(text=f"{emoji} {title}", callback_data=SnippetCB(action="cat", category=cat_id))
    kb.button(text="⬅️ К курсу", callback_data=CourseCB(course_id="python_minecraft"))
    kb.button(text="🏠 Меню", callback_data=MenuCB(action="home"))
    kb.adjust(*([1] * len(categories)), 2)
    return kb.as_markup()


def snippet_list_kb(category: str, snips) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for s in snips:
        icon = _SNIP_DIFF.get(s.difficulty, "🟢")
        kb.button(text=f"{icon} {s.title}", callback_data=SnippetCB(action="view", snippet_id=s.id))
    kb.button(text="⬅️ Категории", callback_data=SnippetCB(action="home"))
    kb.button(text="🏠 Меню", callback_data=MenuCB(action="home"))
    kb.adjust(*([1] * len(snips)), 2)
    return kb.as_markup()


def snippet_card_kb(category: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="⬅️ Назад", callback_data=SnippetCB(action="cat", category=category))
    kb.button(text="📚 Все категории", callback_data=SnippetCB(action="home"))
    kb.adjust(2)
    return kb.as_markup()


def stage_lessons(course: "Course", stage_id: int, current_lesson: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    stage = course.stage(stage_id)
    if stage is not None:
        for index, lesson in enumerate(stage.lessons, start=1):
            icon = _lesson_icon(lesson.id, current_lesson)
            kb.button(text=f"{icon} {index}. {lesson.title}", callback_data=LessonCB(action="open", lesson_id=lesson.id))
    kb.button(text="⬅️ Этапы", callback_data=CourseCB(course_id=course.id))
    kb.button(text="🏠 Меню", callback_data=MenuCB(action="home"))
    kb.adjust(1)
    return kb.as_markup()


def placeholder_card(stage_id: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="⬅️ К этапу", callback_data=StageCB(stage_id=stage_id))
    kb.button(text="🏠 Меню", callback_data=MenuCB(action="home"))
    kb.adjust(2)
    return kb.as_markup()


_COURSE_CODE = {"python_beginner": "b", "python_student": "s",
                "web_htmlcss": "h", "web_python": "w",
                "python_minecraft": "m"}


def lesson_card(lesson: Lesson, *, bookmarked: bool = False, has_next: bool = False) -> InlineKeyboardMarkup:
    """Theory-reading controls: simpler view, related topics, bookmark, next."""
    kb = InlineKeyboardBuilder()
    kb.button(text="💡 Объяснить проще", callback_data=LessonCB(action="simple", lesson_id=lesson.id))
    kb.button(text="🔗 Похожие темы", callback_data=LessonCB(action="related", lesson_id=lesson.id))
    kb.button(text="✅ В избранном" if bookmarked else "⭐ В избранное",
              callback_data=LessonCB(action="bookmark", lesson_id=lesson.id))
    if has_next:
        kb.button(text="➡️ Прочитал, дальше", callback_data=LessonCB(action="read", lesson_id=lesson.id))
    kb.button(text="⬅️ К этапу", callback_data=StageCB(stage_id=lesson.stage_id))
    kb.button(text="🏠 Меню", callback_data=MenuCB(action="home"))
    kb.adjust(2, 1, 1, 2) if has_next else kb.adjust(2, 1, 2)
    return kb.as_markup()


def lesson_simple(lesson: Lesson) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="📖 Полная версия", callback_data=LessonCB(action="open", lesson_id=lesson.id))
    kb.button(text="🔗 Похожие", callback_data=LessonCB(action="related", lesson_id=lesson.id))
    kb.button(text="🏠 Меню", callback_data=MenuCB(action="home"))
    kb.adjust(2, 1)
    return kb.as_markup()


def _link_buttons(kb: InlineKeyboardBuilder, items) -> None:
    """Append one 'open lesson' button per item (search / related / bookmark / rec)."""
    for it in items:
        code = _COURSE_CODE.get(it.course_id, "b")
        kb.button(text=f"{topic_emoji(it.lesson.topic)} {it.lesson.title}",
                  callback_data=ReadCB(course=code, lesson_id=it.lesson.id))


def related_lessons(source: Lesson, items) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    _link_buttons(kb, items)
    kb.button(text="📖 К теме", callback_data=LessonCB(action="open", lesson_id=source.id))
    kb.button(text="🏠 Меню", callback_data=MenuCB(action="home"))
    kb.adjust(*([1] * len(items)), 2)
    return kb.as_markup()


def search_results(hits) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    _link_buttons(kb, hits)
    kb.button(text="🔍 Новый поиск", callback_data=MenuCB(action="search"))
    kb.button(text="🏠 Меню", callback_data=MenuCB(action="home"))
    kb.adjust(*([1] * len(hits)), 2)
    return kb.as_markup()


def bookmarks(items) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    _link_buttons(kb, items)
    kb.button(text="🏠 Меню", callback_data=MenuCB(action="home"))
    kb.adjust(*([1] * len(items)), 1)
    return kb.as_markup()


def recommendations(recs) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    _link_buttons(kb, recs)
    kb.button(text="📚 Курсы", callback_data=MenuCB(action="lessons"))
    kb.button(text="🏠 Меню", callback_data=MenuCB(action="home"))
    kb.adjust(*([1] * len(recs)), 2)
    return kb.as_markup()


def practice_card(lesson_id: int, options: tuple[str, ...]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for index, option in enumerate(options):
        kb.button(text=option, callback_data=LessonCB(action="pans", lesson_id=lesson_id, option=index))
    kb.button(text="⬅️ К уроку", callback_data=LessonCB(action="open", lesson_id=lesson_id))
    kb.adjust(2, 2, 1)
    return kb.as_markup()


def practice_to_test(lesson_id: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="📝 Пройти тест", callback_data=LessonCB(action="quiz", lesson_id=lesson_id))
    kb.button(text="⬅️ К уроку", callback_data=LessonCB(action="open", lesson_id=lesson_id))
    kb.adjust(1)
    return kb.as_markup()


def quiz(lesson_id: int, stage_id: int, options: tuple[str, ...]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for index, option in enumerate(options):
        kb.button(text=option, callback_data=LessonCB(action="answer", lesson_id=lesson_id, option=index))
    kb.button(text="⬅️ К этапу", callback_data=StageCB(stage_id=stage_id))
    kb.adjust(2, 2, 1)
    return kb.as_markup()


def lesson_result(lesson_id: int, stage_id: int, has_challenge: bool,
                  course: "Course | None" = None) -> InlineKeyboardMarkup:
    total = (course or get_course()).total
    kb = InlineKeyboardBuilder()
    if has_challenge:
        kb.button(text="⚡ Challenge (бонус)", callback_data=LessonCB(action="challenge", lesson_id=lesson_id))
    if lesson_id < total:
        kb.button(text="➡️ Следующий урок", callback_data=LessonCB(action="open", lesson_id=lesson_id + 1))
    kb.button(text="⬅️ К этапу", callback_data=StageCB(stage_id=stage_id))
    kb.button(text="🏠 Меню", callback_data=MenuCB(action="home"))
    kb.adjust(1, 1, 2)
    return kb.as_markup()


def challenge(lesson_id: int, stage_id: int, options: tuple[str, ...]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for index, option in enumerate(options):
        kb.button(text=option, callback_data=LessonCB(action="chans", lesson_id=lesson_id, option=index))
    kb.button(text="⬅️ К этапу", callback_data=StageCB(stage_id=stage_id))
    kb.adjust(2, 2, 1)
    return kb.as_markup()


def challenge_result(lesson_id: int, stage_id: int, course: "Course | None" = None) -> InlineKeyboardMarkup:
    total = (course or get_course()).total
    kb = InlineKeyboardBuilder()
    if lesson_id < total:
        kb.button(text="➡️ Следующий урок", callback_data=LessonCB(action="open", lesson_id=lesson_id + 1))
    kb.button(text="⬅️ К этапу", callback_data=StageCB(stage_id=stage_id))
    kb.button(text="🏠 Меню", callback_data=MenuCB(action="home"))
    kb.adjust(1, 2)
    return kb.as_markup()


# ─────────────────────────────── Practice ─────────────────────────────────

def practice_categories() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for topic, label in CATEGORIES:
        kb.button(text=label, callback_data=PracticeCB(action="diff", topic=topic))
    kb.button(text="🏠 Меню", callback_data=MenuCB(action="home"))
    kb.adjust(1)
    return kb.as_markup()


def practice_difficulties(topic: str, is_pro: bool) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for difficulty in DIFFICULTIES:
        label = DIFFICULTY_NAMES[difficulty]
        if difficulty == "hard" and not is_pro:
            label += " 🔒"
        kb.button(text=label, callback_data=PracticeCB(action="q", topic=topic, difficulty=difficulty))
    kb.button(text="⬅️ Категории", callback_data=MenuCB(action="practice"))
    kb.adjust(3, 1)
    return kb.as_markup()


def practice_question(topic: str, difficulty: str, index: int, options: tuple[str, ...]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for opt_index, option in enumerate(options):
        kb.button(
            text=option,
            callback_data=PracticeCB(action="answer", topic=topic, difficulty=difficulty, index=index, option=opt_index),
        )
    kb.button(text="⬅️ Категории", callback_data=MenuCB(action="practice"))
    kb.adjust(2, 2, 1)
    return kb.as_markup()


def practice_result(topic: str, difficulty: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="🔁 Ещё вопрос", callback_data=PracticeCB(action="q", topic=topic, difficulty=difficulty))
    kb.button(text="⬅️ Категории", callback_data=MenuCB(action="practice"))
    kb.button(text="🏠 Меню", callback_data=MenuCB(action="home"))
    kb.adjust(1, 2)
    return kb.as_markup()


# ────────────────────────────── Code Practice ─────────────────────────────

def code_categories(is_pro: bool) -> InlineKeyboardMarkup:
    free_topics = {"variables", "lists"}
    kb = InlineKeyboardBuilder()
    for topic, label in CODE_CATEGORIES:
        if topic not in free_topics and not is_pro:
            label += " 🔒"
        kb.button(text=label, callback_data=CodeCB(action="task", topic=topic))
    kb.button(text="🧪 Тренажёр кода", callback_data=MenuCB(action="sandbox"))
    kb.button(text="🛠 Разбор бага", callback_data=MenuCB(action="debug"))
    kb.button(text="🏠 Меню", callback_data=MenuCB(action="home"))
    kb.adjust(2, 2, 1, 1, 1)
    return kb.as_markup()


# ──────────────────────── Code Runner (sandbox) ───────────────────────────

def _coding_topics() -> list[str]:
    """Topics present in the coding-task bank, in first-appearance order."""
    seen: set[str] = set()
    order: list[str] = []
    for task in coding_tasks():
        if task.topic not in seen:
            seen.add(task.topic)
            order.append(task.topic)
    return order


def sandbox_categories() -> InlineKeyboardMarkup:
    """Code Runner home: adaptive pick + browse by topic (scales to 100s of tasks)."""
    kb = InlineKeyboardBuilder()
    kb.button(text="🎯 Адаптивная задача", callback_data=SandboxCB(action="adaptive"))
    tasks = coding_tasks()
    topics = _coding_topics()
    for topic in topics:
        count = sum(1 for t in tasks if t.topic == topic)
        kb.button(text=f"{topic_emoji(topic)} {topic_name(topic)} · {count}",
                  callback_data=SandboxCB(action="cat", topic=topic))
    kb.button(text="⬅️ Код", callback_data=MenuCB(action="code"))
    kb.button(text="🏠 Меню", callback_data=MenuCB(action="home"))
    rows_of_two = (len(topics) + 1) // 2
    kb.adjust(1, *([2] * rows_of_two), 2)
    return kb.as_markup()


def sandbox_topic_tasks(topic: str, is_pro: bool, solved_ids: set[str]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    topic_tasks = [t for t in coding_tasks() if t.topic == topic]
    for task in topic_tasks:
        if task.id in solved_ids:
            mark = "✅"
        elif task.tier == "pro" and not is_pro:
            mark = "🔒"
        else:
            mark = _DIFF_ICON.get(task.difficulty, "⚪")
        kb.button(text=f"{mark} {task.func}()", callback_data=SandboxCB(action="task", task_id=task.id))
    kb.button(text="⬅️ Темы", callback_data=MenuCB(action="sandbox"))
    kb.button(text="🏠 Меню", callback_data=MenuCB(action="home"))
    kb.adjust(*([1] * len(topic_tasks)), 2)
    return kb.as_markup()


def sandbox_task(topic: str = "") -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    back = SandboxCB(action="cat", topic=topic) if topic else MenuCB(action="sandbox")
    kb.button(text="⬅️ К задачам", callback_data=back)
    kb.button(text="🏠 Меню", callback_data=MenuCB(action="home"))
    kb.adjust(2)
    return kb.as_markup()


def sandbox_done(topic: str = "") -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="🎯 Ещё задача", callback_data=SandboxCB(action="adaptive"))
    if topic:
        kb.button(text="🧪 К теме", callback_data=SandboxCB(action="cat", topic=topic))
    kb.button(text="🏠 Меню", callback_data=MenuCB(action="home"))
    kb.adjust(1, 2) if topic else kb.adjust(1, 1)
    return kb.as_markup()


def debug_done() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="🛠 Ещё разбор", callback_data=MenuCB(action="debug"))
    kb.button(text="💻 Код", callback_data=MenuCB(action="code"))
    kb.button(text="🏠 Меню", callback_data=MenuCB(action="home"))
    kb.adjust(2, 1)
    return kb.as_markup()


def code_task(topic: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="🔁 Другая задача", callback_data=CodeCB(action="task", topic=topic))
    kb.button(text="⬅️ Категории", callback_data=MenuCB(action="code"))
    kb.button(text="🏠 Меню", callback_data=MenuCB(action="home"))
    kb.adjust(1, 2)
    return kb.as_markup()


# ────────────────────────────── Backend Projects ──────────────────────────

_PROJECT_DIFF = {"easy": "🟢", "medium": "🟡", "hard": "🔴"}


def projects_menu(statuses, is_pro: bool) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for st in statuses:
        if st.finished:
            mark = "✅"
        elif st.step > 0:
            mark = "▶️"
        else:
            mark = "🆕"
        lock = " 🔒" if st.project.tier == "pro" and not is_pro else ""
        kb.button(
            text=f"{mark} {st.project.emoji} {st.project.title} · {st.done_steps}/{st.total}{lock}",
            callback_data=ProjectCB(action="open", project_id=st.project.id),
        )
    kb.button(text="🏠 Меню", callback_data=MenuCB(action="home"))
    kb.adjust(*([1] * len(statuses)), 1)
    return kb.as_markup()


def project_card(status, is_pro: bool) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    locked = status.project.tier == "pro" and not is_pro
    if status.finished:
        pass  # nothing to start — it's done
    elif locked:
        # Routes through the step handler, which shows the upsell for locked projects.
        kb.button(text="💎 Открыть в PRO", callback_data=ProjectCB(action="step", project_id=status.project.id))
    else:
        label = "▶️ Продолжить" if status.step > 0 else "🚀 Начать проект"
        kb.button(text=f"{label} · шаг {status.step + 1}/{status.total}",
                  callback_data=ProjectCB(action="step", project_id=status.project.id))
    kb.button(text="⬅️ Проекты", callback_data=MenuCB(action="projects"))
    kb.button(text="🏠 Меню", callback_data=MenuCB(action="home"))
    kb.adjust(1, 2)
    return kb.as_markup()


def project_step(project_id: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Готово, дальше", callback_data=ProjectCB(action="done", project_id=project_id))
    kb.button(text="📋 К проекту", callback_data=ProjectCB(action="open", project_id=project_id))
    kb.button(text="🏠 Меню", callback_data=MenuCB(action="home"))
    kb.adjust(1, 2)
    return kb.as_markup()


def project_step_done(status) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    if status.finished:
        kb.button(text="🏆 К проектам", callback_data=MenuCB(action="projects"))
    else:
        kb.button(text="➡️ Следующий шаг", callback_data=ProjectCB(action="step", project_id=status.project.id))
        kb.button(text="📋 К проекту", callback_data=ProjectCB(action="open", project_id=status.project.id))
    kb.button(text="🏠 Меню", callback_data=MenuCB(action="home"))
    kb.adjust(1, 2) if not status.finished else kb.adjust(1, 1)
    return kb.as_markup()


# ──────────────────────────── Daily / Profile ─────────────────────────────

def daily_question(options: tuple[str, ...]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for index, option in enumerate(options):
        kb.button(text=option, callback_data=DailyCB(action="answer", option=index))
    kb.button(text="🏠 Меню", callback_data=MenuCB(action="home"))
    kb.adjust(2, 2, 1)
    return kb.as_markup()


def daily_done() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="💻 Code Practice", callback_data=MenuCB(action="code"))
    kb.button(text="🏠 Меню", callback_data=MenuCB(action="home"))
    kb.adjust(2)
    return kb.as_markup()


def profile() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="▶️ Продолжить чтение", callback_data=MenuCB(action="continue"))
    kb.button(text="🎯 Career Path", callback_data=MenuCB(action="career"))
    kb.button(text="🎓 Сертификат", callback_data=MenuCB(action="certificate"))
    kb.button(text="⭐ Избранное", callback_data=MenuCB(action="favorites"))
    kb.button(text="📚 Курсы", callback_data=MenuCB(action="lessons"))
    kb.button(text="🏠 Меню", callback_data=MenuCB(action="home"))
    kb.adjust(1, 2, 2, 1)
    return kb.as_markup()


def coach() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="▶️ Продолжить обучение", callback_data=MenuCB(action="continue"))
    kb.button(text="👤 Профиль", callback_data=MenuCB(action="profile"))
    kb.button(text="🏠 Меню", callback_data=MenuCB(action="home"))
    kb.adjust(1, 2)
    return kb.as_markup()


def achievements() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="👤 Профиль", callback_data=MenuCB(action="profile"))
    kb.button(text="🏠 Меню", callback_data=MenuCB(action="home"))
    kb.adjust(2)
    return kb.as_markup()


def leaderboard() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="👤 Профиль", callback_data=MenuCB(action="profile"))
    kb.button(text="🏠 Меню", callback_data=MenuCB(action="home"))
    kb.adjust(2)
    return kb.as_markup()


def upsell() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="👤 Профиль", callback_data=MenuCB(action="profile"))
    kb.button(text="🏠 Меню", callback_data=MenuCB(action="home"))
    kb.adjust(2)
    return kb.as_markup()

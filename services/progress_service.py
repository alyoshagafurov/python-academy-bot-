"""Course-aware progress routing.

Beginner keeps using ``users.current_lesson`` (zero migration, fully backward
compatible). Every other course stores its pointer in ``course_progress``.
XP, streak, leaderboard and achievements remain global by design — this layer
only routes *where you are* in each course.
"""
from __future__ import annotations

from datetime import datetime, timezone

from database import models
from database.models import User
from lessons import Course, all_courses, get_course
from services import course_service

BEGINNER = "python_beginner"
STUDENT = "python_student"
HTMLCSS = "web_htmlcss"
WEB_PYTHON = "web_python"
MINECRAFT = "python_minecraft"

# Compact course codes for short callback payloads (ReadCB).
_CODE_TO_ID = {"b": BEGINNER, "s": STUDENT, "h": HTMLCSS, "w": WEB_PYTHON,
               "m": MINECRAFT}
_ID_TO_CODE = {v: k for k, v in _CODE_TO_ID.items()}


def code_to_id(code: str) -> str:
    return _CODE_TO_ID.get(code, BEGINNER)


def id_to_code(course_id: str) -> str:
    return _ID_TO_CODE.get(course_id, "b")


def active_course_id(user: User) -> str:
    return user.active_course or BEGINNER


async def current_lesson(user: User, course_id: str) -> int:
    """Lesson pointer for a given course (1-based)."""
    if course_id == BEGINNER:
        return user.current_lesson  # unchanged source — Beginner untouched
    lesson = await models.get_course_lesson(user.user_id, course_id)
    return lesson if lesson is not None else 1


async def advance(user_id: int, course_id: str, next_lesson: int) -> None:
    """Move the lesson pointer forward for the given course."""
    if course_id == BEGINNER:
        await models.set_current_lesson(user_id, next_lesson)
    else:
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        await models.set_course_lesson(user_id, course_id, next_lesson, now)


async def set_active(user_id: int, course_id: str) -> None:
    await models.set_active_course(user_id, course_id)


async def active_context(user: User) -> tuple[Course, int]:
    """Resolve the user's active course object and their lesson pointer in it."""
    course_id = active_course_id(user)
    course = get_course(course_id)
    cur = await current_lesson(user, course_id)
    return course, cur


async def track_overview(user: User) -> list[tuple[str, int]]:
    """(label, percent) for every course — shared by the profile and selection."""
    out: list[tuple[str, int]] = []
    for course in all_courses().values():
        cur = await current_lesson(user, course.id)
        _, _, pct = course_service.course_progress(cur, course)
        out.append((f"{course.emoji} {course.title}", pct))
    return out

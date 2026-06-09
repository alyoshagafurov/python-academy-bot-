"""Favorites / bookmarks for theory lessons.

A bookmark is a (course, lesson) pair — lesson ids repeat across courses, so the
course is part of the key. Pure persistence wrapper with lesson resolution.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from database import models
from lessons import Lesson, get_lesson


@dataclass(frozen=True)
class Bookmark:
    course_id: str
    lesson: Lesson


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


async def toggle(user_id: int, course_id: str, lesson_id: int) -> bool:
    """Add if absent, remove if present. Returns True when now bookmarked."""
    if await models.is_bookmarked(user_id, course_id, lesson_id):
        await models.remove_bookmark(user_id, course_id, lesson_id)
        return False
    await models.add_bookmark(user_id, course_id, lesson_id, _now())
    return True


async def is_bookmarked(user_id: int, course_id: str, lesson_id: int) -> bool:
    return await models.is_bookmarked(user_id, course_id, lesson_id)


async def list_lessons(user_id: int) -> list[Bookmark]:
    """Saved lessons (newest first), resolved to lesson objects."""
    out: list[Bookmark] = []
    for course_id, lesson_id in await models.list_bookmarks(user_id):
        lesson = get_lesson(lesson_id, course_id)
        if lesson is not None:
            out.append(Bookmark(course_id, lesson))
    return out


async def count(user_id: int) -> int:
    return await models.count_bookmarks(user_id)

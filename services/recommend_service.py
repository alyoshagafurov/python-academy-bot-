"""Smart theory recommendations — what to read next.

Without quizzes there's no accuracy signal, so recommendations are built from
reading progress and saved lessons: continue the current course, explore a
related topic, and revisit something bookmarked. Deterministic + explainable.
"""
from __future__ import annotations

from dataclasses import dataclass

from database import models
from lessons import Lesson, get_course
from services import bookmark_service, progress_service, related_service


@dataclass(frozen=True)
class Recommendation:
    course_id: str
    lesson: Lesson
    reason: str


async def recommend(user_id: int, limit: int = 4) -> list[Recommendation]:
    user = await models.get_user(user_id)
    if user is None:
        return []

    recs: list[Recommendation] = []
    seen: set[tuple[str, int]] = set()

    def _add(course_id: str, lesson: Lesson, reason: str) -> None:
        key = (course_id, lesson.id)
        if lesson is not None and not lesson.placeholder and key not in seen:
            seen.add(key)
            recs.append(Recommendation(course_id, lesson, reason))

    # 1) Continue the active course where the user left off.
    course_id = progress_service.active_course_id(user)
    course = get_course(course_id)
    cur = await progress_service.current_lesson(user, course_id)
    current_lesson_obj = course.get(min(cur, course.total))
    if cur <= course.total and current_lesson_obj is not None:
        _add(course_id, current_lesson_obj, "продолжить курс с того места, где остановился")

    # 2) A topic related to where the user is now.
    if current_lesson_obj is not None:
        for rel in related_service.related(course_id, current_lesson_obj, limit=3):
            _add(rel.course_id, rel.lesson, "близко к тому, что ты сейчас изучаешь")
            break

    # 3) Something saved for later.
    for bm in await bookmark_service.list_lessons(user_id):
        _add(bm.course_id, bm.lesson, "из твоего избранного — вернись и дочитай")
        if len(recs) >= limit:
            break

    return recs[:limit]

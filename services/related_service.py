"""Related-topic suggestions for a lesson.

Deterministic: same topic across courses first (deepest connection), then
neighbours in the same stage. Self is always excluded.
"""
from __future__ import annotations

from dataclasses import dataclass

from lessons import Lesson, all_courses, get_course


@dataclass(frozen=True)
class Related:
    course_id: str
    lesson: Lesson


def related(course_id: str, lesson: Lesson, limit: int = 5) -> list[Related]:
    out: list[Related] = []
    seen: set[tuple[str, int]] = {(course_id, lesson.id)}

    def _add(cid: str, other: Lesson) -> None:
        key = (cid, other.id)
        if key not in seen and not other.placeholder:
            seen.add(key)
            out.append(Related(cid, other))

    # 1) Same topic anywhere — the strongest link (e.g. lists in both tracks).
    for course in all_courses().values():
        for other in course.lessons:
            if other.topic and other.topic == lesson.topic:
                _add(course.id, other)

    # 2) Neighbours in the same stage of the same course.
    stage = get_course(course_id).stage(lesson.stage_id)
    if stage is not None:
        for other in stage.lessons:
            _add(course_id, other)

    return out[:limit]

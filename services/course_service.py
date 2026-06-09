"""Course / stage / lesson progression: unlock rules and progress math.

Progress is the single global pointer `user.current_lesson` (1..N). Stages and
lessons derive their status from it, so nothing else in the app had to change.
"""
from __future__ import annotations

from dataclasses import dataclass

from lessons import get_course
from lessons.schema import Course, Lesson, Stage

# Student-track identity titles, earned per completed block (stage id → badge).
IDENTITY: dict[int, tuple[str, str]] = {
    1: ("🏭", "Production Mindset"),
    2: ("⚡", "Async Wizard"),
    3: ("🗄️", "Data Keeper"),
    4: ("🌐", "API Builder"),
    5: ("🏛️", "Architect"),
    6: ("🧪", "Quality Guardian"),
    7: ("🚀", "Ship It"),
    8: ("🐍", "Internals Master"),
}


@dataclass(frozen=True)
class StageProgress:
    stage: Stage
    status: str    # "done" | "current" | "locked"
    done: int
    total: int
    percent: int
    xp_earned: int

    @property
    def unlocked(self) -> bool:
        return self.status != "locked"

    @property
    def icon(self) -> str:
        return {"done": "✅", "current": "▶️", "locked": "🔒"}[self.status]


def lesson_unlocked(lesson_id: int, current_lesson: int) -> bool:
    return lesson_id <= current_lesson


def lesson_status(lesson_id: int, current_lesson: int) -> str:
    if lesson_id < current_lesson:
        return "done"
    if lesson_id == current_lesson:
        return "current"
    return "locked"


def lesson_icon(lesson_id: int, current_lesson: int) -> str:
    return {"done": "✅", "current": "▶️", "locked": "🔒"}[lesson_status(lesson_id, current_lesson)]


def stage_unlocked(stage: Stage, current_lesson: int) -> bool:
    return current_lesson >= stage.first_id


def stage_progress(stage: Stage, current_lesson: int) -> StageProgress:
    done = sum(1 for lesson in stage.lessons if lesson.id < current_lesson)
    total = stage.total
    percent = int(done / total * 100) if total else 0
    xp_earned = sum(lesson.xp for lesson in stage.lessons if lesson.id < current_lesson)

    if total and current_lesson > stage.last_id:
        status = "done"
    elif stage_unlocked(stage, current_lesson):
        status = "current"
    else:
        status = "locked"
    return StageProgress(stage, status, done, total, percent, xp_earned)


def all_stage_progress(current_lesson: int, course: Course | None = None) -> list[StageProgress]:
    course = course or get_course()
    return [stage_progress(stage, current_lesson) for stage in course.stages]


def course_progress(current_lesson: int, course: Course | None = None) -> tuple[int, int, int]:
    """Return (done, total, percent) for the whole course."""
    course = course or get_course()
    total = course.total
    done = max(0, min(current_lesson - 1, total))
    percent = int(done / total * 100) if total else 0
    return done, total, percent


def course_xp_earned(current_lesson: int, course: Course | None = None) -> int:
    """XP earned so far inside this course (sum of completed lessons' XP)."""
    course = course or get_course()
    return sum(lesson.xp for lesson in course.lessons if lesson.id < current_lesson)


def lesson_number_in_stage(lesson: Lesson, course: Course | None = None) -> int:
    """1-based position of the lesson within its stage."""
    course = course or get_course()
    stage = course.stage(lesson.stage_id)
    if stage is None or lesson not in stage.lessons:
        return 1
    return stage.lessons.index(lesson) + 1


# ───────────────────────── Student identity ───────────────────────────────

def identity_for_stage(stage_id: int) -> tuple[str, str] | None:
    """The (emoji, title) badge earned by completing a given block."""
    return IDENTITY.get(stage_id)


def current_identity(current_lesson: int, course: Course) -> tuple[str, str] | None:
    """Highest identity badge earned so far (last fully completed block)."""
    earned: tuple[str, str] | None = None
    for sp in all_stage_progress(current_lesson, course):
        if sp.status == "done" and sp.stage.id in IDENTITY:
            earned = IDENTITY[sp.stage.id]
    return earned

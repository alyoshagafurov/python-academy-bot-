"""Content access layer (multi-course).

Each course lives in `content/<lang>/<track>/` (course.json + stage_*.json) and
is discovered + cached on first use. The public API is course-aware but every
function **defaults to the Beginner course**, so existing callers keep working.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from lessons import loader
from lessons.schema import (
    CodeTask, CodingTask, Course, Lesson, Project, ProjectStep, Quiz, Snippet, Stage,
)

_CONTENT = Path(__file__).resolve().parent.parent / "content"
DEFAULT_COURSE_DIR = _CONTENT / "python" / "beginner"
DEFAULT_COURSE_ID = "python_beginner"


@lru_cache(maxsize=1)
def all_courses() -> dict[str, Course]:
    courses = loader.load_courses()
    # Robustness: guarantee the default course is always available.
    if DEFAULT_COURSE_ID not in courses:
        beginner = loader.load_course(DEFAULT_COURSE_DIR)
        courses[beginner.id] = beginner
    return courses


@lru_cache(maxsize=1)
def code_tasks() -> tuple[CodeTask, ...]:
    return loader.load_code_tasks(_CONTENT / "code_tasks.json")


@lru_cache(maxsize=1)
def coding_tasks() -> tuple[CodingTask, ...]:
    return loader.load_coding_tasks(_CONTENT / "coding_tasks.json")


@lru_cache(maxsize=1)
def projects() -> tuple[Project, ...]:
    return loader.load_projects(_CONTENT / "projects.json")


@lru_cache(maxsize=1)
def snippets() -> tuple[Snippet, ...]:
    return loader.load_snippets(_CONTENT / "minecraft_snippets.json")


def get_course(course_id: str | None = None) -> Course:
    """Return a course by id (defaults to Beginner)."""
    courses = all_courses()
    return courses.get(course_id or DEFAULT_COURSE_ID) or courses[DEFAULT_COURSE_ID]


def get_lesson(lesson_id: int, course_id: str | None = None) -> Lesson | None:
    return get_course(course_id).get(lesson_id)


def total_lessons(course_id: str | None = None) -> int:
    return get_course(course_id).total


def get_stage(stage_id: int, course_id: str | None = None) -> Stage | None:
    return get_course(course_id).stage(stage_id)


def stage_of(lesson_id: int, course_id: str | None = None) -> Stage | None:
    return get_course(course_id).stage_of(lesson_id)


# Backward-compatible flat tuple of all Beginner lessons (loaded once).
LESSONS: tuple[Lesson, ...] = get_course().lessons

__all__ = [
    "Quiz", "Lesson", "Stage", "Course", "CodeTask", "CodingTask",
    "Project", "ProjectStep", "projects", "Snippet", "snippets",
    "LESSONS", "get_lesson", "total_lessons",
    "get_course", "all_courses", "code_tasks", "coding_tasks",
    "get_stage", "stage_of", "DEFAULT_COURSE_ID",
]

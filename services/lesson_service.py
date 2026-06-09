"""Lesson progression logic: answer checking, XP rewards, challenges.

Course-aware: the lesson pointer is advanced per course via progress_service
(Beginner → users.current_lesson, others → course_progress). XP/streak/
achievements remain global (granted through reward_service).
"""
from __future__ import annotations

from dataclasses import dataclass

from database import models
from lessons import DEFAULT_COURSE_ID, get_lesson
from services import progress_service, reward_service, stats_service
from services.reward_service import ActivityResult

CHALLENGE_XP = 15


@dataclass
class CompleteResult:
    """Outcome of completing a lesson's mini-test."""

    awarded: bool                       # XP granted this time
    xp_gain: int                        # XP added (0 when already completed)
    already_done: bool                  # lesson had been completed before
    activity: ActivityResult | None = None  # streak / level / achievements


def is_unlocked(lesson_id: int, current_lesson: int) -> bool:
    """A lesson is reachable once the user has progressed up to it."""
    return lesson_id <= current_lesson


def check_answer(lesson_id: int, option: int, course_id: str = DEFAULT_COURSE_ID) -> bool:
    lesson = get_lesson(lesson_id, course_id)
    return lesson is not None and lesson.quiz is not None and option == lesson.quiz.correct


def check_challenge(lesson_id: int, option: int, course_id: str = DEFAULT_COURSE_ID) -> bool:
    lesson = get_lesson(lesson_id, course_id)
    return (
        lesson is not None
        and lesson.challenge is not None
        and option == lesson.challenge.correct
    )


async def record_wrong_answer(user_id: int, topic: str) -> None:
    """Log an incorrect attempt for knowledge analysis (no XP, no streak)."""
    await stats_service.record_answer(user_id, topic, correct=False)


async def complete_lesson(
    user_id: int, lesson_id: int, course_id: str = DEFAULT_COURSE_ID
) -> CompleteResult:
    """Mark a lesson's test as passed in the given course.

    XP is granted only the first time the user finishes their *current* lesson
    in that course (no farming). Activity (streak/achievements) always registers.
    """
    user = await models.get_user(user_id)
    lesson = get_lesson(lesson_id, course_id)
    if user is None or lesson is None:
        return CompleteResult(awarded=False, xp_gain=0, already_done=False)

    current = await progress_service.current_lesson(user, course_id)
    if lesson_id == current:
        await progress_service.advance(user_id, course_id, lesson_id + 1)
        activity = await reward_service.grant(
            user_id, xp=lesson.xp, topic=lesson.topic, correct=True
        )
        return CompleteResult(True, lesson.xp, False, activity)

    # Reviewing an already-completed lesson: register activity, grant no XP.
    activity = await reward_service.grant(user_id, xp=0, topic=lesson.topic, correct=True)
    return CompleteResult(False, 0, True, activity)


async def complete_challenge(
    user_id: int, lesson_id: int, course_id: str = DEFAULT_COURSE_ID
) -> ActivityResult:
    """Award the bonus-challenge XP and register the activity."""
    lesson = get_lesson(lesson_id, course_id)
    topic = lesson.topic if lesson else None
    return await reward_service.grant(user_id, xp=CHALLENGE_XP, topic=topic, correct=True)


async def mark_read(
    user_id: int, lesson_id: int, course_id: str = DEFAULT_COURSE_ID
) -> CompleteResult:
    """Theory-mode completion: reading a lesson advances progress and grants XP.

    Unlike `complete_lesson`, there's no quiz — so no answer outcome is recorded.
    XP is granted only the first time the user reads their *current* lesson
    (advancing the pointer), so re-reading never farms XP. Streak still counts.
    """
    user = await models.get_user(user_id)
    lesson = get_lesson(lesson_id, course_id)
    if user is None or lesson is None:
        return CompleteResult(awarded=False, xp_gain=0, already_done=False)

    current = await progress_service.current_lesson(user, course_id)
    if lesson_id == current:
        await progress_service.advance(user_id, course_id, lesson_id + 1)
        activity = await reward_service.grant(user_id, xp=lesson.xp)  # XP only, no quiz stat
        return CompleteResult(True, lesson.xp, False, activity)

    # Re-reading an already-finished lesson: keep the streak alive, grant no XP.
    activity = await reward_service.grant(user_id, xp=0)
    return CompleteResult(False, 0, True, activity)

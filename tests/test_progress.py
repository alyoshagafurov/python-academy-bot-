"""Multi-course progress: Beginner regression + Student separation + global XP."""
from __future__ import annotations

from database import models
from services import lesson_service, progress_service, user_service

BEGINNER = progress_service.BEGINNER
STUDENT = progress_service.STUDENT


async def test_beginner_advances_users_table():
    uid = 100_001
    await user_service.register_user(uid, "beg")
    await user_service.select_mode(uid, "beginner")

    result = await lesson_service.complete_lesson(uid, 1, BEGINNER)
    assert result.awarded

    user = await models.get_user(uid)
    assert user.current_lesson == 2
    # Beginner must NOT write to course_progress (backward compatibility).
    assert await models.get_course_lesson(uid, BEGINNER) is None


async def test_student_progress_is_separate():
    uid = 100_002
    await user_service.register_user(uid, "stu")
    await lesson_service.complete_lesson(uid, 1, BEGINNER)  # move beginner
    beginner_pointer = (await models.get_user(uid)).current_lesson

    await progress_service.set_active(uid, STUDENT)
    await lesson_service.complete_lesson(uid, 1, STUDENT)

    # Student pointer lives in course_progress…
    assert await models.get_course_lesson(uid, STUDENT) == 2
    # …and Beginner pointer is untouched.
    assert (await models.get_user(uid)).current_lesson == beginner_pointer


async def test_xp_is_global_across_courses():
    uid = 100_003
    await user_service.register_user(uid, "xp")
    before = (await models.get_user(uid)).xp
    await lesson_service.complete_lesson(uid, 1, BEGINNER)
    await progress_service.set_active(uid, STUDENT)
    await lesson_service.complete_lesson(uid, 1, STUDENT)
    after = (await models.get_user(uid)).xp
    assert after > before  # one shared wallet


async def test_replaying_lesson_grants_no_xp():
    uid = 100_004
    await user_service.register_user(uid, "replay")
    first = await lesson_service.complete_lesson(uid, 1, BEGINNER)
    assert first.awarded and first.xp_gain > 0
    # lesson 1 is now behind the pointer → replay grants nothing
    replay = await lesson_service.complete_lesson(uid, 1, BEGINNER)
    assert not replay.awarded and replay.xp_gain == 0

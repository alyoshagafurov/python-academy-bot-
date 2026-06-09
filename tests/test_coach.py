"""Smart Coach / Career Path Predictor: deterministic, monotonic, explainable."""
from __future__ import annotations

from services import coach_service, lesson_service, progress_service, user_service
from services.coach_service import _tier
from utils import texts

BEGINNER = progress_service.BEGINNER


def test_tier_thresholds():
    assert _tier(0)[1] == "Осваиваешь основы"
    assert _tier(30)[1] == "Уверенный Python"
    assert _tier(60)[1] == "Почти Junior Backend"
    assert _tier(80)[1] == "Junior Backend — ready"
    assert _tier(95)[1] == "Middle-направление"


async def test_fresh_user_low_readiness():
    uid = 400_001
    await user_service.register_user(uid, "fresh")
    report = await coach_service.report(uid)
    assert report is not None
    assert 0 <= report.readiness <= 100
    assert report.readiness < 25          # nothing done yet
    assert report.beginner_pct == 0 and report.student_pct == 0
    assert texts.coach(report)            # renders without error


async def test_readiness_increases_with_progress():
    uid = 400_002
    await user_service.register_user(uid, "learner")
    before = (await coach_service.report(uid)).readiness
    for lesson_id in range(1, 6):         # complete 5 beginner lessons (correctly)
        await lesson_service.complete_lesson(uid, lesson_id, BEGINNER)
    after = await coach_service.report(uid)
    assert after.readiness > before
    assert after.coverage_pct > 0
    assert after.beginner_pct > 0


async def test_report_is_deterministic():
    uid = 400_003
    await user_service.register_user(uid, "stable")
    await lesson_service.complete_lesson(uid, 1, BEGINNER)
    r1 = await coach_service.report(uid)
    r2 = await coach_service.report(uid)
    assert (r1.readiness, r1.coverage_pct, r1.accuracy_pct) == (r2.readiness, r2.coverage_pct, r2.accuracy_pct)


async def test_unknown_user_returns_none():
    assert await coach_service.report(999_999_999) is None

"""Adaptive engine: confidence EWMA, SM-2 scheduling, difficulty, recommendations."""
from __future__ import annotations

from datetime import date

from database import models
from services import adaptive_service

T0 = date(2026, 1, 1)


async def test_confidence_rises_on_correct():
    uid = 200_001
    await adaptive_service.record_outcome(uid, "lists", True)
    c1 = await adaptive_service.confidence(uid, "lists")
    await adaptive_service.record_outcome(uid, "lists", True)
    c2 = await adaptive_service.confidence(uid, "lists")
    assert 0.5 < c1 < c2


async def test_confidence_drops_on_wrong():
    uid = 200_002
    await adaptive_service.record_outcome(uid, "loops", True)
    await adaptive_service.record_outcome(uid, "loops", False)
    assert await adaptive_service.confidence(uid, "loops") < 0.5


async def test_interval_grows_on_streak():
    uid = 200_003
    await adaptive_service.record_outcome(uid, "dict", True, today=T0)
    assert (await models.get_review(uid, "dict")).interval_days == 1
    await adaptive_service.record_outcome(uid, "dict", True, today=T0)
    assert (await models.get_review(uid, "dict")).interval_days == 3
    await adaptive_service.record_outcome(uid, "dict", True, today=T0)
    assert (await models.get_review(uid, "dict")).interval_days > 3  # interval × ease


async def test_wrong_resets_and_is_due_today():
    uid = 200_004
    await adaptive_service.record_outcome(uid, "set", True, today=T0)
    await adaptive_service.record_outcome(uid, "set", False, today=T0)
    row = await models.get_review(uid, "set")
    assert row.reps == 0 and row.interval_days == 0
    due = await adaptive_service.due_reviews(uid, today=T0)
    assert any(item.topic == "set" for item in due)


def test_recommend_difficulty_tiers():
    assert adaptive_service.recommend_difficulty(0.3) == "easy"
    assert adaptive_service.recommend_difficulty(0.65) == "medium"
    assert adaptive_service.recommend_difficulty(0.9) == "hard"


async def test_recommendation_prefers_due_review():
    uid = 200_005
    await adaptive_service.record_outcome(uid, "typing", False, today=T0)
    rec = await adaptive_service.next_recommendation(uid)
    assert rec.kind == "review" and rec.topic == "typing" and rec.reason


async def test_analytics_counts_mastery():
    uid = 200_006
    for _ in range(5):
        await adaptive_service.record_outcome(uid, "oop", True)
    stats = await adaptive_service.analytics(uid)
    assert stats["tracked"] >= 1 and stats["mastered"] >= 1


async def test_stats_funnel_feeds_scheduler():
    """Answering through stats_service must populate the review schedule."""
    from services import stats_service
    uid = 200_007
    await stats_service.record_answer(uid, "functions", True)
    assert await models.get_review(uid, "functions") is not None

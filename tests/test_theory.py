"""Theory-first mode: bookmarks, search, related, recommendations, reading."""
from __future__ import annotations

from database import models
from lessons import get_course, get_lesson
from services import (
    bookmark_service,
    lesson_service,
    progress_service,
    recommend_service,
    related_service,
    search_service,
    user_service,
)

BEGINNER = progress_service.BEGINNER
STUDENT = progress_service.STUDENT


# ── Bookmarks ────────────────────────────────────────────────────────────────

async def test_bookmark_toggle_and_count():
    uid = 920_001
    await user_service.register_user(uid, "saver")
    assert await bookmark_service.is_bookmarked(uid, BEGINNER, 3) is False

    assert await bookmark_service.toggle(uid, BEGINNER, 3) is True   # added
    assert await bookmark_service.is_bookmarked(uid, BEGINNER, 3) is True
    assert await bookmark_service.count(uid) == 1

    assert await bookmark_service.toggle(uid, BEGINNER, 3) is False  # removed
    assert await bookmark_service.count(uid) == 0


async def test_bookmarks_are_per_course():
    uid = 920_002
    await user_service.register_user(uid, "saver2")
    await bookmark_service.toggle(uid, BEGINNER, 1)
    await bookmark_service.toggle(uid, STUDENT, 1)
    assert await bookmark_service.count(uid) == 2  # same id, different courses


async def test_bookmark_list_resolves_lessons():
    uid = 920_003
    await user_service.register_user(uid, "saver3")
    await bookmark_service.toggle(uid, BEGINNER, 2)
    items = await bookmark_service.list_lessons(uid)
    assert len(items) == 1
    assert items[0].course_id == BEGINNER
    assert items[0].lesson.id == 2


# ── Search ───────────────────────────────────────────────────────────────────

def test_search_finds_relevant_lessons():
    from lessons import all_courses
    hits = search_service.search("переменные")
    assert hits, "expected matches for a common term"
    assert all(h.course_id in all_courses() for h in hits)  # search spans every course
    assert all(not h.lesson.placeholder for h in hits)  # placeholders never surface


def test_search_empty_query_returns_nothing():
    assert search_service.search("") == []
    assert search_service.search("   ") == []


def test_search_ranks_title_matches_first():
    hits = search_service.search("словари")
    assert hits
    # The dedicated "dict" lesson should rank at the top for this query.
    assert "слов" in hits[0].lesson.title.lower() or hits[0].lesson.topic == "dict"


# ── Related ──────────────────────────────────────────────────────────────────

def test_related_excludes_self_and_returns_items():
    lesson = get_lesson(7, BEGINNER)  # a lists lesson
    rel = related_service.related(BEGINNER, lesson)
    assert all(not (r.course_id == BEGINNER and r.lesson.id == lesson.id) for r in rel)
    assert all(not r.lesson.placeholder for r in rel)


# ── Recommendations ───────────────────────────────────────────────────────────

async def test_recommendations_lead_with_continue():
    uid = 920_010
    await user_service.register_user(uid, "rec")
    recs = await recommend_service.recommend(uid)
    assert recs, "fresh user should still get a 'continue' recommendation"
    assert recs[0].course_id == BEGINNER
    assert recs[0].lesson.id == 1  # current lesson for a new user
    # No duplicate lessons recommended.
    keys = [(r.course_id, r.lesson.id) for r in recs]
    assert len(keys) == len(set(keys))


# ── Reading-based progress (theory mode) ──────────────────────────────────────

async def test_mark_read_advances_and_grants_xp_once():
    uid = 920_020
    await user_service.register_user(uid, "readprog")
    before = (await models.get_user(uid)).xp
    lesson = get_course(BEGINNER).get(1)

    first = await lesson_service.mark_read(uid, 1, BEGINNER)
    assert first.awarded and first.xp_gain == lesson.xp
    assert (await models.get_user(uid)).current_lesson == 2
    assert (await models.get_user(uid)).xp == before + lesson.xp

    # Re-reading an already-read lesson grants no XP (no farming).
    replay = await lesson_service.mark_read(uid, 1, BEGINNER)
    assert not replay.awarded and replay.xp_gain == 0


async def test_mark_read_records_no_quiz_stats():
    uid = 920_021
    await user_service.register_user(uid, "nostats")
    await lesson_service.mark_read(uid, 1, BEGINNER)
    # Theory reading must not fabricate answer/accuracy stats.
    assert await models.get_topic_stats(uid) == []

"""Product analytics: retention cohorts, funnel, topic rankings, drop-off.

Uses delta assertions (before/after) so it stays correct on the shared test DB.
"""
from __future__ import annotations

from datetime import date, timedelta

from database import models
from database.db import connection
from services import admin_service, feature_service, stats_service, user_service

_TODAY = date.today()


def _day(offset: int) -> str:
    return (_TODAY + timedelta(days=offset)).isoformat()


async def _seed_user(uid: int, reg_offset: int, active_offsets: list[int], *, pro: bool = False) -> None:
    async with connection() as db:
        await db.execute(
            "INSERT OR REPLACE INTO users (user_id, username, registration_date, current_lesson, is_pro) "
            "VALUES (?, ?, ?, 1, ?)",
            (uid, f"u{uid}", _day(reg_offset), int(pro)),
        )
        for off in active_offsets:
            await db.execute(
                "INSERT OR IGNORE INTO activity_log (user_id, day) VALUES (?, ?)", (uid, _day(off))
            )
        await db.commit()


# ── Pure metric math ────────────────────────────────────────────────────────

def test_analytics_percentages():
    a = admin_service.Analytics(
        d1_num=3, d1_den=10, d7_num=1, d7_den=4,
        total_users=20, pro_users=5, paywall_hits=2, tasks_solved=9, task_solvers=4,
        hardest=[], most_skipped=[], dropoff=[], funnel=[],
    )
    assert a.d1_pct == 30
    assert a.d7_pct == 25
    assert a.conversion_pct == 25


def test_analytics_percentages_handle_zero():
    a = admin_service.Analytics(0, 0, 0, 0, 0, 0, 0, 0, 0, [], [], [], [])
    assert a.d1_pct == 0 and a.d7_pct == 0 and a.conversion_pct == 0


# ── D1 retention cohort ──────────────────────────────────────────────────────

async def test_d1_cohort_counts_returners():
    before = await admin_service.analytics()
    # Registered 2 days ago; one came back on day+1, one never did.
    await _seed_user(910_001, reg_offset=-2, active_offsets=[-1])   # returner (reg+1)
    await _seed_user(910_002, reg_offset=-2, active_offsets=[])     # no return
    after = await admin_service.analytics()

    assert after.d1_den - before.d1_den == 2
    assert after.d1_num - before.d1_num == 1


# ── D7 retention cohort ──────────────────────────────────────────────────────

async def test_d7_cohort_counts_returners():
    before = await admin_service.analytics()
    await _seed_user(910_010, reg_offset=-7, active_offsets=[0])    # active on reg+7 = today
    await _seed_user(910_011, reg_offset=-7, active_offsets=[])     # no return
    after = await admin_service.analytics()

    assert after.d7_den - before.d7_den == 2
    assert after.d7_num - before.d7_num == 1


# ── FREE → PRO funnel ────────────────────────────────────────────────────────

async def test_conversion_funnel_counts_pro():
    before = await admin_service.analytics()
    await _seed_user(910_020, reg_offset=0, active_offsets=[], pro=True)
    after = await admin_service.analytics()
    assert after.pro_users - before.pro_users == 1
    assert after.total_users - before.total_users == 1


async def test_paywall_hits_counts_capped_free_users():
    before = await admin_service.analytics()
    uid = 910_030
    await user_service.register_user(uid, "capped")
    async with connection() as db:
        await db.execute(
            "UPDATE users SET practice_count = ?, practice_date = ? WHERE user_id = ?",
            (feature_service.FREE_PRACTICE_LIMIT, _day(0), uid),
        )
        await db.commit()
    after = await admin_service.analytics()
    assert after.paywall_hits - before.paywall_hits == 1


# ── Topic rankings + drop-off ────────────────────────────────────────────────

async def test_topic_aggregates_sum_across_users():
    topic = "ztest_topic"
    for _ in range(3):
        await stats_service.record_answer(910_040, topic, correct=False)
    for _ in range(2):
        await stats_service.record_answer(910_041, topic, correct=True)
    aggs = {a.topic: a for a in await models.topic_aggregates()}
    assert topic in aggs
    assert aggs[topic].attempts == 5
    assert aggs[topic].correct == 2


async def test_dropoff_is_sorted_desc():
    await _seed_user(910_050, reg_offset=0, active_offsets=[])
    rows = await models.lesson_dropoff(5)
    counts = [c for _, c in rows]
    assert counts == sorted(counts, reverse=True)


async def test_analytics_object_is_well_formed():
    a = await admin_service.analytics()
    assert isinstance(a.hardest, list)
    assert isinstance(a.most_skipped, list) and len(a.most_skipped) <= 5
    assert isinstance(a.dropoff, list)
    assert len(a.funnel) == 4  # started / stage1 / stage2 / finished

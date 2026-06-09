"""Streak-reminder selection, idempotency and scheduling math."""
from __future__ import annotations

from datetime import date, datetime, timedelta

from database import models
from services import reminder_service, scheduler, user_service


async def test_yesterday_streaker_is_a_target():
    uid = 700_001
    await user_service.register_user(uid, "streaker")
    today = date.today()
    yesterday = (today - timedelta(days=1)).isoformat()
    await models.set_streak(uid, streak=3, best_streak=3, last_active_date=yesterday)

    targets = await models.users_to_remind(yesterday, today.isoformat())
    assert uid in targets


async def test_reminder_is_idempotent_within_a_day():
    uid = 700_002
    await user_service.register_user(uid, "streaker2")
    today = date.today()
    yesterday = (today - timedelta(days=1)).isoformat()
    await models.set_streak(uid, streak=2, best_streak=2, last_active_date=yesterday)

    await models.mark_reminded(uid, today.isoformat())
    targets = await models.users_to_remind(yesterday, today.isoformat())
    assert uid not in targets  # already nudged today → not selected again


async def test_active_today_user_not_reminded():
    uid = 700_003
    await user_service.register_user(uid, "active")
    today = date.today()
    yesterday = (today - timedelta(days=1)).isoformat()
    await models.set_streak(uid, streak=5, best_streak=5, last_active_date=today.isoformat())

    targets = await models.users_to_remind(yesterday, today.isoformat())
    assert uid not in targets  # showed up today already — no nudge needed


async def test_no_streak_user_not_reminded():
    uid = 700_004
    await user_service.register_user(uid, "lapsed")
    today = date.today()
    yesterday = (today - timedelta(days=1)).isoformat()
    await models.set_streak(uid, streak=0, best_streak=4, last_active_date=yesterday)

    targets = await models.users_to_remind(yesterday, today.isoformat())
    assert uid not in targets  # nothing to save (streak already 0)


async def test_run_due_reminders_marks_and_counts():
    """End-to-end with a fake bot: at-risk users get marked, send errors swallowed."""
    today = date.today()
    yesterday = (today - timedelta(days=1)).isoformat()

    ok_uid, blocked_uid = 700_010, 700_011
    await user_service.register_user(ok_uid, "ok")
    await user_service.register_user(blocked_uid, "blocked")
    await models.set_streak(ok_uid, 3, 3, yesterday)
    await models.set_streak(blocked_uid, 3, 3, yesterday)

    sent_to: list[int] = []

    class FakeBot:
        async def send_message(self, user_id, text):
            if user_id == blocked_uid:
                raise RuntimeError("bot blocked")
            sent_to.append(user_id)

    sent = await reminder_service.run_due_reminders(FakeBot(), today=today)

    assert ok_uid in sent_to and blocked_uid not in sent_to
    assert sent >= 1
    # Both are marked reminded → neither is re-selected today.
    remaining = await models.users_to_remind(yesterday, today.isoformat())
    assert ok_uid not in remaining and blocked_uid not in remaining


def test_seconds_until_is_within_a_day():
    # 09:00 → next 17:00 is 8h away today.
    now = datetime(2026, 6, 2, 9, 0, 0)
    secs = scheduler._seconds_until(17, now)
    assert secs == 8 * 3600

    # 18:00 → 17:00 already passed, so it rolls to tomorrow (23h).
    now = datetime(2026, 6, 2, 18, 0, 0)
    secs = scheduler._seconds_until(17, now)
    assert secs == 23 * 3600

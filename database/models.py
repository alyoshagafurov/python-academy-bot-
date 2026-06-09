"""Data-access layer (pure persistence, no business rules).

Tables: users, topic_stats, achievements.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone

import aiosqlite

from database.db import connection

logger = logging.getLogger(__name__)


@dataclass
class User:
    user_id: int
    username: str | None
    xp: int
    current_lesson: int
    selected_mode: str | None
    registration_date: str
    streak: int = 0
    best_streak: int = 0
    last_active_date: str | None = None
    last_daily_date: str | None = None
    is_pro: int = 0
    weekly_xp: int = 0
    week_key: str | None = None
    practice_count: int = 0
    practice_date: str | None = None
    active_course: str | None = None
    last_reminded_date: str | None = None
    pro_until: str | None = None      # PRO expiry (ISO date); None + is_pro=1 ⇒ lifetime
    ref_by: int | None = None         # user_id of the referrer (None ⇒ organic signup)


@dataclass(frozen=True)
class TopicStat:
    topic: str
    attempts: int
    correct: int

    @property
    def accuracy(self) -> float:
        return self.correct / self.attempts if self.attempts else 0.0


@dataclass(frozen=True)
class ReviewItem:
    topic: str
    reps: int
    ease: float
    interval_days: int
    due_date: str | None
    confidence: float
    last_seen: str | None


@dataclass(frozen=True)
class LeaderRow:
    user_id: int
    username: str | None
    weekly_xp: int
    streak: int


# ───────────────────────────────── users ──────────────────────────────────

async def get_user(user_id: int) -> User | None:
    async with connection() as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)) as cur:
            row = await cur.fetchone()
    return User(**dict(row)) if row else None


async def create_user(user_id: int, username: str | None) -> User:
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    async with connection() as db:
        await db.execute(
            "INSERT OR IGNORE INTO users (user_id, username, registration_date) "
            "VALUES (?, ?, ?)",
            (user_id, username, now),
        )
        await db.commit()
    logger.info("Зарегистрирован пользователь %s (@%s)", user_id, username)
    user = await get_user(user_id)
    assert user is not None
    return user


async def update_username(user_id: int, username: str | None) -> None:
    async with connection() as db:
        await db.execute(
            "UPDATE users SET username = ? WHERE user_id = ?", (username, user_id)
        )
        await db.commit()


async def set_mode(user_id: int, mode: str) -> None:
    async with connection() as db:
        await db.execute(
            "UPDATE users SET selected_mode = ? WHERE user_id = ?", (mode, user_id)
        )
        await db.commit()


async def add_xp(user_id: int, amount: int) -> None:
    """Add XP without touching lesson progress (practice, daily, code, challenge)."""
    async with connection() as db:
        await db.execute(
            "UPDATE users SET xp = xp + ? WHERE user_id = ?", (amount, user_id)
        )
        await db.commit()


async def add_xp_and_advance(user_id: int, xp_gain: int, next_lesson: int) -> None:
    """Award XP and move the lesson pointer forward (lesson completion)."""
    async with connection() as db:
        await db.execute(
            "UPDATE users SET xp = xp + ?, current_lesson = ? WHERE user_id = ?",
            (xp_gain, next_lesson, user_id),
        )
        await db.commit()


async def set_current_lesson(user_id: int, next_lesson: int) -> None:
    """Move the Beginner lesson pointer (stored on users) without touching XP."""
    async with connection() as db:
        await db.execute(
            "UPDATE users SET current_lesson = ? WHERE user_id = ?", (next_lesson, user_id)
        )
        await db.commit()


async def set_active_course(user_id: int, course_id: str) -> None:
    async with connection() as db:
        await db.execute(
            "UPDATE users SET active_course = ? WHERE user_id = ?", (course_id, user_id)
        )
        await db.commit()


# ─────────────────────────── course_progress ──────────────────────────────

async def get_course_lesson(user_id: int, course_id: str) -> int | None:
    """Current lesson pointer for a course, or None if the user never started it."""
    async with connection() as db:
        async with db.execute(
            "SELECT current_lesson FROM course_progress WHERE user_id = ? AND course_id = ?",
            (user_id, course_id),
        ) as cur:
            row = await cur.fetchone()
    return int(row[0]) if row else None


async def set_course_lesson(user_id: int, course_id: str, next_lesson: int, when: str) -> None:
    """Upsert the lesson pointer for a non-beginner course."""
    async with connection() as db:
        await db.execute(
            "INSERT INTO course_progress (user_id, course_id, current_lesson, last_activity) "
            "VALUES (?, ?, ?, ?) "
            "ON CONFLICT(user_id, course_id) DO UPDATE SET "
            "current_lesson = excluded.current_lesson, last_activity = excluded.last_activity",
            (user_id, course_id, next_lesson, when),
        )
        await db.commit()


async def bump_weekly_xp(user_id: int, amount: int, week_key: str) -> None:
    """Add to the user's weekly XP, resetting the counter on a new week."""
    async with connection() as db:
        await db.execute(
            "UPDATE users SET "
            "weekly_xp = CASE WHEN week_key = ? THEN weekly_xp + ? ELSE ? END, "
            "week_key = ? WHERE user_id = ?",
            (week_key, amount, amount, week_key, user_id),
        )
        await db.commit()


async def set_streak(
    user_id: int, streak: int, best_streak: int, last_active_date: str
) -> None:
    async with connection() as db:
        await db.execute(
            "UPDATE users SET streak = ?, best_streak = ?, last_active_date = ? "
            "WHERE user_id = ?",
            (streak, best_streak, last_active_date, user_id),
        )
        await db.commit()


async def set_last_daily(user_id: int, date_str: str) -> None:
    async with connection() as db:
        await db.execute(
            "UPDATE users SET last_daily_date = ? WHERE user_id = ?", (date_str, user_id)
        )
        await db.commit()


async def set_pro(user_id: int, is_pro: bool) -> None:
    async with connection() as db:
        await db.execute(
            "UPDATE users SET is_pro = ? WHERE user_id = ?", (int(is_pro), user_id)
        )
        await db.commit()


async def bump_practice_count(user_id: int, date_str: str) -> None:
    """Increment today's practice counter (resets on a new day)."""
    async with connection() as db:
        await db.execute(
            "UPDATE users SET "
            "practice_count = CASE WHEN practice_date = ? THEN practice_count + 1 ELSE 1 END, "
            "practice_date = ? WHERE user_id = ?",
            (date_str, date_str, user_id),
        )
        await db.commit()


# ─────────────────────────── streak reminders ─────────────────────────────

async def users_to_remind(yesterday: str, today: str) -> list[int]:
    """Users whose streak breaks tonight unless they return — at most once/day.

    Targets only *engaged* users (active yesterday, streak ≥ 1) and skips anyone
    already nudged today, so the reminder is helpful rather than spammy.
    """
    async with connection() as db:
        async with db.execute(
            "SELECT user_id FROM users WHERE last_active_date = ? AND streak >= 1 "
            "AND (last_reminded_date IS NULL OR last_reminded_date <> ?)",
            (yesterday, today),
        ) as cur:
            rows = await cur.fetchall()
    return [int(row[0]) for row in rows]


async def mark_reminded(user_id: int, today: str) -> None:
    async with connection() as db:
        await db.execute(
            "UPDATE users SET last_reminded_date = ? WHERE user_id = ?", (today, user_id)
        )
        await db.commit()


# ────────────────────────────── topic_stats ───────────────────────────────

async def record_answer(user_id: int, topic: str, correct: bool) -> None:
    async with connection() as db:
        await db.execute(
            "INSERT INTO topic_stats (user_id, topic, attempts, correct) "
            "VALUES (?, ?, 1, ?) "
            "ON CONFLICT(user_id, topic) DO UPDATE SET "
            "attempts = attempts + 1, correct = correct + ?",
            (user_id, topic, int(correct), int(correct)),
        )
        await db.commit()


async def get_topic_stats(user_id: int) -> list[TopicStat]:
    async with connection() as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT topic, attempts, correct FROM topic_stats WHERE user_id = ?",
            (user_id,),
        ) as cur:
            rows = await cur.fetchall()
    return [TopicStat(row["topic"], row["attempts"], row["correct"]) for row in rows]


# ───────────────────────────── review_schedule ────────────────────────────

def _review(row: aiosqlite.Row) -> ReviewItem:
    return ReviewItem(
        topic=row["topic"], reps=row["reps"], ease=row["ease"],
        interval_days=row["interval_days"], due_date=row["due_date"],
        confidence=row["confidence"], last_seen=row["last_seen"],
    )


async def get_review(user_id: int, topic: str) -> ReviewItem | None:
    async with connection() as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM review_schedule WHERE user_id = ? AND topic = ?", (user_id, topic)
        ) as cur:
            row = await cur.fetchone()
    return _review(row) if row else None


async def upsert_review(user_id: int, topic: str, reps: int, ease: float,
                        interval_days: int, due_date: str, confidence: float,
                        last_seen: str) -> None:
    async with connection() as db:
        await db.execute(
            "INSERT INTO review_schedule "
            "(user_id, topic, reps, ease, interval_days, due_date, confidence, last_seen) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?) "
            "ON CONFLICT(user_id, topic) DO UPDATE SET "
            "reps=excluded.reps, ease=excluded.ease, interval_days=excluded.interval_days, "
            "due_date=excluded.due_date, confidence=excluded.confidence, last_seen=excluded.last_seen",
            (user_id, topic, reps, ease, interval_days, due_date, confidence, last_seen),
        )
        await db.commit()


async def get_reviews(user_id: int) -> list[ReviewItem]:
    async with connection() as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM review_schedule WHERE user_id = ?", (user_id,)
        ) as cur:
            rows = await cur.fetchall()
    return [_review(r) for r in rows]


async def get_due_reviews(user_id: int, today: str) -> list[ReviewItem]:
    async with connection() as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM review_schedule WHERE user_id = ? AND due_date IS NOT NULL "
            "AND due_date <= ? ORDER BY confidence ASC, due_date ASC",
            (user_id, today),
        ) as cur:
            rows = await cur.fetchall()
    return [_review(r) for r in rows]


# ────────────────────────────── achievements ──────────────────────────────

async def add_achievement(user_id: int, code: str) -> bool:
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    async with connection() as db:
        cur = await db.execute(
            "INSERT OR IGNORE INTO achievements (user_id, code, unlocked_date) "
            "VALUES (?, ?, ?)",
            (user_id, code, now),
        )
        await db.commit()
        return cur.rowcount > 0


async def get_achievement_codes(user_id: int) -> set[str]:
    async with connection() as db:
        async with db.execute(
            "SELECT code FROM achievements WHERE user_id = ?", (user_id,)
        ) as cur:
            rows = await cur.fetchall()
    return {row[0] for row in rows}


# ───────────────────────────── solved_tasks ───────────────────────────────

async def record_solved(user_id: int, task_id: str, when: str) -> bool:
    """Mark a coding task solved. Returns True only on the *first* solve."""
    async with connection() as db:
        cur = await db.execute(
            "INSERT OR IGNORE INTO solved_tasks (user_id, task_id, solved_date) "
            "VALUES (?, ?, ?)",
            (user_id, task_id, when),
        )
        await db.commit()
        return cur.rowcount > 0


async def get_solved_task_ids(user_id: int) -> set[str]:
    async with connection() as db:
        async with db.execute(
            "SELECT task_id FROM solved_tasks WHERE user_id = ?", (user_id,)
        ) as cur:
            rows = await cur.fetchall()
    return {row[0] for row in rows}


async def count_solved_tasks(user_id: int) -> int:
    async with connection() as db:
        async with db.execute(
            "SELECT COUNT(*) FROM solved_tasks WHERE user_id = ?", (user_id,)
        ) as cur:
            row = await cur.fetchone()
    return int(row[0]) if row else 0


# ───────────────────────────── activity_log ───────────────────────────────

async def log_activity(user_id: int, day: str) -> None:
    """Record that the user was active on `day` (idempotent — one row per day)."""
    async with connection() as db:
        await db.execute(
            "INSERT OR IGNORE INTO activity_log (user_id, day) VALUES (?, ?)",
            (user_id, day),
        )
        await db.commit()


# ─────────────────────────── project_progress ─────────────────────────────

async def get_project_step(user_id: int, project_id: str) -> int:
    """Next step index for a project (0 if the user hasn't started it)."""
    async with connection() as db:
        async with db.execute(
            "SELECT step FROM project_progress WHERE user_id = ? AND project_id = ?",
            (user_id, project_id),
        ) as cur:
            row = await cur.fetchone()
    return int(row[0]) if row else 0


async def set_project_step(user_id: int, project_id: str, step: int, when: str) -> None:
    async with connection() as db:
        await db.execute(
            "INSERT INTO project_progress (user_id, project_id, step, updated) "
            "VALUES (?, ?, ?, ?) "
            "ON CONFLICT(user_id, project_id) DO UPDATE SET "
            "step = excluded.step, updated = excluded.updated",
            (user_id, project_id, step, when),
        )
        await db.commit()


async def get_project_steps(user_id: int) -> dict[str, int]:
    """Map of project_id → next step index for everything the user has touched."""
    async with connection() as db:
        async with db.execute(
            "SELECT project_id, step FROM project_progress WHERE user_id = ?", (user_id,)
        ) as cur:
            rows = await cur.fetchall()
    return {row[0]: int(row[1]) for row in rows}


# ───────────────────────────────── bookmarks ──────────────────────────────

async def add_bookmark(user_id: int, course_id: str, lesson_id: int, when: str) -> bool:
    """Save a lesson. Returns True only if it wasn't already saved."""
    async with connection() as db:
        cur = await db.execute(
            "INSERT OR IGNORE INTO bookmarks (user_id, course_id, lesson_id, created) "
            "VALUES (?, ?, ?, ?)",
            (user_id, course_id, lesson_id, when),
        )
        await db.commit()
        return cur.rowcount > 0


async def remove_bookmark(user_id: int, course_id: str, lesson_id: int) -> None:
    async with connection() as db:
        await db.execute(
            "DELETE FROM bookmarks WHERE user_id = ? AND course_id = ? AND lesson_id = ?",
            (user_id, course_id, lesson_id),
        )
        await db.commit()


async def is_bookmarked(user_id: int, course_id: str, lesson_id: int) -> bool:
    async with connection() as db:
        async with db.execute(
            "SELECT 1 FROM bookmarks WHERE user_id = ? AND course_id = ? AND lesson_id = ?",
            (user_id, course_id, lesson_id),
        ) as cur:
            return await cur.fetchone() is not None


async def list_bookmarks(user_id: int) -> list[tuple[str, int]]:
    """(course_id, lesson_id) pairs, newest first."""
    async with connection() as db:
        async with db.execute(
            "SELECT course_id, lesson_id FROM bookmarks WHERE user_id = ? ORDER BY created DESC",
            (user_id,),
        ) as cur:
            rows = await cur.fetchall()
    return [(row[0], int(row[1])) for row in rows]


async def count_bookmarks(user_id: int) -> int:
    async with connection() as db:
        async with db.execute(
            "SELECT COUNT(*) FROM bookmarks WHERE user_id = ?", (user_id,)
        ) as cur:
            row = await cur.fetchone()
    return int(row[0]) if row else 0


# ─────────────────────────── access / monetization ────────────────────────

async def set_pro_access(user_id: int, is_pro: bool, pro_until: str | None) -> None:
    """Set PRO flag + optional expiry (pro_until=None with is_pro ⇒ lifetime)."""
    async with connection() as db:
        await db.execute(
            "UPDATE users SET is_pro = ?, pro_until = ? WHERE user_id = ?",
            (int(is_pro), pro_until, user_id),
        )
        await db.commit()


async def record_purchase(user_id: int, product: str, stars: int, charge_id: str, when: str) -> None:
    async with connection() as db:
        await db.execute(
            "INSERT INTO purchases (user_id, product, stars, charge_id, created) "
            "VALUES (?, ?, ?, ?, ?)",
            (user_id, product, stars, charge_id, when),
        )
        await db.commit()


# ───────────────────────────────── referrals ──────────────────────────────

async def set_ref_by(user_id: int, referrer_id: int) -> bool:
    """Attribute a referrer — only if not already attributed. Returns True if set."""
    async with connection() as db:
        cur = await db.execute(
            "UPDATE users SET ref_by = ? WHERE user_id = ? AND ref_by IS NULL",
            (referrer_id, user_id),
        )
        await db.commit()
        return cur.rowcount > 0


async def add_referral_reward(referee_id: int, referrer_id: int, when: str) -> bool:
    """Record a one-time referral reward for a friend's purchase. True if new."""
    async with connection() as db:
        cur = await db.execute(
            "INSERT OR IGNORE INTO referral_rewards (referee_id, referrer_id, created) "
            "VALUES (?, ?, ?)",
            (referee_id, referrer_id, when),
        )
        await db.commit()
        return cur.rowcount > 0


async def referral_stats(referrer_id: int) -> tuple[int, int]:
    """(invited, rewarded) — friends attributed vs. friends who converted."""
    async with connection() as db:
        async with db.execute(
            "SELECT COUNT(*) FROM users WHERE ref_by = ?", (referrer_id,)
        ) as cur:
            invited = int((await cur.fetchone())[0])
        async with db.execute(
            "SELECT COUNT(*) FROM referral_rewards WHERE referrer_id = ?", (referrer_id,)
        ) as cur:
            rewarded = int((await cur.fetchone())[0])
    return invited, rewarded


# ──────────────────────────────── certificates ────────────────────────────

async def issue_certificate(user_id: int, course_id: str, code: str, when: str) -> bool:
    """Issue a certificate once per user+course. Returns True if newly issued."""
    async with connection() as db:
        cur = await db.execute(
            "INSERT OR IGNORE INTO certificates (user_id, course_id, code, issued) "
            "VALUES (?, ?, ?, ?)",
            (user_id, course_id, code, when),
        )
        await db.commit()
        return cur.rowcount > 0


async def get_certificate(user_id: int, course_id: str) -> tuple[str, str] | None:
    """(code, issued) for a user's course certificate, or None."""
    async with connection() as db:
        async with db.execute(
            "SELECT code, issued FROM certificates WHERE user_id = ? AND course_id = ?",
            (user_id, course_id),
        ) as cur:
            row = await cur.fetchone()
    return (row[0], row[1]) if row else None


async def list_certificates(user_id: int) -> list[tuple[str, str, str]]:
    """(course_id, code, issued) for all of a user's certificates."""
    async with connection() as db:
        async with db.execute(
            "SELECT course_id, code, issued FROM certificates WHERE user_id = ? ORDER BY issued",
            (user_id,),
        ) as cur:
            rows = await cur.fetchall()
    return [(r[0], r[1], r[2]) for r in rows]


# ────────────────────────────── leaderboard ───────────────────────────────

async def top_weekly(week_key: str, limit: int) -> list[LeaderRow]:
    async with connection() as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT user_id, username, weekly_xp, streak FROM users "
            "WHERE week_key = ? AND weekly_xp > 0 "
            "ORDER BY weekly_xp DESC, streak DESC LIMIT ?",
            (week_key, limit),
        ) as cur:
            rows = await cur.fetchall()
    return [LeaderRow(r["user_id"], r["username"], r["weekly_xp"], r["streak"]) for r in rows]


async def weekly_rank(user_id: int, week_key: str) -> int:
    """1-based rank within the current week (counts everyone ahead of the user)."""
    async with connection() as db:
        async with db.execute(
            "SELECT COUNT(*) + 1 FROM users WHERE week_key = ? AND weekly_xp > "
            "COALESCE((SELECT weekly_xp FROM users WHERE user_id = ? AND week_key = ?), 0)",
            (week_key, user_id, week_key),
        ) as cur:
            row = await cur.fetchone()
    return int(row[0]) if row else 1


# ───────────────────────────────── admin ──────────────────────────────────

async def admin_overview(today: str, week_ago: str) -> dict[str, int]:
    """Aggregate platform stats in a single connection."""
    async with connection() as db:
        async def scalar(query: str, params: tuple = ()) -> int:
            async with db.execute(query, params) as cur:
                row = await cur.fetchone()
            return int(row[0]) if row and row[0] is not None else 0

        return {
            "total_users": await scalar("SELECT COUNT(*) FROM users"),
            "pro_users": await scalar("SELECT COUNT(*) FROM users WHERE is_pro = 1"),
            "active_today": await scalar(
                "SELECT COUNT(*) FROM users WHERE last_active_date = ?", (today,)),
            "active_7d": await scalar(
                "SELECT COUNT(*) FROM users WHERE last_active_date >= ?", (week_ago,)),
            "total_xp": await scalar("SELECT COALESCE(SUM(xp), 0) FROM users"),
            "lessons_completed": await scalar(
                "SELECT COALESCE(SUM(current_lesson - 1), 0) FROM users"),
            "daily_today": await scalar(
                "SELECT COUNT(*) FROM users WHERE last_daily_date = ?", (today,)),
            "attempts": await scalar("SELECT COALESCE(SUM(attempts), 0) FROM topic_stats"),
            "correct": await scalar("SELECT COALESCE(SUM(correct), 0) FROM topic_stats"),
        }


# ───────────────────────────────── analytics ──────────────────────────────

async def admin_analytics(today: str, practice_limit: int) -> dict[str, int]:
    """Retention cohorts + FREE→PRO funnel, all in one connection."""
    async with connection() as db:
        async def scalar(query: str, params: tuple = ()) -> int:
            async with db.execute(query, params) as cur:
                row = await cur.fetchone()
            return int(row[0]) if row and row[0] is not None else 0

        # D1 / D7 cohort retention: of users old enough, how many were active
        # exactly one / seven days after they registered (needs activity_log).
        d1_den = await scalar(
            "SELECT COUNT(*) FROM users WHERE date(registration_date) <= date(?, '-1 day')", (today,))
        d1_num = await scalar(
            "SELECT COUNT(*) FROM users u WHERE date(u.registration_date) <= date(?, '-1 day') "
            "AND EXISTS (SELECT 1 FROM activity_log a WHERE a.user_id = u.user_id "
            "AND a.day = date(u.registration_date, '+1 day'))", (today,))
        d7_den = await scalar(
            "SELECT COUNT(*) FROM users WHERE date(registration_date) <= date(?, '-7 day')", (today,))
        d7_num = await scalar(
            "SELECT COUNT(*) FROM users u WHERE date(u.registration_date) <= date(?, '-7 day') "
            "AND EXISTS (SELECT 1 FROM activity_log a WHERE a.user_id = u.user_id "
            "AND a.day = date(u.registration_date, '+7 day'))", (today,))

        return {
            "d1_num": d1_num, "d1_den": d1_den,
            "d7_num": d7_num, "d7_den": d7_den,
            "total_users": await scalar("SELECT COUNT(*) FROM users"),
            "pro_users": await scalar("SELECT COUNT(*) FROM users WHERE is_pro = 1"),
            # Free users who hit today's practice cap — prime upsell candidates.
            "paywall_hits": await scalar(
                "SELECT COUNT(*) FROM users WHERE is_pro = 0 AND practice_date = ? "
                "AND practice_count >= ?", (today, practice_limit)),
            "tasks_solved": await scalar("SELECT COUNT(*) FROM solved_tasks"),
            "task_solvers": await scalar("SELECT COUNT(DISTINCT user_id) FROM solved_tasks"),
        }


async def topic_aggregates() -> list[TopicStat]:
    """Per-topic totals across ALL users (for hardest / most-skipped rankings)."""
    async with connection() as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT topic, SUM(attempts) AS attempts, SUM(correct) AS correct "
            "FROM topic_stats GROUP BY topic"
        ) as cur:
            rows = await cur.fetchall()
    return [TopicStat(r["topic"], int(r["attempts"]), int(r["correct"])) for r in rows]


async def lesson_dropoff(limit: int) -> list[tuple[int, int]]:
    """Lessons where the most users are currently parked (Beginner pointer)."""
    async with connection() as db:
        async with db.execute(
            "SELECT current_lesson, COUNT(*) AS c FROM users "
            "GROUP BY current_lesson ORDER BY c DESC, current_lesson ASC LIMIT ?",
            (limit,),
        ) as cur:
            rows = await cur.fetchall()
    return [(int(r[0]), int(r[1])) for r in rows]


async def reached_counts(thresholds: list[int]) -> list[tuple[int, int]]:
    """For each threshold L, how many users have current_lesson > L (completion funnel)."""
    async with connection() as db:
        async def scalar(query: str, params: tuple) -> int:
            async with db.execute(query, params) as cur:
                row = await cur.fetchone()
            return int(row[0]) if row and row[0] is not None else 0

        return [
            (L, await scalar("SELECT COUNT(*) FROM users WHERE current_lesson > ?", (L,)))
            for L in thresholds
        ]

"""SQLite connection management and schema initialization (async via aiosqlite).

Schema changes are applied as additive, idempotent migrations so an existing
database (with real user data) is upgraded in place — never recreated.
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

import aiosqlite

from config import config

logger = logging.getLogger(__name__)

# Wait this long for a write lock instead of erroring out with "database is
# locked". With WAL this lets many concurrent users coexist on one SQLite file.
_BUSY_TIMEOUT = 30.0

_CREATE_USERS_TABLE = """
CREATE TABLE IF NOT EXISTS users (
    user_id           INTEGER PRIMARY KEY,
    username          TEXT,
    xp                INTEGER NOT NULL DEFAULT 0,
    current_lesson    INTEGER NOT NULL DEFAULT 1,
    selected_mode     TEXT,
    registration_date TEXT    NOT NULL,
    streak            INTEGER NOT NULL DEFAULT 0,
    best_streak       INTEGER NOT NULL DEFAULT 0,
    last_active_date  TEXT,
    last_daily_date   TEXT,
    is_pro            INTEGER NOT NULL DEFAULT 0,
    weekly_xp         INTEGER NOT NULL DEFAULT 0,
    week_key          TEXT,
    practice_count    INTEGER NOT NULL DEFAULT 0,
    practice_date     TEXT
);
"""

_CREATE_COURSE_PROGRESS_TABLE = """
CREATE TABLE IF NOT EXISTS course_progress (
    user_id        INTEGER NOT NULL,
    course_id      TEXT    NOT NULL,
    current_lesson INTEGER NOT NULL DEFAULT 1,
    last_activity  TEXT,
    PRIMARY KEY (user_id, course_id)
);
"""

_CREATE_REVIEW_SCHEDULE_TABLE = """
CREATE TABLE IF NOT EXISTS review_schedule (
    user_id       INTEGER NOT NULL,
    topic         TEXT    NOT NULL,
    reps          INTEGER NOT NULL DEFAULT 0,
    ease          REAL    NOT NULL DEFAULT 2.5,
    interval_days INTEGER NOT NULL DEFAULT 0,
    due_date      TEXT,
    confidence    REAL    NOT NULL DEFAULT 0.5,
    last_seen     TEXT,
    PRIMARY KEY (user_id, topic)
);
"""

_CREATE_TOPIC_STATS_TABLE = """
CREATE TABLE IF NOT EXISTS topic_stats (
    user_id  INTEGER NOT NULL,
    topic    TEXT    NOT NULL,
    attempts INTEGER NOT NULL DEFAULT 0,
    correct  INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (user_id, topic)
);
"""

_CREATE_ACHIEVEMENTS_TABLE = """
CREATE TABLE IF NOT EXISTS achievements (
    user_id       INTEGER NOT NULL,
    code          TEXT    NOT NULL,
    unlocked_date TEXT    NOT NULL,
    PRIMARY KEY (user_id, code)
);
"""

_CREATE_SOLVED_TASKS_TABLE = """
CREATE TABLE IF NOT EXISTS solved_tasks (
    user_id     INTEGER NOT NULL,
    task_id     TEXT    NOT NULL,
    solved_date TEXT    NOT NULL,
    PRIMARY KEY (user_id, task_id)
);
"""

# One row per (user, active day) — the basis for true D1/D7 retention cohorts.
_CREATE_ACTIVITY_LOG_TABLE = """
CREATE TABLE IF NOT EXISTS activity_log (
    user_id INTEGER NOT NULL,
    day     TEXT    NOT NULL,
    PRIMARY KEY (user_id, day)
);
"""

# Backend-project progress: `step` is the next step index (0-based); when it
# reaches the project's step count, the project is finished.
_CREATE_PROJECT_PROGRESS_TABLE = """
CREATE TABLE IF NOT EXISTS project_progress (
    user_id    INTEGER NOT NULL,
    project_id TEXT    NOT NULL,
    step       INTEGER NOT NULL DEFAULT 0,
    updated    TEXT,
    PRIMARY KEY (user_id, project_id)
);
"""

# Saved theory lessons (per course, since lesson ids repeat across courses).
_CREATE_BOOKMARKS_TABLE = """
CREATE TABLE IF NOT EXISTS bookmarks (
    user_id   INTEGER NOT NULL,
    course_id TEXT    NOT NULL,
    lesson_id INTEGER NOT NULL,
    created   TEXT    NOT NULL,
    PRIMARY KEY (user_id, course_id, lesson_id)
);
"""

# Monetization: a row per successful payment (audit + analytics).
_CREATE_PURCHASES_TABLE = """
CREATE TABLE IF NOT EXISTS purchases (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER NOT NULL,
    product    TEXT    NOT NULL,
    stars      INTEGER NOT NULL DEFAULT 0,
    charge_id  TEXT,
    created    TEXT    NOT NULL
);
"""

# Referral rewards: at most one reward per referred friend (referee).
_CREATE_REFERRAL_REWARDS_TABLE = """
CREATE TABLE IF NOT EXISTS referral_rewards (
    referee_id  INTEGER PRIMARY KEY,
    referrer_id INTEGER NOT NULL,
    created     TEXT    NOT NULL
);
"""

# Issued completion certificates (one per user+course).
_CREATE_CERTIFICATES_TABLE = """
CREATE TABLE IF NOT EXISTS certificates (
    user_id   INTEGER NOT NULL,
    course_id TEXT    NOT NULL,
    code      TEXT    NOT NULL,
    issued    TEXT    NOT NULL,
    PRIMARY KEY (user_id, course_id)
);
"""

# Performance indexes.
_CREATE_INDEXES = (
    "CREATE INDEX IF NOT EXISTS idx_users_week ON users(week_key, weekly_xp)",
    "CREATE INDEX IF NOT EXISTS idx_users_active ON users(last_active_date)",
    "CREATE INDEX IF NOT EXISTS idx_progress_user ON course_progress(user_id)",
    "CREATE INDEX IF NOT EXISTS idx_review_due ON review_schedule(user_id, due_date)",
    "CREATE INDEX IF NOT EXISTS idx_solved_user ON solved_tasks(user_id)",
    "CREATE INDEX IF NOT EXISTS idx_project_user ON project_progress(user_id)",
    "CREATE INDEX IF NOT EXISTS idx_bookmarks_user ON bookmarks(user_id, created)",
    "CREATE INDEX IF NOT EXISTS idx_purchases_user ON purchases(user_id)",
    "CREATE INDEX IF NOT EXISTS idx_referral_referrer ON referral_rewards(referrer_id)",
)

# Columns added to `users` after the initial release: name -> column definition.
_USERS_ADDED_COLUMNS: dict[str, str] = {
    "streak": "INTEGER NOT NULL DEFAULT 0",
    "best_streak": "INTEGER NOT NULL DEFAULT 0",
    "last_active_date": "TEXT",
    "last_daily_date": "TEXT",
    "is_pro": "INTEGER NOT NULL DEFAULT 0",
    "weekly_xp": "INTEGER NOT NULL DEFAULT 0",
    "week_key": "TEXT",
    "practice_count": "INTEGER NOT NULL DEFAULT 0",
    "practice_date": "TEXT",
    "active_course": "TEXT",  # which course the user is currently in (NULL ⇒ beginner)
    "last_reminded_date": "TEXT",  # last day we sent a streak reminder (anti-spam)
    "pro_until": "TEXT",  # PRO access expiry (ISO date); NULL with is_pro=1 ⇒ lifetime
    "ref_by": "INTEGER",  # user_id of the referrer who invited this user (NULL ⇒ organic)
}


@asynccontextmanager
async def connection() -> AsyncIterator[aiosqlite.Connection]:
    """Open a tuned connection: waits on locks (busy_timeout) and uses the
    WAL-friendly ``synchronous=NORMAL`` so concurrent writes stay fast & safe."""
    db = await aiosqlite.connect(config.db_path, timeout=_BUSY_TIMEOUT)
    try:
        await db.execute("PRAGMA synchronous=NORMAL")
        yield db
    finally:
        await db.close()


async def _migrate_users(db: aiosqlite.Connection) -> None:
    """Add any missing columns to an existing `users` table."""
    async with db.execute("PRAGMA table_info(users)") as cursor:
        existing = {row[1] for row in await cursor.fetchall()}

    for column, definition in _USERS_ADDED_COLUMNS.items():
        if column not in existing:
            await db.execute(f"ALTER TABLE users ADD COLUMN {column} {definition}")
            logger.info("Миграция: добавлена колонка users.%s", column)


async def init_db() -> None:
    """Create/upgrade the database schema. Safe to run on every startup."""
    config.db_path.parent.mkdir(parents=True, exist_ok=True)
    async with connection() as db:
        await db.execute("PRAGMA journal_mode=WAL")  # better read/write concurrency
        await db.execute(_CREATE_USERS_TABLE)
        await db.execute(_CREATE_COURSE_PROGRESS_TABLE)
        await db.execute(_CREATE_REVIEW_SCHEDULE_TABLE)
        await db.execute(_CREATE_TOPIC_STATS_TABLE)
        await db.execute(_CREATE_ACHIEVEMENTS_TABLE)
        await db.execute(_CREATE_SOLVED_TASKS_TABLE)
        await db.execute(_CREATE_ACTIVITY_LOG_TABLE)
        await db.execute(_CREATE_PROJECT_PROGRESS_TABLE)
        await db.execute(_CREATE_BOOKMARKS_TABLE)
        await db.execute(_CREATE_PURCHASES_TABLE)
        await db.execute(_CREATE_REFERRAL_REWARDS_TABLE)
        await db.execute(_CREATE_CERTIFICATES_TABLE)
        await _migrate_users(db)
        for index_sql in _CREATE_INDEXES:
            await db.execute(index_sql)
        await db.commit()
    logger.info("База данных готова: %s", config.db_path)

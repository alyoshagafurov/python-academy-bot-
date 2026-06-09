"""Backward-compatible migration: old schema upgrades in place, no data loss."""
from __future__ import annotations

import sqlite3

import aiosqlite

from database.db import _migrate_users

_OLD_SCHEMA = (
    "CREATE TABLE users ("
    " user_id INTEGER PRIMARY KEY, username TEXT, xp INTEGER NOT NULL DEFAULT 0,"
    " current_lesson INTEGER NOT NULL DEFAULT 1, selected_mode TEXT,"
    " registration_date TEXT NOT NULL)"
)


async def test_migration_adds_columns_and_preserves_data(tmp_path):
    db_file = tmp_path / "old.db"
    con = sqlite3.connect(db_file)
    con.execute(_OLD_SCHEMA)
    con.execute(
        "INSERT INTO users (user_id, username, xp, current_lesson, registration_date) "
        "VALUES (7, 'legacy', 99, 3, '2026-01-01')"
    )
    con.commit()
    con.close()

    async with aiosqlite.connect(db_file) as db:
        await _migrate_users(db)
        await db.commit()

        async with db.execute("PRAGMA table_info(users)") as cur:
            columns = {row[1] for row in await cur.fetchall()}
        assert {"streak", "is_pro", "weekly_xp", "active_course"} <= columns

        async with db.execute("SELECT xp, current_lesson FROM users WHERE user_id = 7") as cur:
            row = await cur.fetchone()
        assert row == (99, 3)  # legacy data intact


async def test_migration_is_idempotent(tmp_path):
    db_file = tmp_path / "again.db"
    con = sqlite3.connect(db_file)
    con.execute(_OLD_SCHEMA)
    con.commit()
    con.close()
    async with aiosqlite.connect(db_file) as db:
        await _migrate_users(db)
        await _migrate_users(db)  # second run must not raise
        await db.commit()

"""Weekly leaderboard (ranking by XP earned in the current ISO week)."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from database import models
from database.models import LeaderRow


@dataclass
class Leaderboard:
    week_key: str
    rows: list[LeaderRow]
    my_rank: int
    my_weekly_xp: int


def current_week_key(today: date | None = None) -> str:
    """Stable key for the current ISO week, e.g. '2026-W22'."""
    today = today or date.today()
    year, week, _ = today.isocalendar()
    return f"{year}-W{week:02d}"


async def get(user_id: int, limit: int = 10) -> Leaderboard:
    week = current_week_key()
    rows = await models.top_weekly(week, limit)
    rank = await models.weekly_rank(user_id, week)
    user = await models.get_user(user_id)
    my_xp = user.weekly_xp if user and user.week_key == week else 0
    return Leaderboard(week_key=week, rows=rows, my_rank=rank, my_weekly_xp=my_xp)

"""Daily streak tracking (consecutive days of activity)."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

from database import models


@dataclass(frozen=True)
class StreakResult:
    streak: int
    best_streak: int
    increased: bool   # streak grew today
    reset: bool       # a previous streak was broken


def _today() -> str:
    return date.today().isoformat()


def _yesterday() -> str:
    return (date.today() - timedelta(days=1)).isoformat()


async def touch(user_id: int) -> StreakResult:
    """Register activity for today and update the streak accordingly.

    Idempotent within a day: calling it many times only counts once.
    """
    user = await models.get_user(user_id)
    if user is None:
        return StreakResult(streak=0, best_streak=0, increased=False, reset=False)

    today, yesterday = _today(), _yesterday()
    last = user.last_active_date

    # Record the active day for retention analytics (idempotent per day).
    await models.log_activity(user_id, today)

    if last == today:
        return StreakResult(user.streak, user.best_streak, increased=False, reset=False)

    if last == yesterday:
        streak, increased, reset = user.streak + 1, True, False
    else:
        streak = 1
        increased = True
        reset = bool(last) and user.streak > 1

    best = max(user.best_streak, streak)
    await models.set_streak(user_id, streak, best, today)
    return StreakResult(streak=streak, best_streak=best, increased=increased, reset=reset)

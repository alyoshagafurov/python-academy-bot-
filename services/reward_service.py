"""Single entry point for "the user did something worth rewarding".

Centralizes the side effects of an activity (stats, XP, streak, level-up,
achievements) so handlers stay thin and feedback stays consistent.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from database import models
from services import (
    achievement_service,
    leaderboard_service,
    level_service,
    stats_service,
    streak_service,
)
from services.achievement_service import Achievement
from services.level_service import LevelInfo
from services.streak_service import StreakResult


@dataclass
class ActivityResult:
    xp_gain: int
    leveled_up: bool
    level: LevelInfo
    streak: StreakResult
    new_achievements: list[Achievement] = field(default_factory=list)


async def grant(
    user_id: int,
    *,
    xp: int = 0,
    topic: str | None = None,
    correct: bool | None = None,
    advance_to: int | None = None,
) -> ActivityResult:
    """Apply an activity and report what changed.

    - `topic`/`correct`: record an answer outcome for knowledge analysis.
    - `xp`: XP to award (0 is fine, e.g. a wrong answer or a review).
    - `advance_to`: when set, also move the lesson pointer (lesson completion).
    """
    before = await models.get_user(user_id)
    xp_before = before.xp if before else 0

    if topic and correct is not None:
        await stats_service.record_answer(user_id, topic, correct)

    if advance_to is not None:
        await models.add_xp_and_advance(user_id, xp, advance_to)
    elif xp:
        await models.add_xp(user_id, xp)

    if xp:  # keep the weekly leaderboard in sync
        await models.bump_weekly_xp(user_id, xp, leaderboard_service.current_week_key())

    streak = await streak_service.touch(user_id)
    new_achievements = await achievement_service.evaluate(user_id)

    after = await models.get_user(user_id)
    xp_after = after.xp if after else xp_before

    level_before = level_service.level_info(xp_before)
    level_after = level_service.level_info(xp_after)

    return ActivityResult(
        xp_gain=xp,
        leveled_up=level_after.level > level_before.level,
        level=level_after,
        streak=streak,
        new_achievements=new_achievements,
    )

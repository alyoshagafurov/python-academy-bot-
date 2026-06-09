"""Daily Challenge logic: one rewarded task per day with a streak bonus."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from database import models
from lessons import daily as content
from lessons.schema import Quiz
from services import reward_service
from services.reward_service import ActivityResult


@dataclass
class DailyResult:
    activity: ActivityResult
    base_xp: int
    bonus_xp: int


def get_today() -> Quiz:
    return content.get_today()


def is_done_today(user: models.User) -> bool:
    return user.last_daily_date == date.today().isoformat()


def check(option: int) -> bool:
    return option == content.get_today().correct


async def complete(user_id: int) -> DailyResult | None:
    """Reward today's challenge once. Returns None if already done today."""
    user = await models.get_user(user_id)
    if user is None:
        return None

    today = date.today().isoformat()
    if user.last_daily_date == today:
        return None

    challenge = content.get_today()
    base = content.DAILY_BASE_XP
    bonus = min(user.streak, 7)  # reward consistency

    await models.set_last_daily(user_id, today)
    activity = await reward_service.grant(
        user_id, xp=base + bonus, topic=challenge.topic, correct=True
    )
    return DailyResult(activity=activity, base_xp=base, bonus_xp=bonus)

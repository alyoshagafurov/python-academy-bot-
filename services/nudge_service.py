"""Context-aware motivational nudges.

Turns the generic "come back" reminder into a personal one built from real
signals the app already tracks:

  • a streak about to expire (with the exact day count)
  • a topic the learner has *almost* mastered ("ещё один заход")
  • XP remaining to the next level/rank

`booster_from_signals` is pure (easy to unit-test); `compose` wires it to the DB.
"""
from __future__ import annotations

from database import models
from database.models import User
from services import adaptive_service, level_service
from services.level_service import LevelInfo
from utils.constants import topic_name

# Surface an "almost there" XP nudge when the next level is within this range.
_XP_NUDGE_WINDOW = 60
# A topic counts as "almost mastered" in this confidence band (just below MASTERED).
_NEAR_MASTERY_FLOOR = 0.6

_FALLBACK = (
    "🔥 <b>Не теряй свой streak!</b>\n\n"
    "Вчера ты занимался — вернись сегодня, чтобы серия не оборвалась 💪\n"
    "Жми /menu и продолжай 👇"
)


def streak_line(streak: int) -> str:
    if streak >= 2:
        return f"🔥 <b>Твой {streak}-дневный streak сгорит сегодня!</b>\nЗайди и продли серию — это пара минут."
    return "🔥 <b>Не дай streak оборваться!</b>\nОдин заход сегодня — и серия живёт."


def booster_from_signals(level: LevelInfo, near_topic: str | None) -> str:
    """Pick the single most motivating second line. Pure → unit-testable."""
    if 0 < level.to_next <= _XP_NUDGE_WINDOW:
        return f"⚡ Всего <b>{level.to_next} XP</b> до уровня «{level_service.level_title(level.level + 1)}»."
    if near_topic:
        return f"🧠 Ты почти разобрал <b>{near_topic}</b> — ещё один заход, и тема в кармане."
    return "💡 5 минут чтения теории двигают тебя вперёд каждый день."


async def _near_mastery_topic(user_id: int) -> str | None:
    """Human name of the topic closest to mastery from below, if any."""
    reviews = await models.get_reviews(user_id)
    candidates = [r for r in reviews if _NEAR_MASTERY_FLOOR <= r.confidence < adaptive_service.MASTERED]
    if not candidates:
        return None
    best = max(candidates, key=lambda r: r.confidence)
    return topic_name(best.topic)


async def compose(user_id: int) -> str:
    """Build the personal streak reminder for one user (falls back to generic)."""
    user: User | None = await models.get_user(user_id)
    if user is None:
        return _FALLBACK

    level = level_service.level_info(user.xp)
    near_topic = await _near_mastery_topic(user_id)
    booster = booster_from_signals(level, near_topic)
    return f"{streak_line(user.streak)}\n\n{booster}\n\nЖми /menu 👇"

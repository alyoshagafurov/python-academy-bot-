"""Smart repetition: surface the best topic to review right now.

Priority: a topic *due* by the spaced-repetition scheduler → otherwise the
weakest topic by raw accuracy. Backward-compatible return shape.
"""
from __future__ import annotations

from dataclasses import dataclass

from services import adaptive_service, stats_service
from utils.constants import topic_emoji, topic_name


@dataclass(frozen=True)
class ReviewSuggestion:
    topic: str
    name: str
    emoji: str
    accuracy_pct: int


def _build(topic: str, score: float) -> ReviewSuggestion:
    return ReviewSuggestion(topic, topic_name(topic), topic_emoji(topic), round(score * 100))


async def suggest(user_id: int) -> ReviewSuggestion | None:
    """Best topic to review, or None if nothing is due/weak."""
    # 1) Spaced repetition: anything due (weakest confidence first).
    due = await adaptive_service.due_reviews(user_id)
    if due:
        return _build(due[0].topic, due[0].confidence)

    # 2) Fallback: weakest topic by raw accuracy.
    summary = await stats_service.get_summary(user_id)
    if summary.weak:
        weakest = summary.weak[0]
        return _build(weakest.topic, weakest.accuracy)
    return None

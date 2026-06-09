"""Deterministic adaptive-learning engine — no LLM, fast, explainable.

Three signals, all derived from answer outcomes:
  • confidence  — EWMA of correctness per topic (0..1), recency-aware.
  • spaced repetition — SM-2-lite scheduler (ease/interval/due_date).
  • dynamic difficulty — recommended tier from confidence.

Everything is pure arithmetic over the `review_schedule` table, so it is
reproducible, unit-testable and scales to any number of users.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

from database import models
from database.models import ReviewItem

_EASE_DEFAULT = 2.5
_EASE_MIN = 1.3
_EASE_MAX = 3.0
_EWMA_ALPHA = 0.3          # weight of the newest answer in confidence
_CONFIDENCE_START = 0.5

MASTERED = 0.8             # confidence ≥ → mastered
WEAK = 0.5                 # confidence < → weak


@dataclass(frozen=True)
class Recommendation:
    kind: str               # "review" | "advance"
    topic: str | None
    reason: str             # human, explainable


def recommend_difficulty(confidence: float) -> str:
    """Map confidence → difficulty tier (dynamic difficulty)."""
    if confidence < WEAK:
        return "easy"
    if confidence < MASTERED:
        return "medium"
    return "hard"


def _next_interval(reps: int, ease: float, interval: int) -> int:
    """SM-2-lite interval (days) after a *correct* answer."""
    if reps <= 1:
        return 1
    if reps == 2:
        return 3
    return max(1, round(interval * ease))


async def record_outcome(user_id: int, topic: str, correct: bool, today: date | None = None) -> None:
    """Update the spaced-repetition schedule + confidence for one answer."""
    if not topic:
        return
    today = today or date.today()
    item = await models.get_review(user_id, topic)
    reps = item.reps if item else 0
    ease = item.ease if item else _EASE_DEFAULT
    interval = item.interval_days if item else 0
    confidence = item.confidence if item else _CONFIDENCE_START

    confidence = round(confidence * (1 - _EWMA_ALPHA) + (1.0 if correct else 0.0) * _EWMA_ALPHA, 4)

    if correct:
        reps += 1
        ease = min(_EASE_MAX, ease + 0.1)
        interval = _next_interval(reps, ease, interval)
    else:
        reps = 0
        ease = max(_EASE_MIN, ease - 0.2)
        interval = 0  # resurface immediately (due today)

    due = (today + timedelta(days=interval)).isoformat()
    await models.upsert_review(user_id, topic, reps, ease, interval, due, confidence, today.isoformat())


async def confidence(user_id: int, topic: str) -> float:
    item = await models.get_review(user_id, topic)
    return item.confidence if item else 0.0


async def due_reviews(user_id: int, today: date | None = None) -> list[ReviewItem]:
    """Topics due for review (weakest first)."""
    today = (today or date.today()).isoformat()
    return await models.get_due_reviews(user_id, today)


async def next_recommendation(user_id: int) -> Recommendation:
    """The single best next action, with an explainable reason."""
    due = await due_reviews(user_id)
    if due:
        weakest = due[0]
        return Recommendation(
            kind="review",
            topic=weakest.topic,
            reason=f"повторение закрепит память (интервальное повторение, уверенность {int(weakest.confidence * 100)}%)",
        )
    return Recommendation(kind="advance", topic=None, reason="ты в потоке — продолжай курс")


async def analytics(user_id: int) -> dict[str, int]:
    """Mastery breakdown across tracked topics."""
    rows = await models.get_reviews(user_id)
    return {
        "tracked": len(rows),
        "mastered": sum(1 for r in rows if r.confidence >= MASTERED),
        "learning": sum(1 for r in rows if WEAK <= r.confidence < MASTERED),
        "weak": sum(1 for r in rows if r.confidence < WEAK),
    }

"""Knowledge analysis: turns raw per-topic answers into insight.

Weak / strong topics drive adaptive lessons and smart repetition.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from database import models
from database.models import TopicStat
from services import adaptive_service

# A topic needs at least this many attempts before we judge it.
_MIN_ATTEMPTS = 2
_WEAK_BELOW = 0.60   # accuracy under 60% → weak
_STRONG_FROM = 0.80  # accuracy from 80% → strong


@dataclass
class KnowledgeSummary:
    total_attempts: int = 0
    total_correct: int = 0
    weak: list[TopicStat] = field(default_factory=list)
    strong: list[TopicStat] = field(default_factory=list)
    per_topic: list[TopicStat] = field(default_factory=list)

    @property
    def accuracy(self) -> float:
        return self.total_correct / self.total_attempts if self.total_attempts else 0.0

    @property
    def accuracy_pct(self) -> int:
        return round(self.accuracy * 100)

    @property
    def solved(self) -> int:
        """Number of correctly answered questions."""
        return self.total_correct


async def record_answer(user_id: int, topic: str, correct: bool) -> None:
    """Persist one answer outcome — the single funnel for all answers.

    Feeds both raw stats and the adaptive spaced-repetition engine.
    """
    if topic:
        await models.record_answer(user_id, topic, correct)
        await adaptive_service.record_outcome(user_id, topic, correct)


async def get_summary(user_id: int) -> KnowledgeSummary:
    stats = await models.get_topic_stats(user_id)
    summary = KnowledgeSummary(per_topic=sorted(stats, key=lambda s: s.accuracy))

    for stat in stats:
        summary.total_attempts += stat.attempts
        summary.total_correct += stat.correct
        if stat.attempts >= _MIN_ATTEMPTS and stat.accuracy < _WEAK_BELOW:
            summary.weak.append(stat)
        elif stat.attempts >= _MIN_ATTEMPTS and stat.accuracy >= _STRONG_FROM:
            summary.strong.append(stat)

    summary.weak.sort(key=lambda s: s.accuracy)
    summary.strong.sort(key=lambda s: s.accuracy, reverse=True)
    return summary


async def topic_is_weak(user_id: int, topic: str) -> bool:
    for stat in await models.get_topic_stats(user_id):
        if stat.topic == topic:
            return stat.attempts >= _MIN_ATTEMPTS and stat.accuracy < _WEAK_BELOW
    return False


async def topic_is_strong(user_id: int, topic: str) -> bool:
    for stat in await models.get_topic_stats(user_id):
        if stat.topic == topic:
            return stat.attempts >= _MIN_ATTEMPTS and stat.accuracy >= _STRONG_FROM
    return False

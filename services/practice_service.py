"""Practice Mode logic: serve questions and reward correct answers."""
from __future__ import annotations

import random
from dataclasses import dataclass

from lessons import practice as content
from lessons.schema import Quiz
from services import reward_service
from services.reward_service import ActivityResult
from utils.constants import DIFFICULTY_XP


@dataclass
class PracticeAnswer:
    correct: bool
    xp_gain: int
    question: Quiz | None
    activity: ActivityResult


def categories() -> tuple[tuple[str, str], ...]:
    return content.CATEGORIES


def difficulties() -> tuple[str, ...]:
    return content.DIFFICULTIES


def random_index(topic: str, difficulty: str) -> int:
    size = content.pool_size(topic, difficulty)
    return random.randrange(size) if size else 0


def get_question(topic: str, difficulty: str, index: int) -> Quiz | None:
    return content.get_question(topic, difficulty, index)


async def answer(
    user_id: int, topic: str, difficulty: str, index: int, option: int
) -> PracticeAnswer:
    question = content.get_question(topic, difficulty, index)
    correct = question is not None and option == question.correct
    xp = DIFFICULTY_XP.get(difficulty, 5) if correct else 0
    activity = await reward_service.grant(
        user_id, xp=xp, topic=topic, correct=correct
    )
    return PracticeAnswer(correct=correct, xp_gain=xp, question=question, activity=activity)

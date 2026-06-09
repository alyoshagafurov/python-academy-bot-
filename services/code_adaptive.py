"""Adaptive selection of the next coding task.

Deterministic and explainable — no LLM. It reads the same signals the rest of
the app already tracks (per-topic accuracy + spaced-repetition confidence) and
picks the most useful *unsolved* task for this user:

  • weak in a topic  → reinforce it at the recommended (easier) difficulty
  • strong in a topic → push complexity up (harder task in that topic)
  • no signal yet     → start easy on something unsolved

Respects the free/PRO gate and skips already-solved tasks (falling back to a
replay only when everything accessible is done).
"""
from __future__ import annotations

from dataclasses import dataclass

from database import models
from lessons import coding_tasks
from lessons.schema import CodingTask
from services import adaptive_service, feature_service, stats_service
from utils.constants import topic_name

_DIFF_ORDER = {"easy": 0, "medium": 1, "hard": 2}


@dataclass(frozen=True)
class TaskPick:
    task: CodingTask
    reason: str          # human, explainable ("слабое место" / "повышаем сложность" / …)


async def pick(user_id: int) -> TaskPick | None:
    """Choose the best next coding task for this user, with a reason. None if no tasks."""
    user = await models.get_user(user_id)
    is_pro = feature_service.is_pro(user)

    solved = await models.get_solved_task_ids(user_id)
    accessible = [t for t in coding_tasks() if t.tier == "free" or is_pro]
    if not accessible:
        return None

    unsolved = [t for t in accessible if t.id not in solved]
    pool = unsolved or accessible           # replay only when nothing new is left
    topics_in_pool = {t.topic for t in pool}

    summary = await stats_service.get_summary(user_id)
    target_topic, target_diff, reason = None, "easy", "стартуем с простого"

    # 1) Weakest tracked topic that still has tasks → reinforce.
    for weak in summary.weak:
        if weak.topic in topics_in_pool:
            conf = await adaptive_service.confidence(user_id, weak.topic)
            target_topic = weak.topic
            target_diff = adaptive_service.recommend_difficulty(conf)
            reason = f"подтягиваем слабое место — <b>{topic_name(weak.topic)}</b>"
            break

    # 2) Otherwise a strong topic → raise the bar (gradual complexity).
    if target_topic is None:
        for strong in summary.strong:
            if strong.topic in topics_in_pool:
                target_topic = strong.topic
                target_diff = "hard"
                reason = f"ты силён в «{topic_name(strong.topic)}» — повышаем сложность"
                break

    chosen = min(pool, key=lambda t: _rank(t, target_topic, target_diff))
    if not unsolved:
        reason = "всё пройдено — закрепляем (повтор)"
    return TaskPick(task=chosen, reason=reason)


def _rank(task: CodingTask, target_topic: str | None, target_diff: str) -> tuple:
    """Lower is better: prefer target topic, then target difficulty, then stable order."""
    topic_miss = 0 if (target_topic and task.topic == target_topic) else 1
    diff_miss = abs(_DIFF_ORDER.get(task.difficulty, 0) - _DIFF_ORDER.get(target_diff, 0))
    return (topic_miss, diff_miss, _DIFF_ORDER.get(task.difficulty, 0), task.id)

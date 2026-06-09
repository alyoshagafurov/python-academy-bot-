"""Code Practice logic: serve tasks and reward correct submissions."""
from __future__ import annotations

import random
from dataclasses import dataclass

from lessons import code_tasks
from lessons.schema import CodeTask
from services import reward_service
from services.code_check import CheckResult, check
from services.reward_service import ActivityResult
from utils.constants import CODE_CATEGORIES

# Categories shown in Code Practice (topic key, label).
CATEGORIES = CODE_CATEGORIES


@dataclass
class CodeResult:
    passed: bool
    check: CheckResult
    xp_gain: int
    activity: ActivityResult | None
    task: CodeTask


def tasks_for(topic: str) -> tuple[CodeTask, ...]:
    return tuple(t for t in code_tasks() if t.topic == topic)


def get_task(task_id: str) -> CodeTask | None:
    for task in code_tasks():
        if task.id == task_id:
            return task
    return None


def random_task(topic: str) -> CodeTask | None:
    pool = tasks_for(topic)
    return random.choice(pool) if pool else None


async def submit(user_id: int, task_id: str, source: str) -> CodeResult | None:
    """Validate a submission. Awards XP only when every check passes."""
    task = get_task(task_id)
    if task is None:
        return None

    result = check(source, task.checks)
    if not result.passed:
        return CodeResult(False, result, 0, None, task)

    activity = await reward_service.grant(
        user_id, xp=task.xp, topic=task.topic, correct=True
    )
    return CodeResult(True, result, task.xp, activity, task)

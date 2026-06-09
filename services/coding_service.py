"""Code Runner logic: serve sandboxed tasks, grade submissions, award XP."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from database import models
from lessons import coding_tasks
from lessons.schema import CodingTask
from services import reward_service, sandbox
from services.reward_service import ActivityResult
from services.sandbox import SandboxResult

FIRST_PASS_BONUS = 5

DIFFICULTY_ICON = {"easy": "🟢", "medium": "🟡", "hard": "🔴"}


@dataclass
class CodingOutcome:
    result: SandboxResult
    passed: bool
    xp_gain: int
    first_try: bool
    activity: ActivityResult | None
    task: CodingTask


def all_tasks() -> tuple[CodingTask, ...]:
    return coding_tasks()


def get_task(task_id: str) -> CodingTask | None:
    for task in coding_tasks():
        if task.id == task_id:
            return task
    return None


async def submit(user_id: int, task_id: str, code: str, attempts: int) -> CodingOutcome | None:
    """Run a submission against the task's (visible + hidden) tests."""
    task = get_task(task_id)
    if task is None:
        return None

    result = await sandbox.run(code, task.func, [list(case) for case in task.tests])
    if not result.ok:
        return CodingOutcome(result, False, 0, False, None, task)

    # Record completion (idempotent) — powers adaptive selection & analytics.
    # XP rules are unchanged: every pass still rewards, as before.
    await models.record_solved(user_id, task.id, date.today().isoformat())

    first_try = attempts == 0
    xp = task.xp + (FIRST_PASS_BONUS if first_try else 0)
    activity = await reward_service.grant(user_id, xp=xp, topic=task.topic, correct=True)
    return CodingOutcome(result, True, xp, first_try, activity, task)

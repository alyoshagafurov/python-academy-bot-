"""Solved-task tracking + adaptive coding-task selection."""
from __future__ import annotations

from datetime import date

from database import models
from services import code_adaptive, coding_service, stats_service, user_service


# ── solved_tasks tracking ──────────────────────────────────────────────────

async def test_record_solved_is_idempotent():
    uid = 810_001
    await user_service.register_user(uid, "solver")
    today = date.today().isoformat()

    assert await models.record_solved(uid, "sum_two", today) is True   # first solve
    assert await models.record_solved(uid, "sum_two", today) is False  # already solved
    assert "sum_two" in await models.get_solved_task_ids(uid)
    assert await models.count_solved_tasks(uid) == 1


async def test_submit_records_solved():
    uid = 810_002
    await user_service.register_user(uid, "solver2")
    solution = coding_service.get_task("sum_two").solution
    out = await coding_service.submit(uid, "sum_two", solution, attempts=0)
    assert out.passed
    assert "sum_two" in await models.get_solved_task_ids(uid)


async def test_failed_submit_does_not_record_solved():
    uid = 810_003
    await user_service.register_user(uid, "solver3")
    out = await coding_service.submit(uid, "sum_two", "def sum_two(a, b):\n    return a - b", attempts=0)
    assert not out.passed
    assert "sum_two" not in await models.get_solved_task_ids(uid)


# ── adaptive selection ──────────────────────────────────────────────────────

async def _pro(uid: int, name: str):
    await user_service.register_user(uid, name)
    await models.set_pro(uid, True)


async def test_fresh_user_gets_an_easy_task():
    uid = 820_001
    await _pro(uid, "fresh")
    pick = await code_adaptive.pick(uid)
    assert pick is not None
    assert pick.task.difficulty == "easy"


async def test_weak_topic_is_reinforced():
    uid = 820_002
    await _pro(uid, "weaklists")
    # Tank accuracy in 'lists' → it becomes the weakest topic.
    for _ in range(4):
        await stats_service.record_answer(uid, "lists", correct=False)
    pick = await code_adaptive.pick(uid)
    assert pick is not None
    assert pick.task.topic == "lists"
    assert pick.task.difficulty in {"easy", "medium"}  # reinforce, not punish


async def test_strong_topic_pushes_difficulty_up():
    uid = 820_003
    await _pro(uid, "strongstrings")
    # Master 'strings' (no weak topic anywhere) → push complexity up.
    for _ in range(5):
        await stats_service.record_answer(uid, "strings", correct=True)
    pick = await code_adaptive.pick(uid)
    assert pick is not None
    assert pick.task.topic == "strings"
    assert pick.task.difficulty == "hard"


async def test_free_user_only_gets_free_tasks_and_skips_solved():
    uid = 820_004
    await user_service.register_user(uid, "freeuser")  # not PRO
    today = date.today().isoformat()
    # Solve every free task but one, then the pick must be that remaining one.
    free_ids = [t.id for t in coding_service.all_tasks() if t.tier == "free"]
    keep = free_ids[-1]
    for tid in free_ids[:-1]:
        await models.record_solved(uid, tid, today)

    pick = await code_adaptive.pick(uid)
    assert pick is not None
    assert pick.task.tier == "free"
    assert pick.task.id == keep

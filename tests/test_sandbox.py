"""Sandbox safety + correctness, coding tasks, feedback, XP."""
from __future__ import annotations

from database import models
from lessons import coding_tasks
from services import coding_service, sandbox, user_service
from services.sandbox import SandboxResult, feedback

PASS = [[[2, 3], 5], [[1, 1], 2]]


# ── Safety ──────────────────────────────────────────────────────────────

async def test_blocks_import():
    r = await sandbox.run("import os\ndef f():\n    return 1", "f", [[[], 1]])
    assert r.status == "blocked"


async def test_blocks_eval_and_open():
    for src in ("def f():\n    return eval('1')", "def f():\n    return open('/etc/passwd')"):
        r = await sandbox.run(src, "f", [[[], 1]])
        assert r.status == "blocked", src


async def test_blocks_dunder_escape():
    r = await sandbox.run("def f():\n    return ().__class__.__bases__", "f", [[[], 1]])
    assert r.status == "blocked"


async def test_timeout_on_infinite_loop():
    r = await sandbox.run("def f():\n    while True:\n        pass", "f", [[[], 1]], timeout=2.0)
    assert r.status == "timeout"


# ── Correctness ─────────────────────────────────────────────────────────

async def test_correct_solution_passes():
    r = await sandbox.run("def f(a, b):\n    return a + b", "f", PASS)
    assert r.ok and r.status == "passed"


async def test_wrong_solution_reports_case():
    r = await sandbox.run("def f(a, b):\n    return a - b", "f", [[[2, 3], 5]])
    assert r.status == "failed" and r.expected == 5 and r.got == -1


async def test_missing_return_is_none():
    r = await sandbox.run("def f(a, b):\n    a + b", "f", [[[2, 3], 5]])
    assert r.status == "failed" and r.got is None


async def test_no_function_and_runtime_and_syntax():
    assert (await sandbox.run("x = 1", "f", [[[], 1]])).status == "no_function"
    rt = await sandbox.run("def f():\n    return 1 / 0", "f", [[[], 1]])
    assert rt.status == "runtime_error" and rt.error_type == "ZeroDivisionError"
    assert (await sandbox.run("def f(:\n    pass", "f", [[[], 1]])).status == "syntax"


def test_feedback_nonempty_for_all_statuses():
    for status in ("passed", "failed", "runtime_error", "syntax", "blocked", "timeout", "no_function"):
        msg = feedback(SandboxResult(status, message="x", error_type="ValueError", func="f"))
        assert isinstance(msg, str) and msg


# ── Content: every task ships a reference solution that passes its tests ───
# Solutions live *in the task definition* (the `solution` field), so the bank
# scales to hundreds of tasks without a parallel reference table to drift.

def test_all_tasks_are_well_formed():
    seen_ids = set()
    for task in coding_tasks():
        assert task.id not in seen_ids, f"duplicate task id: {task.id}"
        seen_ids.add(task.id)
        assert task.func and task.tests and task.signature, task.id
        assert task.solution, f"{task.id} is missing a reference solution"


async def test_every_task_solution_passes_hidden_tests():
    for task in coding_tasks():
        result = await sandbox.run(task.solution, task.func, [list(c) for c in task.tests])
        assert result.status == "passed", (task.id, result.status, result.expected, result.got)


# ── Service: XP on pass, none on fail ─────────────────────────────────────

async def test_submit_awards_xp_first_try():
    uid = 300_001
    await user_service.register_user(uid, "coder")
    before = (await models.get_user(uid)).xp
    out = await coding_service.submit(uid, "sum_two", coding_service.get_task("sum_two").solution, attempts=0)
    assert out.passed and out.first_try and out.xp_gain > 0
    assert (await models.get_user(uid)).xp == before + out.xp_gain


async def test_submit_fail_no_xp():
    uid = 300_002
    await user_service.register_user(uid, "coder2")
    before = (await models.get_user(uid)).xp
    out = await coding_service.submit(uid, "sum_two", "def sum_two(a, b):\n    return a - b", attempts=0)
    assert not out.passed and out.xp_gain == 0
    assert (await models.get_user(uid)).xp == before

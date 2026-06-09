"""Backend Projects: content integrity + progress/XP tracking."""
from __future__ import annotations

from database import models
from lessons import projects
from services import project_service, user_service

TELEGRAM_LIMIT = 4096


# ── Content integrity ────────────────────────────────────────────────────────

def test_projects_load_and_are_well_formed():
    ps = projects()
    assert len(ps) >= 5
    ids = [p.id for p in ps]
    assert len(ids) == len(set(ids)), "duplicate project ids"
    for p in ps:
        assert p.title and p.summary and p.outcome and p.stack
        assert p.total_steps >= 4
        assert p.total_xp > 0
        for step in p.steps:
            assert step.title and step.goal and step.detail and step.deliverable
            assert step.xp > 0


def test_first_project_is_free_taster():
    assert project_service.get_project("todo_api").tier == "free"


def test_project_cards_fit_telegram():
    from utils import texts

    for p in projects():
        status = project_service.ProjectStatus(p, step=0, finished=False)
        assert len(texts.project_card(status)) < TELEGRAM_LIMIT, p.id
        for i in range(p.total_steps):
            assert len(texts.project_step(p, i)) < TELEGRAM_LIMIT, (p.id, i)


# ── Progress + XP ────────────────────────────────────────────────────────────

async def test_fresh_status_is_zero():
    uid = 840_001
    await user_service.register_user(uid, "builder")
    status = await project_service.status(uid, project_service.get_project("todo_api"))
    assert status.step == 0 and not status.finished
    assert status.done_steps == 0 and status.percent == 0


async def test_advance_grants_step_xp_and_moves_pointer():
    uid = 840_002
    await user_service.register_user(uid, "builder2")
    project = project_service.get_project("todo_api")
    before = (await models.get_user(uid)).xp

    r1 = await project_service.advance(uid, "todo_api")
    assert r1.completed_index == 0 and r1.new_step == 1 and not r1.finished
    assert r1.xp_gain == project.steps[0].xp
    after1 = (await models.get_user(uid)).xp
    assert after1 == before + project.steps[0].xp

    r2 = await project_service.advance(uid, "todo_api")
    assert r2.completed_index == 1 and r2.new_step == 2
    after2 = (await models.get_user(uid)).xp
    assert after2 == after1 + project.steps[1].xp  # different step, no farming


async def test_finishing_project_awards_full_xp_then_no_more():
    uid = 840_003
    await user_service.register_user(uid, "finisher")
    project = project_service.get_project("todo_api")
    before = (await models.get_user(uid)).xp

    result = None
    for _ in range(project.total_steps):
        result = await project_service.advance(uid, "todo_api")
    assert result.finished
    assert (await models.get_user(uid)).xp == before + project.total_xp

    # Already finished → no step, no extra XP.
    again = await project_service.advance(uid, "todo_api")
    assert again.completed is None and again.xp_gain == 0
    assert (await models.get_user(uid)).xp == before + project.total_xp


async def test_overview_covers_all_projects():
    uid = 840_004
    await user_service.register_user(uid, "browser")
    overview = await project_service.overview(uid)
    assert {s.project.id for s in overview} == {p.id for p in projects()}
    assert all(s.step == 0 and not s.finished for s in overview)

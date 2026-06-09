"""Backend projects: guided, multi-step portfolio builds.

Projects are *milestone content* — the bot walks the learner through real
engineering steps (Todo API, JWT auth, deployment …). A step can't be auto-run
(it's a whole service), so completion is self-attested: tapping "Готово"
advances the pointer and awards that step's XP exactly once.

Progress lives in `project_progress` (one row per user+project). XP rules for
existing features are untouched — these are a brand-new, additive XP source.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from database import models
from lessons import Project, ProjectStep, projects
from services import reward_service
from services.reward_service import ActivityResult


@dataclass(frozen=True)
class ProjectStatus:
    project: Project
    step: int                 # next step index (0-based)
    finished: bool

    @property
    def done_steps(self) -> int:
        return min(self.step, self.project.total_steps)

    @property
    def total(self) -> int:
        return self.project.total_steps

    @property
    def percent(self) -> int:
        return int(self.done_steps / self.total * 100) if self.total else 0


@dataclass(frozen=True)
class AdvanceResult:
    project: Project
    completed: ProjectStep | None   # the step just finished (None if already done)
    completed_index: int
    new_step: int
    finished: bool
    xp_gain: int
    activity: ActivityResult | None


def all_projects() -> tuple[Project, ...]:
    return projects()


def get_project(project_id: str) -> Project | None:
    for project in projects():
        if project.id == project_id:
            return project
    return None


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


async def status(user_id: int, project: Project) -> ProjectStatus:
    step = await models.get_project_step(user_id, project.id)
    return ProjectStatus(project, step, finished=step >= project.total_steps)


async def overview(user_id: int) -> list[ProjectStatus]:
    """Status of every project for the projects menu."""
    steps = await models.get_project_steps(user_id)
    out: list[ProjectStatus] = []
    for project in projects():
        step = steps.get(project.id, 0)
        out.append(ProjectStatus(project, step, finished=step >= project.total_steps))
    return out


async def current_step(user_id: int, project: Project) -> ProjectStep | None:
    """The step the user should work on now, or None if the project is finished."""
    step = await models.get_project_step(user_id, project.id)
    if step >= project.total_steps:
        return None
    return project.steps[step]


async def advance(user_id: int, project_id: str) -> AdvanceResult | None:
    """Mark the current step done: award its XP once and move the pointer forward."""
    project = get_project(project_id)
    if project is None:
        return None

    cur = await models.get_project_step(user_id, project_id)
    if cur >= project.total_steps:  # already finished — nothing to award
        return AdvanceResult(project, None, cur, cur, True, 0, None)

    step = project.steps[cur]
    new_step = cur + 1
    await models.set_project_step(user_id, project_id, new_step, _now())
    activity = await reward_service.grant(user_id, xp=step.xp)  # new XP source, no topic
    return AdvanceResult(
        project=project, completed=step, completed_index=cur, new_step=new_step,
        finished=new_step >= project.total_steps, xp_gain=step.xp, activity=activity,
    )

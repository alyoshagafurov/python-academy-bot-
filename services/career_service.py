"""Career Path — the outcome promise + measurable progress to a goal.

Theory-mode readiness toward "Junior Python Backend", blended from real signals:
reading coverage across courses (60%), portfolio projects (30%) and consistency
(10%). Deterministic and explainable — the transformation a buyer is paying for.
"""
from __future__ import annotations

from dataclasses import dataclass

from database import models
from lessons import get_course
from services import course_service, progress_service, project_service

# Curated learning order toward a backend role.
_ROADMAP = ("python_beginner", "web_htmlcss", "web_python", "python_student")

_W_COVERAGE = 0.60
_W_PROJECTS = 0.30
_W_CONSISTENCY = 0.10

# readiness threshold → (emoji, label)
_TIERS = (
    (90, "🏆", "Middle-направление"),
    (75, "🚀", "Junior Backend — ready"),
    (50, "⚙️", "Почти Junior Backend"),
    (25, "📘", "Уверенная база"),
    (0, "🌱", "Осваиваешь основы"),
)


@dataclass(frozen=True)
class Milestone:
    label: str
    percent: int
    done: bool


@dataclass(frozen=True)
class CareerReport:
    readiness: int
    tier_emoji: str
    tier_label: str
    coverage_pct: int
    projects_done: int
    projects_total: int
    streak_days: int
    milestones: list[Milestone]
    next_step: str


def _tier(readiness: int) -> tuple[str, str]:
    for threshold, emoji, label in _TIERS:
        if readiness >= threshold:
            return emoji, label
    return "🌱", "Осваиваешь основы"


async def report(user_id: int) -> CareerReport | None:
    user = await models.get_user(user_id)
    if user is None:
        return None

    total_lessons = read_lessons = 0
    milestones: list[Milestone] = []
    for course_id in _ROADMAP:
        course = get_course(course_id)
        cur = await progress_service.current_lesson(user, course_id)
        done, total, pct = course_service.course_progress(cur, course)
        total_lessons += total
        read_lessons += min(max(cur - 1, 0), total)
        milestones.append(Milestone(f"{course.emoji} {course.title}", pct, done >= total and total > 0))

    coverage = read_lessons / total_lessons if total_lessons else 0.0

    statuses = await project_service.overview(user_id)
    projects_done = sum(1 for s in statuses if s.finished)
    projects_total = len(statuses)
    projects_cov = projects_done / projects_total if projects_total else 0.0
    milestones.append(Milestone(
        "🛠 Проекты в портфолио",
        int(projects_cov * 100),
        projects_total > 0 and projects_done >= projects_total,
    ))

    consistency = min(user.best_streak / 14.0, 1.0)
    readiness = round(100 * (_W_COVERAGE * coverage + _W_PROJECTS * projects_cov + _W_CONSISTENCY * consistency))
    readiness = max(0, min(100, readiness))
    emoji, label = _tier(readiness)

    nxt = next((m for m in milestones if not m.done), None)
    next_step = f"🎯 Следующий шаг: <b>{nxt.label}</b>" if nxt else "🎯 Всё пройдено — собирай резюме и откликайся!"

    return CareerReport(
        readiness=readiness, tier_emoji=emoji, tier_label=label,
        coverage_pct=round(coverage * 100),
        projects_done=projects_done, projects_total=projects_total,
        streak_days=user.best_streak, milestones=milestones, next_step=next_step,
    )

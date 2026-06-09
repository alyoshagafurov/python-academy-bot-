"""Smart Coach + Career Path Predictor.

Deterministic, explainable estimate of how close a learner is to a Junior
Backend mindset, plus strengths/weaknesses and a single next-focus call.
No LLM: a transparent weighted blend of real signals the app already tracks.
"""
from __future__ import annotations

from dataclasses import dataclass

from database import models
from lessons import get_course
from services import adaptive_service, course_service, progress_service, stats_service
from utils.constants import topic_name

# Readiness weights (sum = 1.0). Coverage dominates; quality & habit refine it.
_W_COVERAGE = 0.50   # how much of the curriculum is done
_W_ACCURACY = 0.25   # answer quality
_W_MASTERY = 0.15    # topics confidently mastered (spaced repetition)
_W_CONSISTENCY = 0.10  # streak habit

_ACCURACY_PRIOR = 10  # shrink accuracy toward 0.5 until ~10 answers exist

# readiness threshold → (emoji, label)
_TIERS = (
    (90, "🏆", "Middle-направление"),
    (75, "🚀", "Junior Backend — ready"),
    (50, "⚙️", "Почти Junior Backend"),
    (25, "📘", "Уверенный Python"),
    (0, "🌱", "Осваиваешь основы"),
)


@dataclass
class CoachReport:
    readiness: int                       # 0..100 toward Junior Backend
    tier_emoji: str
    tier_label: str
    coverage_pct: int
    accuracy_pct: int
    mastery_pct: int
    streak_days: int
    strengths: list[str]
    weaknesses: list[str]
    focus: str
    identity: tuple[str, str] | None     # student rank (emoji, title)
    beginner_pct: int
    student_pct: int


def _tier(readiness: int) -> tuple[str, str]:
    for threshold, emoji, label in _TIERS:
        if readiness >= threshold:
            return emoji, label
    return "🌱", "Осваиваешь основы"


async def report(user_id: int) -> CoachReport | None:
    user = await models.get_user(user_id)
    if user is None:
        return None

    beginner = get_course(progress_service.BEGINNER)
    student = get_course(progress_service.STUDENT)
    b_cur = user.current_lesson
    s_cur = await progress_service.current_lesson(user, progress_service.STUDENT)

    _, _, b_pct = course_service.course_progress(b_cur, beginner)
    _, _, s_pct = course_service.course_progress(s_cur, student)

    b_done, s_done = max(0, b_cur - 1), max(0, s_cur - 1)
    total = beginner.total + student.total
    coverage = (b_done + s_done) / total if total else 0.0

    summary = await stats_service.get_summary(user_id)
    n = summary.total_attempts
    accuracy = (summary.accuracy * n + 0.5 * _ACCURACY_PRIOR) / (n + _ACCURACY_PRIOR)

    analytics = await adaptive_service.analytics(user_id)
    mastery = (analytics["mastered"] / analytics["tracked"]) if analytics["tracked"] else 0.0
    consistency = min(user.best_streak / 7.0, 1.0)

    readiness = round(100 * (
        _W_COVERAGE * coverage
        + _W_ACCURACY * accuracy
        + _W_MASTERY * mastery
        + _W_CONSISTENCY * consistency
    ))
    readiness = max(0, min(100, readiness))
    emoji, label = _tier(readiness)

    strengths = [topic_name(s.topic) for s in summary.strong[:3]]
    weaknesses = [topic_name(w.topic) for w in summary.weak[:3]]
    focus = _focus(summary, student, s_cur, s_done, beginner, b_done)
    identity = course_service.current_identity(s_cur, student)

    return CoachReport(
        readiness=readiness, tier_emoji=emoji, tier_label=label,
        coverage_pct=round(coverage * 100), accuracy_pct=summary.accuracy_pct,
        mastery_pct=round(mastery * 100), streak_days=user.best_streak,
        strengths=strengths, weaknesses=weaknesses, focus=focus,
        identity=identity, beginner_pct=b_pct, student_pct=s_pct,
    )


def _focus(summary, student, s_cur, s_done, beginner, b_done) -> str:
    if summary.weak:
        return f"🎯 Подтяни <b>{topic_name(summary.weak[0].topic)}</b> — слабое место тянет вниз."
    if s_done < student.total:
        stage = student.stage_of(s_cur)
        if stage is not None:
            return f"🎯 Продолжай Student: «<b>{stage.title}</b>» — это твой путь в backend."
        return "🎯 Продолжай Student-трек."
    if b_done < beginner.total:
        return "🎯 Заверши Beginner — фундамент важнее всего."
    return "🎯 Оба трека пройдены — закрепляй 🧪 Тренажёром кода и практикой."

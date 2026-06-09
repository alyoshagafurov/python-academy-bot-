"""Achievement definitions and unlocking logic."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from database import models
from database.models import User
from lessons import get_course
from services import level_service, stats_service
from services.stats_service import KnowledgeSummary

# Last global lesson id of each early stage (drives stage-completion badges).
_stage1 = get_course().stage(1)
_stage2 = get_course().stage(2)
_STAGE1_END = _stage1.last_id if _stage1 else 6
_STAGE2_END = _stage2.last_id if _stage2 else 16
# Total lessons in the Beginner course (drives the "course finished" badge).
_BEGINNER_TOTAL = get_course().total


@dataclass(frozen=True)
class Achievement:
    code: str
    emoji: str
    title: str
    description: str
    condition: Callable[[User, KnowledgeSummary], bool]


# Order matters only for display.
ACHIEVEMENTS: tuple[Achievement, ...] = (
    Achievement("first_lesson", "🐍", "Первый шаг",
                "Пройти первый урок",
                lambda u, s: u.current_lesson > 1),
    Achievement("correct_10", "🧠", "Снайпер",
                "10 правильных ответов",
                lambda u, s: s.total_correct >= 10),
    Achievement("xp_100", "⚡", "Сотка",
                "Набрать 100 XP",
                lambda u, s: u.xp >= 100),
    Achievement("streak_7", "🔥", "Неделя огня",
                "7 дней подряд",
                lambda u, s: u.best_streak >= 7),
    Achievement("daily_first", "📅", "Дейли-старт",
                "Выполнить Daily Challenge",
                lambda u, s: bool(u.last_daily_date)),
    Achievement("sharp_shooter", "🎯", "Меткость",
                "80%+ точности на 10+ ответах",
                lambda u, s: s.total_attempts >= 10 and s.accuracy >= 0.8),
    Achievement("level_3", "🚀", "Explorer",
                "Достичь 3 уровня",
                lambda u, s: level_service.level_info(u.xp).level >= 3),
    Achievement("stage1_done", "🏗️", "Фундамент заложен",
                "Завершить Этап 1",
                lambda u, s: u.current_lesson > _STAGE1_END),
    Achievement("stage2_done", "📦", "Контейнеры освоены",
                "Завершить Этап 2",
                lambda u, s: u.current_lesson > _STAGE2_END),
    # ── Late-game goals (keep players coming back) ──
    Achievement("correct_50", "🎯", "Полста",
                "50 правильных ответов",
                lambda u, s: s.total_correct >= 50),
    Achievement("correct_100", "💯", "Сотня ответов",
                "100 правильных ответов",
                lambda u, s: s.total_correct >= 100),
    Achievement("marksman", "🏹", "Снайпер PRO",
                "90%+ точности на 30+ ответах",
                lambda u, s: s.total_attempts >= 30 and s.accuracy >= 0.9),
    Achievement("xp_500", "🌟", "Полтысячи",
                "Набрать 500 XP",
                lambda u, s: u.xp >= 500),
    Achievement("xp_1000", "👑", "Тысячник",
                "Набрать 1000 XP",
                lambda u, s: u.xp >= 1000),
    Achievement("level_5", "🚀", "Pythonista",
                "Достичь 5 уровня",
                lambda u, s: level_service.level_info(u.xp).level >= 5),
    Achievement("level_10", "🥷", "Code Ninja",
                "Достичь 10 уровня",
                lambda u, s: level_service.level_info(u.xp).level >= 10),
    Achievement("streak_30", "🌋", "Несокрушимый",
                "30 дней подряд",
                lambda u, s: u.best_streak >= 30),
    Achievement("beginner_done", "🎓", "Beginner завершён",
                "Пройти весь курс Beginner",
                lambda u, s: u.current_lesson > _BEGINNER_TOTAL),
)

_BY_CODE = {a.code: a for a in ACHIEVEMENTS}


def get(code: str) -> Achievement | None:
    return _BY_CODE.get(code)


async def evaluate(user_id: int) -> list[Achievement]:
    """Unlock any newly-earned achievements; return the freshly unlocked ones."""
    user = await models.get_user(user_id)
    if user is None:
        return []

    summary = await stats_service.get_summary(user_id)
    already = await models.get_achievement_codes(user_id)

    unlocked: list[Achievement] = []
    for ach in ACHIEVEMENTS:
        if ach.code in already:
            continue
        if ach.condition(user, summary) and await models.add_achievement(user_id, ach.code):
            unlocked.append(ach)
    return unlocked


async def get_status(user_id: int) -> list[tuple[Achievement, bool]]:
    """Return every achievement paired with whether the user has unlocked it."""
    owned = await models.get_achievement_codes(user_id)
    return [(ach, ach.code in owned) for ach in ACHIEVEMENTS]

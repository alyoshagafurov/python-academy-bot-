"""Admin analytics: platform stats, product insights and PRO management."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

from config import config
from database import models
from lessons import get_course
from lessons.practice import CATEGORIES as PRACTICE_CATEGORIES
from services import feature_service
from utils.constants import CODE_CATEGORIES, topic_name

# A topic needs this many aggregate answers before it's ranked as "hardest".
_MIN_ATTEMPTS_FOR_RANK = 5
_RANK_LIMIT = 5


@dataclass
class Overview:
    total_users: int
    active_today: int
    active_7d: int
    pro_users: int
    total_xp: int
    lessons_completed: int
    daily_today: int
    attempts: int
    correct: int

    @property
    def accuracy_pct(self) -> int:
        return round(self.correct / self.attempts * 100) if self.attempts else 0

    @property
    def retention_pct(self) -> int:
        """Share of all users active in the last 7 days."""
        return round(self.active_7d / self.total_users * 100) if self.total_users else 0


@dataclass
class Analytics:
    d1_num: int
    d1_den: int
    d7_num: int
    d7_den: int
    total_users: int
    pro_users: int
    paywall_hits: int
    tasks_solved: int
    task_solvers: int
    hardest: list[tuple[str, int, int]]   # (topic name, accuracy %, attempts)
    most_skipped: list[tuple[str, int]]   # (topic name, attempts)
    dropoff: list[tuple[str, int]]        # (lesson label, users parked)
    funnel: list[tuple[str, int]]         # (milestone label, users reached)

    @staticmethod
    def _pct(num: int, den: int) -> int:
        return round(num / den * 100) if den else 0

    @property
    def d1_pct(self) -> int:
        return self._pct(self.d1_num, self.d1_den)

    @property
    def d7_pct(self) -> int:
        return self._pct(self.d7_num, self.d7_den)

    @property
    def conversion_pct(self) -> int:
        return self._pct(self.pro_users, self.total_users)


def is_admin(user_id: int) -> bool:
    return user_id in config.admin_ids


async def overview() -> Overview:
    today = date.today().isoformat()
    week_ago = (date.today() - timedelta(days=7)).isoformat()
    data = await models.admin_overview(today, week_ago)
    return Overview(**data)


async def analytics() -> Analytics:
    today = date.today().isoformat()
    core = await models.admin_analytics(today, feature_service.FREE_PRACTICE_LIMIT)

    aggregates = await models.topic_aggregates()
    by_topic = {a.topic: a for a in aggregates}

    # Hardest topics: lowest accuracy among sufficiently-answered topics.
    ranked = [a for a in aggregates if a.attempts >= _MIN_ATTEMPTS_FOR_RANK]
    ranked.sort(key=lambda a: a.accuracy)
    hardest = [(topic_name(a.topic), round(a.accuracy * 100), a.attempts) for a in ranked[:_RANK_LIMIT]]

    # Most skipped: of the topics we actively offer, which get practiced least.
    offered = {t for t, _ in PRACTICE_CATEGORIES} | {t for t, _ in CODE_CATEGORIES}
    skipped = sorted(offered, key=lambda t: by_topic[t].attempts if t in by_topic else 0)
    most_skipped = [(topic_name(t), by_topic[t].attempts if t in by_topic else 0)
                    for t in skipped[:_RANK_LIMIT]]

    # Drop-off: lessons where users are currently parked.
    course = get_course()
    dropoff: list[tuple[str, int]] = []
    for lesson_id, count in await models.lesson_dropoff(_RANK_LIMIT):
        if lesson_id > course.total:
            label = "🎓 завершили курс"
        else:
            lesson = course.get(lesson_id)
            label = f"Урок {lesson_id}: {lesson.title}" if lesson else f"Урок {lesson_id}"
        dropoff.append((label, count))

    # Completion funnel by milestones.
    s1 = course.stage(1).last_id if course.stage(1) else 6
    s2 = course.stage(2).last_id if course.stage(2) else 16
    rows = await models.reached_counts([1, s1, s2, course.total])
    labels = {1: "Начали (>1)", s1: f"Прошли этап 1 (>{s1})",
              s2: f"Прошли этап 2 (>{s2})", course.total: "Завершили курс"}
    funnel = [(labels.get(L, f">{L}"), n) for L, n in rows]

    return Analytics(
        d1_num=core["d1_num"], d1_den=core["d1_den"],
        d7_num=core["d7_num"], d7_den=core["d7_den"],
        total_users=core["total_users"], pro_users=core["pro_users"],
        paywall_hits=core["paywall_hits"], tasks_solved=core["tasks_solved"],
        task_solvers=core["task_solvers"],
        hardest=hardest, most_skipped=most_skipped, dropoff=dropoff, funnel=funnel,
    )


async def grant_pro(user_id: int) -> bool:
    """Grant PRO. Returns False if the user doesn't exist."""
    if await models.get_user(user_id) is None:
        return False
    await models.set_pro(user_id, True)
    return True


async def revoke_pro(user_id: int) -> bool:
    if await models.get_user(user_id) is None:
        return False
    await models.set_pro(user_id, False)
    return True

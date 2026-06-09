"""Startup diagnostics — a clear, scannable boot report.

Surfaces content, config and integrity at launch so misconfiguration is
obvious immediately (production-safe: warns, never crashes the bot).
"""
from __future__ import annotations

import logging

from config import config
from lessons import all_courses

logger = logging.getLogger(__name__)


def run_diagnostics() -> None:
    """Log a startup banner with content + config sanity checks."""
    logger.info("──────── Python Academy · startup ────────")
    logger.info("📂 БД: %s", config.db_path)

    courses = all_courses()
    if not courses:
        logger.error("⚠️  Контент не найден — проверь content/*/*/course.json")
    for course in courses.values():
        full = sum(1 for lesson in course.lessons if not lesson.placeholder)
        logger.info(
            "📚 %s %s — %d уроков (%d готовых, %d placeholder)",
            course.emoji, course.title, course.total, full, course.total - full,
        )

    logger.info("🛠  Админов: %d · PRO-конфиг: %d", len(config.admin_ids), len(config.pro_ids))
    if not config.admin_ids:
        logger.warning("⚠️  ADMIN_IDS пуст — команды /admin недоступны")

    _validate_content(courses)
    logger.info("──────────────────────────────────────────")


def _validate_content(courses: dict) -> None:
    """Cheap integrity checks on quizzes — logs problems, never raises."""
    problems = 0
    for course in courses.values():
        for lesson in course.lessons:
            if lesson.placeholder:
                continue
            for quiz in (lesson.practice, lesson.quiz, lesson.challenge):
                if quiz is None:
                    continue
                if not (0 <= quiz.correct < len(quiz.options)):
                    problems += 1
                    logger.error("Битый вопрос в уроке «%s» (%s)", lesson.title, course.id)
    if problems:
        logger.error("⚠️  Найдено битых вопросов: %d", problems)
    else:
        logger.info("✅ Контент проверен — вопросы валидны")

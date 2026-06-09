"""Content-engine integrity: both courses load and lessons are well-formed."""
from __future__ import annotations

from lessons import all_courses, get_course
from utils import texts

TELEGRAM_LIMIT = 4096


def test_both_courses_discovered():
    courses = all_courses()
    assert "python_beginner" in courses
    assert "python_student" in courses


def test_beginner_fully_authored():
    beginner = get_course("python_beginner")
    assert beginner.total == 51
    assert all(not lesson.placeholder for lesson in beginner.lessons)


def test_student_block1_full_rest_placeholder():
    student = get_course("python_student")
    assert len(student.stages) == 8
    block1 = student.stage(1)
    assert block1.total == 7
    assert all(not lesson.placeholder for lesson in block1.lessons)


def test_quiz_integrity_across_all_courses():
    for course in all_courses().values():
        for lesson in course.lessons:
            if lesson.placeholder:
                continue
            for quiz in (lesson.practice, lesson.quiz, lesson.challenge):
                if quiz is None:
                    continue
                assert 0 <= quiz.correct < len(quiz.options), lesson.title
                assert len(quiz.options) >= 2
                assert quiz.explanation


def test_lesson_cards_fit_telegram():
    for course in all_courses().values():
        for lesson in course.lessons:
            if lesson.placeholder:
                continue
            rendered = texts.lesson_card(lesson, course=course)
            assert len(rendered) < TELEGRAM_LIMIT, f"{course.id}:{lesson.title}"

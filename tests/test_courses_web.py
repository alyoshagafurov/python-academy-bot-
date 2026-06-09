"""New web courses: discovery, sizing, Telegram-HTML safety, search reach."""
from __future__ import annotations

import re

from lessons import all_courses, get_course
from services import progress_service, search_service
from utils import texts

WEB_HTMLCSS = "web_htmlcss"
WEB_PYTHON = "web_python"

# Prose fields are rendered RAW (Telegram HTML). Only these tags are allowed;
# any other "<" must be written as an entity (&lt;). The `example` field is
# escaped by texts._code_block, so it's exempt.
_ALLOWED = r"</?(?:b|strong|i|em|u|s|code|pre|a|br)\b"
_RAW_TAG = re.compile(r"<(?!" + _ALLOWED[1:] + r")")  # a "<" not starting an allowed tag
_PROSE_FIELDS = ("theory", "association", "real_example", "code_explained")


def test_all_four_courses_discovered():
    courses = all_courses()
    assert set(courses) >= {"python_beginner", "python_student", WEB_HTMLCSS, WEB_PYTHON}


def test_web_courses_fully_authored():
    for cid in (WEB_HTMLCSS, WEB_PYTHON):
        course = get_course(cid)
        assert len(course.stages) == 5
        assert course.total == 25
        assert all(not lesson.placeholder for lesson in course.lessons)
        assert course.description  # shown on the selection screen


def test_web_courses_have_codes_for_readcb():
    # ReadCB round-trips course codes — new courses must map both ways.
    for cid in (WEB_HTMLCSS, WEB_PYTHON):
        code = progress_service.id_to_code(cid)
        assert progress_service.code_to_id(code) == cid


def test_web_lessons_are_fully_populated():
    for cid in (WEB_HTMLCSS, WEB_PYTHON):
        for lesson in get_course(cid).lessons:
            assert lesson.title and lesson.theory and lesson.association
            assert lesson.example and lesson.code_explained
            assert lesson.common_mistakes
            assert lesson.xp > 0


def test_web_prose_has_no_raw_html_tags():
    """Literal HTML in prose must be escaped (&lt;), or Telegram rejects the message."""
    offenders = []
    for cid in (WEB_HTMLCSS, WEB_PYTHON):
        for lesson in get_course(cid).lessons:
            fields = {f: getattr(lesson, f) for f in _PROSE_FIELDS}
            fields["common_mistakes"] = " ".join(lesson.common_mistakes)
            for fname, value in fields.items():
                if _RAW_TAG.search(value):
                    offenders.append(f"{cid}:{lesson.title}:{fname}")
    assert not offenders, f"raw/unescaped tags in prose: {offenders}"


def test_web_cards_fit_telegram():
    for cid in (WEB_HTMLCSS, WEB_PYTHON):
        course = get_course(cid)
        for lesson in course.lessons:
            assert len(texts.lesson_card(lesson, course=course)) < 4096


def test_search_reaches_web_courses():
    # HTML/CSS terms surface the new courses.
    css_hits = search_service.search("flexbox")
    assert any(h.course_id == WEB_HTMLCSS for h in css_hits)

    flask_hits = search_service.search("flask")
    assert any(h.course_id == WEB_PYTHON for h in flask_hits)

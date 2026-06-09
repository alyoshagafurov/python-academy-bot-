"""Fast theory search across all courses.

Deterministic keyword ranking over lesson title / topic / body — no index, no
LLM. Good enough for a few hundred lessons and instant to compute.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from lessons import Lesson, all_courses
from utils.constants import topic_name

_TAG_RE = re.compile(r"<[^>]+>")
_WORD_RE = re.compile(r"\w+", re.UNICODE)


@dataclass(frozen=True)
class SearchHit:
    course_id: str
    lesson: Lesson
    score: int


def _strip(text: str) -> str:
    return _TAG_RE.sub(" ", text or "")


def _score(lesson: Lesson, query: str, tokens: list[str]) -> int:
    title = lesson.title.lower()
    topic = f"{lesson.topic} {topic_name(lesson.topic)}".lower()
    body = _strip(" ".join((lesson.theory, lesson.association, lesson.real_example,
                            lesson.code_explained))).lower()
    score = 0
    for token in tokens:
        if token in title:
            score += 3
        if token in topic:
            score += 2
        if token in body:
            score += 1
    if query in title:        # whole-phrase title match is the strongest signal
        score += 5
    return score


def search(query: str, limit: int = 8) -> list[SearchHit]:
    """Rank non-placeholder lessons across both courses for a free-text query."""
    query = (query or "").strip().lower()
    if not query:
        return []
    tokens = _WORD_RE.findall(query)
    if not tokens:
        return []

    hits: list[SearchHit] = []
    for course in all_courses().values():
        for lesson in course.lessons:
            if lesson.placeholder:
                continue
            score = _score(lesson, query, tokens)
            if score:
                hits.append(SearchHit(course.id, lesson, score))

    hits.sort(key=lambda h: (-h.score, h.course_id, h.lesson.id))
    return hits[:limit]

"""Completion certificates — a shareable, verifiable proof of finishing a course.

A course is "completed" when every (non-placeholder) lesson has been read
(reading advances progress, so current_lesson > total). The certificate code is
deterministic per user+course, so it can be re-derived and verified without a
lookup. Issuance is recorded once in the `certificates` table.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import date

from database import models
from database.models import User
from lessons import get_course
from services import progress_service

# Short course codes for human-readable certificate ids.
_CCODE = {
    "python_beginner": "PB",
    "python_student": "PS",
    "web_htmlcss": "HC",
    "web_python": "PW",
}
_SALT = "python-academy"


@dataclass(frozen=True)
class Certificate:
    course_id: str
    course_title: str
    code: str
    issued: str
    holder: str


def code_for(user_id: int, course_id: str) -> str:
    digest = hashlib.sha256(f"{user_id}:{course_id}:{_SALT}".encode()).hexdigest()[:6].upper()
    return f"PA-{_CCODE.get(course_id, 'XX')}-{user_id}-{digest}"


def verify(code: str, user_id: int, course_id: str) -> bool:
    return code == code_for(user_id, course_id)


async def is_completed(user: User, course_id: str) -> bool:
    course = get_course(course_id)
    cur = await progress_service.current_lesson(user, course_id)
    return course.total > 0 and cur > course.total


def _holder(user: User) -> str:
    return user.username or f"user{user.user_id}"


async def existing(user_id: int, course_id: str) -> Certificate | None:
    row = await models.get_certificate(user_id, course_id)
    if not row:
        return None
    code, issued = row
    user = await models.get_user(user_id)
    return Certificate(course_id, get_course(course_id).title, code, issued, _holder(user) if user else str(user_id))


async def issue(user_id: int, course_id: str) -> tuple[Certificate | None, bool]:
    """Issue a certificate if the course is completed. Returns (cert, newly_issued).

    Caller decides any access gating; this only checks completion + records it.
    """
    user = await models.get_user(user_id)
    if user is None or not await is_completed(user, course_id):
        return await existing(user_id, course_id), False
    newly = await models.issue_certificate(user_id, course_id, code_for(user_id, course_id), date.today().isoformat())
    return await existing(user_id, course_id), newly


async def list_for(user_id: int) -> list[Certificate]:
    user = await models.get_user(user_id)
    holder = _holder(user) if user else str(user_id)
    out: list[Certificate] = []
    for course_id, code, issued in await models.list_certificates(user_id):
        out.append(Certificate(course_id, get_course(course_id).title, code, issued, holder))
    return out

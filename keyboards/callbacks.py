"""Typed callback-data factories (aiogram 3.x).

Structured payloads keep button routing validated and refactor-safe.
All payloads stay well under Telegram's 64-byte limit.
"""
from __future__ import annotations

from aiogram.filters.callback_data import CallbackData


class MenuCB(CallbackData, prefix="menu"):
    """Top-level navigation."""

    action: str  # continue | lessons | search | recommend | favorites | profile | about | home
    #             legacy (dormant): learn | practice | code | projects | daily | leaders
    #                               | achievements | coach | sandbox | debug | pro


class ModeCB(CallbackData, prefix="mode"):
    """Learning-mode selection."""

    mode: str  # kid | beginner | student


class CourseCB(CallbackData, prefix="crs"):
    """Open a course (stages overview)."""

    course_id: str = "python_beginner"


class StageCB(CallbackData, prefix="stg"):
    """Open a stage (its lessons)."""

    stage_id: int = 0


class LessonCB(CallbackData, prefix="lsn"):
    """Theory-lesson navigation (read / simpler / related / bookmark).

    Legacy quiz actions (practice/pans/quiz/answer/challenge/chans) remain valid
    payloads for dormant modules but are no longer surfaced in the UI.
    """

    action: str          # open | read | simple | related | bookmark  (+ legacy)
    lesson_id: int = 0
    option: int = -1     # selected answer index (legacy quiz flow)


class PracticeCB(CallbackData, prefix="prc"):
    """Practice Mode navigation and answers."""

    action: str           # diff | q | answer
    topic: str = ""
    difficulty: str = ""  # easy | medium | hard
    index: int = 0        # which question in the pool
    option: int = -1      # selected answer index


class DailyCB(CallbackData, prefix="dly"):
    """Daily Challenge answers."""

    action: str       # answer
    option: int = -1


class CodeCB(CallbackData, prefix="code"):
    """Code Practice navigation (the current task lives in FSM state)."""

    action: str       # cats | task
    topic: str = ""


class SandboxCB(CallbackData, prefix="sbx"):
    """Code Runner (sandbox) navigation."""

    action: str       # cat | task | adaptive
    task_id: str = ""
    topic: str = ""


class ProjectCB(CallbackData, prefix="prj"):
    """Backend-projects navigation (dormant in theory-first mode)."""

    action: str          # open | step | done
    project_id: str = ""


class ReadCB(CallbackData, prefix="rd"):
    """Open any lesson in a given course — used by search, related, favorites, recs."""

    course: str = "b"    # short course code: b = Beginner, s = Student
    lesson_id: int = 0


class SnippetCB(CallbackData, prefix="snip"):
    """Ready-to-copy Minecraft code library navigation."""

    action: str       # home | cat | view
    category: str = ""
    snippet_id: str = ""


class BuyCB(CallbackData, prefix="buy"):
    """Start a purchase for a pricing product (Telegram Stars checkout)."""

    product: str = ""    # pricing.Product id


class CertCB(CallbackData, prefix="cert"):
    """Certificate actions (issue / view) for a course."""

    course: str = "b"    # short course code

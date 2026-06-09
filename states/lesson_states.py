"""Finite-state-machine states for the lesson flow.

Tracking *where* the user is lets the fallback handler give a helpful nudge
instead of a generic reply when they type while inside a lesson.
"""
from __future__ import annotations

from aiogram.fsm.state import State, StatesGroup


class LessonStates(StatesGroup):
    reading = State()  # viewing a lesson's theory
    solving = State()  # answering the mini-quiz
